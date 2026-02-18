import os
import sys

from Autodesk.Revit.DB import ElementTransformUtils, Line, XYZ
from pyrevit import revit, forms


doc = revit.doc

# Ensure extension-local libraries (state + solver wrappers) are importable.
this_dir = os.path.dirname(__file__)
ext_dir = os.path.abspath(os.path.join(this_dir, "..", "..", ".."))
lib_dir = os.path.join(ext_dir, "lib")
if os.path.isdir(lib_dir) and lib_dir not in sys.path:
    sys.path.insert(0, lib_dir)

try:
    import rubiks_state
except Exception as ex:
    forms.alert("State module not found in lib folder.\n\n{}".format(ex), exitscript=True)

# Rotation axis passes through project internal origin.
origin = XYZ(0, 0, 0)
axis = Line.CreateBound(origin, XYZ(-10, 0, 0))
angle_radians = -1.57079632679

# Cubie centers are expected at -1/0/+1 feet from origin.
cubie_size_ft = 1.0
layer_value = -cubie_size_ft
layer_tolerance = 0.05

# Require explicit Initialize and validate target cubie identity set.
rubiks_state.ensure_state(doc, require_initialized=True)
cubies_with_points = rubiks_state.collect_target_cubies(doc)

if len(cubies_with_points) != 26:
    forms.alert("Expected 26 target cubies, found {}.".format(len(cubies_with_points)), exitscript=True)

# Pick the 9 cubies on the requested face layer.
if "X" == "X":
    face_layer = [elem for elem, point, _ in cubies_with_points if abs(point.X - layer_value) <= layer_tolerance]
elif "X" == "Y":
    face_layer = [elem for elem, point, _ in cubies_with_points if abs(point.Y - layer_value) <= layer_tolerance]
else:
    face_layer = [elem for elem, point, _ in cubies_with_points if abs(point.Z - layer_value) <= layer_tolerance]

if len(face_layer) != 9:
    forms.alert("Expected 9 cubies in Left layer, found {}.".format(len(face_layer)), exitscript=True)

try:
    # Geometry rotation and logical state update happen in one transaction so Undo stays consistent.
    with revit.Transaction("Rotate Left Face"):
        for cubey in face_layer:
            ElementTransformUtils.RotateElement(doc, cubey.Id, axis, angle_radians)
        rubiks_state.apply_move(doc, "L")
except Exception as ex:
    forms.alert(
        "Left rotation/state update failed.\n\n{}".format(ex),
        exitscript=True,
    )
