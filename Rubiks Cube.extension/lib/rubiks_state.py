import types

from Autodesk.Revit.DB import (
    BuiltInCategory,
    BuiltInParameter,
    DirectShape,
    FilteredElementCollector,
    LocationPoint,
)
from Autodesk.Revit.DB.ExtensibleStorage import AccessLevel, Entity, Schema, SchemaBuilder
from pyrevit import forms
from System import Guid, String

# rubik-solver expects past.builtins.basestring on older code paths.
import sys
if "past" not in sys.modules:
    past_mod = types.ModuleType("past")
    builtins_mod = types.ModuleType("past.builtins")
    builtins_mod.basestring = str
    past_mod.builtins = builtins_mod
    sys.modules["past"] = past_mod
    sys.modules["past.builtins"] = builtins_mod

from rubik_solver.Cubie import Cube
from rubik_solver.Move import Move
from rubik_solver.NaiveCube import NaiveCube
from rubik_solver import utils as rubik_utils


# New GUID to avoid collisions with earlier schema attempts.
SCHEMA_GUID = Guid("8F6E6F6A-AB10-4A6E-9B97-0DF4B7C7C40F")
FIELD_CONFIG = "config"
FIELD_SIGNATURE = "mark_signature"
TARGET_COMMENTS = "Cubeys"


def _get_center(element):
    loc = element.Location
    if isinstance(loc, LocationPoint):
        return loc.Point

    bbox = element.get_BoundingBox(None)
    if bbox:
        return (bbox.Min + bbox.Max) * 0.5

    return None


def _get_mark(element):
    p = element.get_Parameter(BuiltInParameter.ALL_MODEL_MARK)
    if not p:
        return ""
    return (p.AsString() or p.AsValueString() or "").strip()


def _get_comments(element):
    p = element.get_Parameter(BuiltInParameter.ALL_MODEL_INSTANCE_COMMENTS)
    if not p:
        return ""
    return (p.AsString() or p.AsValueString() or "").strip()


def _collect_target_cubies(doc):
    elems = (
        FilteredElementCollector(doc)
        .OfCategory(BuiltInCategory.OST_GenericModel)
        .WhereElementIsNotElementType()
        .ToElements()
    )
    out = []
    for elem in elems:
        if not isinstance(elem, DirectShape):
            continue
        if _get_comments(elem).lower() != TARGET_COMMENTS.lower():
            continue
        center = _get_center(elem)
        if not center:
            continue
        out.append((elem, center, _get_mark(elem)))
    return out


def _solved_config():
    return Cube().to_naive_cube().get_cube()


def _get_schema():
    schema = Schema.Lookup(SCHEMA_GUID)
    if schema:
        return schema

    builder = SchemaBuilder(SCHEMA_GUID)
    builder.SetSchemaName("RubiksCubeState")
    builder.SetReadAccessLevel(AccessLevel.Public)
    builder.SetWriteAccessLevel(AccessLevel.Public)
    builder.AddSimpleField(FIELD_CONFIG, String)
    builder.AddSimpleField(FIELD_SIGNATURE, String)
    return builder.Finish()


def _get_state_host(doc):
    # ProjectInformation exists in all projects and is transaction/undo aware.
    return doc.ProjectInformation


def _load_state(doc):
    schema = _get_schema()
    host = _get_state_host(doc)
    ent = host.GetEntity(schema)
    if not ent or not ent.IsValid():
        return None

    field_config = schema.GetField(FIELD_CONFIG)
    field_sig = schema.GetField(FIELD_SIGNATURE)
    if field_config is None or field_sig is None:
        return None

    try:
        config = ent.Get[String](field_config)
        signature = ent.Get[String](field_sig)
    except Exception:
        return None

    return {
        "config": config,
        "mark_signature": signature,
    }


def _save_state(doc, state):
    if not doc.IsModifiable:
        raise Exception("State save requires an open Revit transaction.")

    schema = _get_schema()
    host = _get_state_host(doc)

    ent = Entity(schema)
    ent.Set[String](schema.GetField(FIELD_CONFIG), state["config"])
    ent.Set[String](schema.GetField(FIELD_SIGNATURE), state["mark_signature"])
    host.SetEntity(ent)


def _build_cube_from_config(config):
    nc = NaiveCube()
    nc.set_cube(config)
    c = Cube()
    c.from_naive_cube(nc)
    return c


def collect_target_cubies(doc):
    return _collect_target_cubies(doc)


