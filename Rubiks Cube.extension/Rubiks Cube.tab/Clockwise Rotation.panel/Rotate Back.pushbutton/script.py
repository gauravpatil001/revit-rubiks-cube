from Autodesk.Revit.DB import (
    BuiltInCategory,
    DirectShape,
    ElementTransformUtils,
    FilteredElementCollector,
    Line,
    LocationPoint,
    XYZ,
)
from pyrevit import revit, forms


doc = revit.doc

origin = XYZ(0, 0, 0)
axis = Line.CreateBound(origin, XYZ(0, -10, 0))
angle_radians = -1.57079632679

cubie_size_ft = 1.0
back_layer_y_ft = -cubie_size_ft
y_tolerance = 0.05


def get_element_center(element):
    loc = element.Location
    if isinstance(loc, LocationPoint):
        return loc.Point

    bbox = element.get_BoundingBox(None)
    if bbox:
        return (bbox.Min + bbox.Max) * 0.5

    return None


all_generic_instances = (
    FilteredElementCollector(doc)
    .OfCategory(BuiltInCategory.OST_GenericModel)
    .WhereElementIsNotElementType()
    .ToElements()
)

cubies_with_points = []
for elem in all_generic_instances:
    if not isinstance(elem, DirectShape):
        continue
    point = get_element_center(elem)
    if point:
        cubies_with_points.append((elem, point))

if not cubies_with_points:
    forms.alert(
        "No DirectShape cubies found in Generic Models.",
        exitscript=True,
    )

if len(cubies_with_points) != 26:
    forms.alert(
        "Expected 26 DirectShape cubies, found {}.".format(len(cubies_with_points)),
        exitscript=True,
    )

back_layer = [elem for elem, point in cubies_with_points if abs(point.Y - back_layer_y_ft) <= y_tolerance]

if len(back_layer) != 9:
    forms.alert(
        "Expected 9 cubies in back layer at Y = -1.0 ft, found {}.".format(len(back_layer)),
        exitscript=True,
    )

with revit.Transaction("Rotate Back Face"):
    failed_ids = []
    for cubey in back_layer:
        try:
            ElementTransformUtils.RotateElement(doc, cubey.Id, axis, angle_radians)
        except Exception:
            failed_ids.append(cubey.Id.IntegerValue)

if failed_ids:
    forms.alert("Back rotation failed for ids: {}".format(", ".join(str(x) for x in failed_ids)))
