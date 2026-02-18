# Revit Rubik's Cube (pyRevit)

Small pyRevit toolset to rotate and solve a Rubik's Cube modeled in Revit.

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

## Basic Workflow
1. Set cubie `Comments = Cubeys` and unique `Mark` values.
2. Click `Initialize`.
3. Use rotation buttons to scramble.
4. Click `Solve Cube` to get moves.
5. Use `Validate State` if anything looks out of sync.
