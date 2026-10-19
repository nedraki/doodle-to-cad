# usd_brep 1.0.0 — deterministic tessellation crash on arc_pipe ∪ cylinder (missing `_omni_solid`)

Filed against: `usd-brep==1.0.0` (PyPI wheel), NVIDIA Omniverse USD BRep bindings.
Environment: aarch64 (NVIDIA GB10), Ubuntu 24.04, glibc 2.39, CPython 3.12 worker venv.
Reproducer owner: doodle-to-cad issue #61 (branch `brep-integration`).

## Summary
Building a solid that unions a 180-degree `arc_pipe` (torus-segment sweep) with a
cylinder intersecting its terminal cap always fails inside tessellation with:

```
ModuleNotFoundError: No module named '_omni_solid'
```

The private extension module `_omni_solid` is not shipped in the wheel for this
body class. The failure is **deterministic** (3/3 serial rebuilds, same recipe) and
is raised even when all inputs are individually buildable.

## Minimal reproducer
`scripts/repro_omni_solid.py` + `scripts/fixtures/omni_solid_minimal.recipe.json`
(sha256 `0e0fa35a69b0c59bd5bc0c2ee35bab8ef610aa62e731d7dc70ec025ea6e14cdf`),
run through the same worker entry point used in production (`workers/brep/build.py`).

The recipe (brep-recipe-v1):
1. `arc_pipe` "arch": bend_radius 20, origin (0,0,4), 180° — a half-torus tube;
2. `cylinder` "leg": radius 4, origin (-20,0,0) — sits across the arch's left terminal cap;
3. `union` of the two → tessellation crashes.

Run: `DOODLE_BREP_PYTHON=<worker py> python scripts/repro_omni_solid.py`
Exit 0 with verdict `3/3 behaved as expected (expected=crash, signature="No module named '_omni_solid'")`.

## Characterization (measured, from `logs/shrink-ladder.json`)
| case | result |
|---|---|
| arc_pipe alone (180°) | builds |
| cylinder alone | builds |
| two cylinders union | builds (reported disconnected_output — geometry issue, not kernel) |
| box + arc_pipe union | builds |
| arc90 ∪ cylinder | builds |
| **arc180 ∪ cylinder (crossing terminal cap)** | **crashes 3/3** |
| arc135/270 ∪ cylinder, axis/difference variants | see ladder (recorded verbatim, incl. `unknown` probes) |

The trigger narrows to the **180-degree arc_pipe boolean union with a solid
intersecting its terminal cap**. It is not "all circular geometry": the recipe path
builds wheels with radial spokes (8 cylinders + hub unions) without this crash
(`docs/brep/bench-features/artifacts/wheel`).

## Expected vs actual
- Expected: tessellation returns a triangle mesh, or raises a documented kernel error.
- Actual: the tessellator lazily imports the wheel-missing private module
  `_omni_solid`, producing `ModuleNotFoundError`, indistinguishable (in the raw form)
  from a user-side packaging mistake.

## Product-side containment (already shipped in doodle-to-cad)
`build_contract.classify_kernel_crash` maps the exact signature to failure code
`kernel_unavailable` with advice "Retry with the OpenSCAD backend" plus the fixture
hash; any other `ModuleNotFoundError` keeps its generic code (planted-error tests in
`tests/test_brep_kernel_containment.py`, 12 cases).

## Second defect (message-level evidence only)
Two independent generated recipes in our frozen comparison failed on spoke
unions with the worker message `"<op>: kernel produced an invalid solid"`
(wheel trials 04/05 of an 8-spoke style wheel; trial-03 failed connectivity
with `components=5`). The harness stored the error rows but not the failing
recipes, and 8 hand-built mutations of our known-good wheel fixture did not
reproduce the message (log in this dossier). We report it as observed kernel
behaviour, not a reproducer: if the validity check in your boolean path is
expected under rotated-union spoke patterns, we would like to know what makes
the solid "invalid".

## Asks
1. Ship `_omni_solid` (or document the optional kernel extra) in the 1.0.0 wheel.
2. Raise a typed kernel error instead of a bare `ModuleNotFoundError`.
3. Confirm whether the 180° sweep class is supported at all in 1.0.0.
4. Explain the `kernel produced an invalid solid` validity rejection (see above).
