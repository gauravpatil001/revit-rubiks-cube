import os
import sys

from pyrevit import forms, revit


doc = revit.doc

# Load extension-local helper module.
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

# Run structural + saved-state checks and show a readable report.
ok, report = rubiks_state.validate_state(doc)
title = "Validate State - OK" if ok else "Validate State - Issues Found"
forms.alert("\n".join(report), title=title)
