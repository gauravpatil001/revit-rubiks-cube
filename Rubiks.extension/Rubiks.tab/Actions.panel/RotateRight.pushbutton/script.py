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

# Rotate around right face outward normal (+X) through project internal origin.
origin = XYZ(0, 0, 0)
axis = Line.CreateBound(origin, XYZ(10, 0, 0))
angle_radians = -1.57079632679  # 90 degrees clockwise from face viewpoint

# Your model dimensions (Revit internal units are feet):
# each cubie is 1 ft, centered at grid points around internal origin.
cubie_size_ft = 1.0
right_layer_x_ft = cubie_size_ft  # +1.0 ft
x_tolerance = 0.01


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

right_layer = [
    elem for elem, point in cubies_with_points
    if abs(point.X - right_layer_x_ft) <= x_tolerance
]

if not right_layer:
    forms.alert(
        "Right layer could not be identified at X = +1.0 ft.",
        exitscript=True,
    )

if len(right_layer) != 9:
    forms.alert(
        "Expected 9 cubies in right layer at X = +1.0 ft, found {}. "
        "Check cubie placement/origins.".format(len(right_layer)),
        exitscript=True,
    )

with revit.Transaction("Rotate Right Face"):
    for cubey in right_layer:
        ElementTransformUtils.RotateElement(doc, cubey.Id, axis, angle_radians)

