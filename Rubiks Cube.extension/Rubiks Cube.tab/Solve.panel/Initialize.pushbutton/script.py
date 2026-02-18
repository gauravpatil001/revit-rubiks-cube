import os
import sys

from pyrevit import forms, revit


doc = revit.doc

# Load extension-local libs so this button works without global installs.
this_dir = os.path.dirname(__file__)
ext_dir = os.path.abspath(os.path.join(this_dir, "..", "..", ".."))
lib_dir = os.path.join(ext_dir, "lib")
if os.path.isdir(lib_dir) and lib_dir not in sys.path:
    sys.path.insert(0, lib_dir)

try:
    import rubiks_state
except Exception as ex:
    forms.alert(
        "State module not found in lib folder.\n\n{}".format(ex),
        exitscript=True,
    )

try:
    # Persist solved baseline in a single undo-aware Revit transaction.
    with revit.Transaction("Initialize Rubik Solver State"):
        rubiks_state.initialize_state(doc)
except Exception as ex:
    forms.alert(
        "Initialize failed.\n\n{}".format(ex),
        exitscript=True,
    )

forms.alert("Solver state initialized to solved cube.")
