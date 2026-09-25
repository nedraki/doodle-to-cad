# Initial User Request (saved verbatim)

Date: 2026-09-16

Review the source code and get familiar with the project and core purpose.

Core idea: user draws a basic doodle and the intelligent pipeline can create a CAD representing the part, ready to 3D print. Following principles to increase 3D printing quality are encouraged and the volume can be limited to the cube of a Bambulab (X1C/P1S class: 256 x 256 x 256 mm build volume).

The current pipeline is OK-ish but not reliable enough for the broad possibilities of doodles a user can give.

## Task

1. Work from a worktree.
2. First create a variety of use cases to increase the benchmark (create them, search online, or make a hybrid: download an STL part from Thingiverse, MakerWorld, or McMaster-Carr and create what could be a doodle representing such part).
3. With an increased benchmark, be ready to make changes to the app and check if reliability and quality of generation increases.

## Known problem to investigate

Coordinate system is confused or lost across the pipeline: things located at a certain position on the doodle end up in totally different places. Core issue: maintaining the same reference system across steps of the pipeline.

## Method

- Run the app with benchmark images and do the failure analysis yourself.
- Ask whether your own analysis is accurate (self-critique).
- Then plan and execute an improvement plan.
- The benchmark is the north star.

## Working style

Work in an organized and surgical way: make a plan, make a todo list, and track progress, so it is easier to communicate with other agents in the future or with subagents that can be used.
