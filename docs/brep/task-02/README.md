# Task 02: Shared build result

Issue: [#19](https://github.com/nedraki/doodle-to-cad/issues/19).
Task branch: `codex/brep-02-build-contract`.
PR base: `brep-integration`. Do not merge this work into `main`.

## Change

Both backends now accept a `BuildInput` and return a `BuildResult`.
The input selects the backend, native source file, output directory, and render option.
The result contains the source, STL, optional exports, view images, mesh measurements,
log, and diagnostic codes. Source formats stay separate: OpenSCAD text and recipe JSON.
`GET /api/backends` lists supported formats, exports, views, and parameter editing.
This is a capability list. It does not prove that a backend is installed.

The OpenSCAD generation pipeline uses the shared result. Existing tuple and recipe
API wrappers remain available. The parameter editor retains its current behavior.
The BRep worker runs in its separate Python process, with a 120-second timeout.
It publishes a new revision only after its checks pass. A failed build retains
previous revisions. OpenSCAD builds reject stale STL output after a failed compile.

Both backends use the existing camera values. X is width, Y is depth, and Z is height.
Distances are in millimetres. BRep view images use OpenSCAD to render the finished
STL. OpenSCAD does not construct the BRep solid.

Failure codes are `invalid_input`, `backend_unavailable`, `build_failed`, `timeout`,
`invalid_output`, and `render_failed`. A render failure is a warning: the checked
mesh stays available, but missing views are explicit. A successful build does not
mean that the part matches the drawing. Drawing evaluation remains a separate step.

## Validation

Use the four-hole bracket in `benchmarks/brep/bracket.json` and the OpenSCAD
reference in `scripts/evaluate_brep.py`. No model call is needed.

Run the app in a separate process:

```sh
DOODLE_RESULTS_DIR=results/brep-contract-tests .venv/bin/python -m uvicorn doodle_to_cad.app:app --host 127.0.0.1 --port 8081
```

Run the product check with the path to an installed Chromium executable:

```sh
DOODLE_RESULTS_DIR=results/brep-contract-tests CHROMIUM_EXECUTABLE=/path/to/chrome .venv/bin/python scripts/check_build_contract.py
DOODLE_BREP_PYTHON="$PWD/workers/brep/.venv/bin/python" .venv/bin/python -m pytest -q
```

The full regression suite passes: **76 tests**.

The product check writes `report.json` and the images in this directory.
Both parts measure 60 × 40 × 80 mm. Each has one watertight component.
Silhouette overlap is 1.0 for all four views. This checks the same asymmetric part
with the same camera settings. It does not prove camera accuracy for all shapes.
Both parts load in the current browser viewer. All four view images load.
Source and STL downloads match the files used by the viewer. The USD download also
matches its BRep revision. No browser script errors occurred.

## Limits and review gate

- This task does not add direct model generation of BRep recipes or select a backend.
- BRep image rendering requires an available OpenSCAD renderer.
- Recipe support and geometric limits remain those of the existing worker.
- Parameter edits keep the existing API. OpenSCAD parameter edits compile only STL.
- The regression suite reports the existing Starlette/httpx deprecation warning.
- User review is pending. Keep this issue open. Do not start task 03 yet.
- Integration commit: pending review and merge into `brep-integration`.
