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

# New GUID (schema v3) for strict project-bound state.
SCHEMA_GUID = Guid("6A22FE1F-C4AF-4E74-8A5C-1D1F8946E1D7")
FIELD_CONFIG = "config"
FIELD_SIGNATURE = "mark_signature"
FIELD_PROJECT_KEY = "project_key"
TARGET_COMMENTS = "Cubeys"
CUBIE_SIZE_FT = 1.0
GRID_TOLERANCE_FT = 0.2
SOLVED_CONFIG = "yyyyyyyyybbbbbbbbbrrrrrrrrrgggggggggooooooooowwwwwwwww"
_solver_cache = None


def _get_center(element):
    # DirectShape may expose either LocationPoint or only a bounding box.
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
    # Restrict scope to the dedicated Rubik cubies only.
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
    return SOLVED_CONFIG


def _get_solver_modules():
    global _solver_cache
    if _solver_cache:
        return _solver_cache

    import sys
    import types

    # rubik-solver expects past.builtins.basestring on older code paths.
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

    _solver_cache = (Cube, Move, NaiveCube, rubik_utils)
    return _solver_cache


def _project_key(doc):
    # Tie saved state to this specific Revit project, not just element names.
    path = (doc.PathName or "").strip().lower()
    proj_uid = (doc.ProjectInformation.UniqueId or "").strip().lower()
    if path:
        return "path:{}|proj:{}".format(path, proj_uid)
    return "title:{}|proj:{}".format((doc.Title or "").strip().lower(), proj_uid)


def _nearest_grid_value(value):
    candidates = (-CUBIE_SIZE_FT, 0.0, CUBIE_SIZE_FT)
    best = min(candidates, key=lambda c: abs(value - c))
    if abs(value - best) > GRID_TOLERANCE_FT:
        return None
    return best


def _grid_slot(point):
    gx = _nearest_grid_value(point.X)
    gy = _nearest_grid_value(point.Y)
    gz = _nearest_grid_value(point.Z)
    if gx is None or gy is None or gz is None:
        return None
    return (gx, gy, gz)


def _get_schema():
    # Reuse schema if it already exists in the document session.
    schema = Schema.Lookup(SCHEMA_GUID)
    if schema:
        return schema

    builder = SchemaBuilder(SCHEMA_GUID)
    builder.SetSchemaName("RubiksCubeState")
    builder.SetReadAccessLevel(AccessLevel.Public)
    builder.SetWriteAccessLevel(AccessLevel.Public)
    builder.AddSimpleField(FIELD_CONFIG, String)
    builder.AddSimpleField(FIELD_SIGNATURE, String)
    builder.AddSimpleField(FIELD_PROJECT_KEY, String)
    return builder.Finish()


def _get_state_host(doc):
    # ProjectInformation exists in all projects and is transaction/undo aware.
    return doc.ProjectInformation


def _load_state(doc):
    # Read persisted state from ProjectInformation extensible storage.
    schema = _get_schema()
    host = _get_state_host(doc)
    ent = host.GetEntity(schema)
    if not ent or not ent.IsValid():
        return None

    # Pull fields from the Entity's own schema to avoid mismatches with
    # stale/legacy schema objects after upgrades or undo/redo boundaries.
    ent_schema = ent.Schema
    if ent_schema is None:
        return None

    field_config = ent_schema.GetField(FIELD_CONFIG)
    field_sig = ent_schema.GetField(FIELD_SIGNATURE)
    field_proj = ent_schema.GetField(FIELD_PROJECT_KEY)
    if field_config is None or field_sig is None or field_proj is None:
        return None

    try:
        config = ent.Get[String](field_config)
        signature = ent.Get[String](field_sig)
        project_key = ent.Get[String](field_proj)
    except Exception:
        return None

    return {
        "config": config,
        "mark_signature": signature,
        "project_key": project_key,
    }


def _save_state(doc, state):
    if not doc.IsModifiable:
        raise Exception("State save requires an open Revit transaction.")

    schema = _get_schema()
    host = _get_state_host(doc)

    ent = Entity(schema)
    ent.Set[String](schema.GetField(FIELD_CONFIG), state["config"])
    ent.Set[String](schema.GetField(FIELD_SIGNATURE), state["mark_signature"])
    ent.Set[String](schema.GetField(FIELD_PROJECT_KEY), state["project_key"])
    host.SetEntity(ent)


