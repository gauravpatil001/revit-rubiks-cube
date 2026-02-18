import os
import sys

from pyrevit import forms, revit


doc = revit.doc

# Load extension-local helper module and bundled solver dependencies.
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
    # Ensure preconditions before attempting a solve.
    rubiks_state.ensure_state(doc, require_initialized=True)
    # Compute move notation from the currently tracked cube state.
    solution = rubiks_state.solve_current(doc)
except Exception as ex:
    forms.alert(
        "Solver failed.\n\n{}\n\n"
        "Check Mark values and that moves were performed using these pyRevit buttons.".format(ex),
        exitscript=True,
    )

forms.alert(
    "Solution:\n\n{}\n\n"
    "Copy this move sequence for execution.".format(solution if solution else "(already solved)"),
    title="Rubik Solution",
)
