# Revit Rubik's Cube (pyRevit)

The first Rubik's Cube project in the world built for Revit, with live turns and solve workflow directly in pyRevit.

An exciting pyRevit toolset to rotate and solve a Rubik's Cube modeled in Revit.

## What It Does
- Adds ribbon buttons for clockwise and counter-clockwise face turns (`U/D/L/R/F/B`).
- Tracks cube state in-project (undo/redo aware).
- Solves the current tracked state and returns move notation.
- Provides `Initialize` and `Validate State` utility buttons.

## Expected Revit Setup
- 26 cube elements in `Generic Model` category.
- Elements are `DirectShape`.
- Instance `Comments` parameter is exactly `Cubeys`.
- Each cubie has a unique, non-empty `Mark`.
- Cube centered around Revit internal origin on a `-1/0/+1` grid.

## Panels
- `Clockwise Rotation`
- `Counter Clockwise Rotation`
- `Solve`

## pyRevit Dependencies
1. Install Autodesk Revit.
2. Install pyRevit and attach it to your Revit version.
3. Place this extension folder in a pyRevit extensions path:
   - `Rubiks Cube.extension`
4. Reload pyRevit (`pyRevit > Reload`).

Notes:
- Python solver dependencies are bundled in `Rubiks Cube.extension/lib`.
- No extra `pip install` is required for normal use.

## Basic Workflow
Use the provided `Rubiks Cube.rvt` project and run the buttons from the pyRevit ribbon.