def _build_cube_from_config(config):
    # Build Cubie representation from the stored 54-char facelet config.
    Cube, _, NaiveCube, _ = _get_solver_modules()
    nc = NaiveCube()
    nc.set_cube(config)
    c = Cube()
    c.from_naive_cube(nc)
    return c


def collect_target_cubies(doc):
    return _collect_target_cubies(doc)


def ensure_state(doc, exitscript_on_error=True, require_initialized=False):
    # Validate cubie population and identity before any move/solve call.
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
    project_key = _project_key(doc)
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
            "project_key": project_key,
        }
        return state

    if state.get("project_key") != project_key:
        msg = (
            "Saved state belongs to a different Revit project. "
            "Click 'Initialize' in this project."
        )
        if require_initialized:
            if exitscript_on_error:
                forms.alert(msg, exitscript=True)
            raise Exception(msg)
        state = {
            "config": _solved_config(),
            "mark_signature": signature,
            "project_key": project_key,
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
            "project_key": project_key,
        }
    return state


def apply_move(doc, move_notation):
    # Apply move to saved config inside the same transaction as geometry.
    _, Move, _, _ = _get_solver_modules()
    state = ensure_state(doc, exitscript_on_error=False, require_initialized=True)
    cube = _build_cube_from_config(state["config"])
    cube.move(Move(move_notation))
    state["config"] = cube.to_naive_cube().get_cube()
    _save_state(doc, state)
    return state["config"]


def solve_current(doc):
    # Return notation only; geometry is changed by rotation buttons.
    _, _, _, rubik_utils = _get_solver_modules()
    state = ensure_state(doc, exitscript_on_error=False, require_initialized=True)
    if state.get("config") == _solved_config():
        return ""
    moves = rubik_utils.solve(state["config"], "Kociemba")
    return " ".join(str(m) for m in moves)


def initialize_state(doc, exitscript_on_error=True):
    # Fast reset: trust user-provided baseline and set solved state directly.
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
        "project_key": _project_key(doc),
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

    # Strict geometry checks to avoid false positives.
    slots = []
    bad_slot = False
    for _, pt, _ in cubies:
        s = _grid_slot(pt)
        if s is None:
            bad_slot = True
        else:
            slots.append(s)
    if bad_slot:
        ok = False
        report.append("Some cubies are not near the expected -1/0/+1 grid.")
    else:
        report.append("All cubies are near expected -1/0/+1 grid.")

    if slots:
        if len(set(slots)) != len(slots):
            ok = False
            report.append("Duplicate cubie grid slots found.")
        else:
            report.append("All cubies occupy unique grid slots.")

        if (0.0, 0.0, 0.0) in set(slots):
            ok = False
            report.append("Center slot (0,0,0) is occupied; expected 26-cubie shell.")
        else:
            report.append("Center slot is empty as expected.")

        for axis_name, idx in (("X", 0), ("Y", 1), ("Z", 2)):
            counts = {-1.0: 0, 0.0: 0, 1.0: 0}
            for s in slots:
                counts[s[idx]] += 1
            if counts[-1.0] != 9 or counts[0.0] != 8 or counts[1.0] != 9:
                ok = False
                report.append(
                    "{} layer counts invalid (-1/0/+1 = {}/{}/{}; expected 9/8/9)."
                    .format(axis_name, counts[-1.0], counts[0.0], counts[1.0])
                )
            else:
                report.append("{} layer counts valid (9/8/9).".format(axis_name))

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
    if state.get("project_key") != _project_key(doc):
        ok = False
        report.append("Saved state belongs to a different project.")
    else:
        report.append("Saved state is bound to this project.")

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

    allowed = set("wrgbyo")
    if not config or any(ch not in allowed for ch in config):
        ok = False
        report.append("Saved config contains invalid color symbols.")
    else:
        bad_counts = []
        for ch in sorted(allowed):
            cnt = config.count(ch)
            if cnt != 9:
                bad_counts.append("{}={}".format(ch, cnt))
        if bad_counts:
            ok = False
            report.append("Saved config color counts invalid: {}.".format(", ".join(bad_counts)))
        else:
            report.append("Saved config color counts are valid (9 each).")

    return ok, report
