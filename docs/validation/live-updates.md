# Live parameter updates

Input values update immediately. A 350 ms pause coalesces edits before requesting
an OpenSCAD compilation. Each input invalidates older responses and pending mesh
loads; reset and changing runs do the same. The visible mesh, feature metadata,
and STL link advance only after the current mesh loads successfully. During
compilation the previous mesh remains visible and the camera remains usable.
Failures retain that mesh and report an update failure through a live status region.

Every API compilation uses a UUID in its SCAD/STL filenames. Concurrent requests
cannot share output files, including requests changing the same parameters.
Aborting a browser request does not cancel an already-running server compilation.
These artifacts currently remain in the run directory; cleanup and server-side
job scheduling are separate work. Edited-result validation labels and SCAD
download selection remain tracked by issue #5.

## Measured compilation latency

Measured 2026-09-27 on the development host, using the configured Docker fallback
(`openscad/openscad:latest`) through `compile_stl_only`, three sequential runs per
case with unique output names in a temporary directory. No model inference or
view rendering was included.

| Model | Compile times (seconds) |
| --- | --- |
| 40 × 30 × 10 mm cube | 0.360, 0.329, 0.335 |
| `docs/demo/multiview_model.scad` (bookend with four openings) | 0.393, 0.416, 0.402 |

These samples suggest roughly 0.68–0.77 seconds including debounce, before HTTP
and browser mesh-loading overhead. They are local measurements, not a latency
promise for complex models or concurrent load. A separate frame-by-frame preview
is not needed to address request ordering.

## Validation

- `pytest -q`: includes overlapping API compilations with independent source and
  output contents, and preservation of the original model.
- `node scripts/check_live_updates.cjs`: delayed older responses, input during
  mesh loading, reset during compilation, current/stale failures, run changes,
  and the viewer's stale-geometry disposal guard.
- `python scripts/check_live_updates_browser.py`: rapid inputs coalesce; the
  previous mesh stays visible; camera changes survive replacement; compilation
  failures retain the mesh; reset restores controls. Requires a running app and
  an existing result. `--browser` selects an installed Chromium executable.
- `python scripts/check_feature_highlights.py`: feature overlays and camera
  preservation continue to work. Uses the same browser prerequisites.

Browser checks mock compilation responses; the timing measurements above use
real OpenSCAD compilation.
