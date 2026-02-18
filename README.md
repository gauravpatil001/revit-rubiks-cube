# Revit Rubik's Cube (pyRevit)

Turn Revit into a puzzle-solving playground. This pyRevit toolset allows you to rotate, track, and solve a fully modeled Rubik's Cube directly within your project environment.

This extension brings the logic of the world's most famous puzzle to the world's most famous BIM software, complete with live rotations and a built-in solver.

## What It Does

Live Rotations: Dedicated ribbon buttons for all standard face turns (U/D/L/R/F/B) in both clockwise and counter-clockwise directions.

State Tracking: The tool stays aware of the cube's position, and it is fully Undo/Redo aware.

Instant Solver: If you get stuck, the built-in solver analyzes your current Revit model state and returns the move notation to get you back to a perfect finish.

Utility Tools: Includes Initialize and Validate State buttons to ensure your cube is ready for action.

## Expected Revit Setup

To get spinning, your Revit project should meet these simple specs, or just use the provided Rubiks Cube.rvt.

Category: 26 elements in the Generic Model category.

Type: Elements should be DirectShape.

Identification: Instance Comments parameter must be exactly Cubeys.

Marking: Each cubie needs a unique, non-empty Mark.

Coordinates: Cube must be centered around the Revit internal origin on a -1/0/+1 grid.

## Panels

Clockwise Rotation: Quick access to standard moves.

Counter Clockwise Rotation: Inverse moves for easier scrambling and solving.

Solve: The brains of the operation to help you finish the puzzle.

## pyRevit Dependencies

Getting started is a breeze with no extra pip install required.

Install Software: Ensure Autodesk Revit and pyRevit are installed and attached.

Add Extension: Place the Rubiks Cube.extension folder in your pyRevit extensions path.

Reload: Run pyRevit > Reload to see the new ribbon tab.

Bundled Libs: All Python solver dependencies are pre-bundled in the Rubiks Cube.extension/lib folder.

## Basic Workflow

Simply open the provided Rubiks Cube.rvt project and use the buttons on the pyRevit ribbon to start twisting and turning.