def ensure_state(doc, exitscript_on_error=True, require_initialized=False):
    cubies = _collect_target_cubies(doc)
    if len(cubies) != 26:
        msg = (
            "Expected 26 DirectShape Generic Model cubies with Comments='{}', found {}."
            .format(TARGET_COMMENTS, len(cubies))
        )
        if exitscript_on_error:
            forms.alert(msg, exitscript=True)
        raise Exception(msg)

    marks = [m for _, _, m in cubies]
    if any(not m for m in marks):
        msg = "Every cubie needs a unique non-empty Mark value."
        if exitscript_on_error:
            forms.alert(msg, exitscript=True)
        raise Exception(msg)

    if len(set(marks)) != 26:
        msg = "Cubie Marks are not unique. Provide 26 unique Mark values."
        if exitscript_on_error:
            forms.alert(msg, exitscript=True)
        raise Exception(msg)

    signature = "|".join(sorted(marks))
    state = _load_state(doc)
    if not state:
        msg = "State is not initialized. Click 'Initialize' before rotating or solving."
        if require_initialized:
            if exitscript_on_error:
                forms.alert(msg, exitscript=True)
            raise Exception(msg)
        state = {
            "config": _solved_config(),
            "mark_signature": signature,
        }
        return state

    if state.get("mark_signature") != signature:
        msg = (
            "Saved state does not match current Mark set. "
            "Click 'Initialize' to reset solver state."
        )
        if require_initialized:
            if exitscript_on_error:
                forms.alert(msg, exitscript=True)
            raise Exception(msg)
        state = {
            "config": _solved_config(),
            "mark_signature": signature,
        }
    return state


def apply_move(doc, move_notation):
    state = ensure_state(doc, exitscript_on_error=False, require_initialized=True)
    cube = _build_cube_from_config(state["config"])
    cube.move(Move(move_notation))
    state["config"] = cube.to_naive_cube().get_cube()
    _save_state(doc, state)
    return state["config"]


def solve_current(doc):
    state = ensure_state(doc, exitscript_on_error=False, require_initialized=True)
    if state.get("config") == _solved_config():
        return ""
    moves = rubik_utils.solve(state["config"], "Kociemba")
    return " ".join(str(m) for m in moves)


def initialize_state(doc, exitscript_on_error=True):
    cubies = _collect_target_cubies(doc)
    if len(cubies) != 26:
        msg = (
            "Expected 26 DirectShape Generic Model cubies with Comments='{}', found {}."
            .format(TARGET_COMMENTS, len(cubies))
        )
        if exitscript_on_error:
            forms.alert(msg, exitscript=True)
        raise Exception(msg)

    marks = [m for _, _, m in cubies]
    if any(not m for m in marks):
        msg = "Every cubie needs a unique non-empty Mark value."
        if exitscript_on_error:
            forms.alert(msg, exitscript=True)
        raise Exception(msg)

    if len(set(marks)) != 26:
        msg = "Cubie Marks are not unique. Provide 26 unique Mark values."
        if exitscript_on_error:
            forms.alert(msg, exitscript=True)
        raise Exception(msg)

    state = {
        "config": _solved_config(),
        "mark_signature": "|".join(sorted(marks)),
    }
    _save_state(doc, state)
    return state


def validate_state(doc):
    report = []
    ok = True

    cubies = _collect_target_cubies(doc)
    report.append("Target cubies (Comments='{}'): {}".format(TARGET_COMMENTS, len(cubies)))
    if len(cubies) != 26:
        ok = False

    marks = [m for _, _, m in cubies]
    if any(not m for m in marks):
        ok = False
        report.append("Some cubies have empty Mark.")
    else:
        report.append("All cubies have Mark values.")

    if len(set(marks)) != len(marks):
        ok = False
        report.append("Mark values are not unique.")
    else:
        report.append("Mark values are unique.")

    state = _load_state(doc)
    if not state:
        ok = False
        report.append("Saved state not found. Click Initialize.")
        return ok, report

    report.append("Saved state found.")
    signature = "|".join(sorted(marks))
    if state.get("mark_signature") != signature:
        ok = False
        report.append("Saved state signature does not match current Mark set.")
    else:
        report.append("Saved state signature matches Mark set.")

    config = state.get("config", "")
    if len(config) != 54:
        ok = False
        report.append("Saved config length is {}, expected 54.".format(len(config)))
    else:
        report.append("Saved config length is valid (54).")

    return ok, report
