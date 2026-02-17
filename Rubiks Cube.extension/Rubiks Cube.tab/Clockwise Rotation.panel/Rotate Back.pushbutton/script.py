import os
import sys

from Autodesk.Revit.DB import ElementTransformUtils, Line, XYZ
from pyrevit import revit, forms


doc = revit.doc

this_dir = os.path.dirname(__file__)
ext_dir = os.path.abspath(os.path.join(this_dir, "..", "..", ".."))
lib_dir = os.path.join(ext_dir, "lib")
if os.path.isdir(lib_dir) and lib_dir not in sys.path:
    sys.path.insert(0, lib_dir)

try:
    import rubiks_state
except Exception as ex:
    forms.alert("State module not found in lib folder.\n\n{}".format(ex), exitscript=True)

origin = XYZ(0, 0, 0)
axis = Line.CreateBound(origin, XYZ(0, 10, 0))
angle_radians = -1.57079632679

cubie_size_ft = 1.0
layer_value = cubie_size_ft
layer_tolerance = 0.05

# Requires explicit Initialize and validates 26 unique marked target cubies.
rubiks_state.ensure_state(doc, require_initialized=True)
cubies_with_points = rubiks_state.collect_target_cubies(doc)

if len(cubies_with_points) != 26:
    forms.alert("Expected 26 target cubies, found {}.".format(len(cubies_with_points)), exitscript=True)

if "Y" == "X":
    face_layer = [elem for elem, point, _ in cubies_with_points if abs(point.X - layer_value) <= layer_tolerance]
elif "Y" == "Y":
    face_layer = [elem for elem, point, _ in cubies_with_points if abs(point.Y - layer_value) <= layer_tolerance]
else:
    face_layer = [elem for elem, point, _ in cubies_with_points if abs(point.Z - layer_value) <= layer_tolerance]

if len(face_layer) != 9:
    forms.alert("Expected 9 cubies in Back layer, found {}.".format(len(face_layer)), exitscript=True)

try:
    with revit.Transaction("Rotate Back Face"):
        for cubey in face_layer:
            ElementTransformUtils.RotateElement(doc, cubey.Id, axis, angle_radians)
        rubiks_state.apply_move(doc, "B")
except Exception as ex:
    forms.alert(
        "Back rotation/state update failed.\n\n{}".format(ex),
        exitscript=True,
    )
