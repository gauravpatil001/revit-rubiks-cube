from Autodesk.Revit.DB import (
    BuiltInCategory,
    ElementTransformUtils,
    FilteredElementCollector,
    Line,
    LocationPoint,
    XYZ,
)
from pyrevit import revit, forms


doc = revit.doc

# Rotate around bottom face outward normal (-Z) through project internal origin.
origin = XYZ(0, 0, 0)
axis = Line.CreateBound(origin, XYZ(0, 0, -10))
angle_radians = -1.57079632679  # 90 degrees clockwise from face viewpoint

# Your model dimensions (Revit internal units are feet):
# each cubie is 1 ft, centered at grid points around internal origin.
cubie_size_ft = 1.0
bottom_layer_z_ft = -cubie_size_ft  # -1.0 ft
z_tolerance = 0.01


def get_point_location(element):
    loc = element.Location
    if isinstance(loc, LocationPoint):
        return loc.Point
    return None


all_generic_instances = (
    FilteredElementCollector(doc)
    .OfCategory(BuiltInCategory.OST_GenericModel)
    .WhereElementIsNotElementType()
    .ToElements()
)

cubies_with_points = []
for elem in all_generic_instances:
    point = get_point_location(elem)
    if point:
        cubies_with_points.append((elem, point))

if not cubies_with_points:
    forms.alert(
        "No point-based Generic Model instances found. "
        "Verify your 26 cubies are model instances with point locations.",
        exitscript=True,
    )

bottom_layer = [
    elem for elem, point in cubies_with_points
    if abs(point.Z - bottom_layer_z_ft) <= z_tolerance
]

if not bottom_layer:
    forms.alert(
        "Bottom layer could not be identified at Z = -1.0 ft.",
        exitscript=True,
    )

if len(bottom_layer) != 9:
    forms.alert(
        "Expected 9 cubies in bottom layer at Z = -1.0 ft, found {}. "
        "Check cubie placement/origins.".format(len(bottom_layer)),
        exitscript=True,
    )

with revit.Transaction("Rotate Bottom Face"):
    for cubey in bottom_layer:
        ElementTransformUtils.RotateElement(doc, cubey.Id, axis, angle_radians)

