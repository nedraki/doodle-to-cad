# Special-features benchmark (BRep recipe matrix)

Question answered here: does each BRep recipe feature build a geometrically
correct solid, measured on the exported mesh, not on kernel claims? One row
per feature. Every build, pass or fail, is published under `artifacts/` and
`measurements/`. Re-run every claim with `audit.py` (see bottom).

## Feature matrix

| Feature | Fixture | Measured vs expected | Verdict | Artifacts |
|---|---|---|---|---|
| Fillet | pocket block 60×40×20, `outer_vertical` edges, r=15 (derived: width/4) | 4/4 corner arcs fit r = 15.003–15.007 mm (tol 0.1 mm) | **Pass** | `artifacts/fillet_block/`, `measurements/fillet_block.json`, `gifs/fillet_block_orbit.gif` |
| Chamfer | box 50×40×20, `chamfer {body, radius: 3}` | 45° taper both ends (fit slopes 2.000); fitted leg = 2.1215 mm = 3/√2 (tol 0.05) | **Pass, with kernel semantics note** (below) | `artifacts/chamfer_box/`, `gifs/chamfer_box_orbit.gif` |
| Chamfer planted error | same fixture built at radius 1.0, verified against nominal 3 | checker FAILS it (slope 0.57, leg 1.61 vs 2.12) | **Checker can fail** | `artifacts/chamfer_planted_wrong_radius/`, `measurements/…json` |
| Arc pipe quarter | quarter torus, bend + tube radii | centreline and tube radii within 0.1 mm at 4 height probes | **Pass** | `artifacts/arc_pipe_quarter/`, `gifs/arc_pipe_quarter_orbit.gif` |
| Arc pipe half | half torus | same checks pass | **Pass** | `artifacts/arc_pipe_half/`, `gifs/arc_pipe_half_orbit.gif` |
| Loft (rect→round) | 40×30 rectangle → r15 circle over 50 mm | both ends exact (≤0.15 mm); edge midpoints move linearly (slope err ≤ 0.004 mm/mm); area strictly monotone 1200→707 mm²; symmetric ≤0.15 mm | **Pass** | `artifacts/loft_transition/`, `gifs/loft_transition_orbit.gif` |
| Loft planted error | same loft built with circle_radius 12, verified against nominal 15 | checker FAILS it (top circle 12.00 vs 15.00, edge-midline slopes wrong) | **Checker can fail** | `artifacts/loft_planted_wrong_radius/` |
| Shell (open-top tray) | 80×60×30, walls/floor 4 mm | volume 46656.0 mm³ = ideal to 0.00%; watertight; Euler 2 (genus 1 = open top); wall/floor probes all 4.0 mm; cavity hollow at all heights | **Pass** | `artifacts/shell_tray/`, `gifs/shell_tray_orbit.gif` |
| Wheel spokes (regression probe) | circular-pattern spoke union | built: watertight, 1 component, 860 triangles | **Pass (this configuration)** | `artifacts/wheel_spokes/`, `gifs/wheel_spokes_orbit.gif` |
| Curved handle + legs (regression probe) | arc_pipe + cylinder boolean | build failed: `No module named '_omni_solid'` (deterministic kernel crash, recorded verbatim) | **Published failure** — issue #61 | `artifacts/curved_handle/build.json` |

## Kernel semantics learned by measurement (not from docs)

- **Chamfer `radius` is the hypotenuse, not the leg.** A `chamfer` with
  radius 3 produced a 45° taper with leg 3/√2 = 2.1215 mm, fitted from four
  slice probes per side. The checker asserts the fitted leg, so the planted
  wrong-radius build cannot pass.
- **Chamfer touched the horizontal (top/bottom) edges only.** Mid-height
  footprint stayed the full 50×40 rectangle (vertical edges untouched).
- **Loft interpolation law is unspecified.** The recipe promises the two end
  profiles. Edge midpoints interpolate linearly; the corner region bulges
  relative to a polar-linear model (measured +0.72 mm at t=0.5). The checker
  therefore asserts exact ends, linear edge midpoints, monotone area, and
  symmetry — not an interpolation law the kernel never promised.
- **Ray-parity point tests hit a loft tessellation seam** (~0.7 mm from
  centre). Symmetry claims therefore use vertex-band extents, not point
  membership. Recorded so future checkers do not repeat the false alarm.

## Failures kept (all published, none hidden)

1. `curved_handle`: deterministic `_omni_solid` crash (worker log tail in
   `artifacts/curved_handle/build.json`). Cross-ref **issue #61**.
2. Two checkers were wrong before any geometry was trusted: `verify_shell`
   inverted its hollow-cavity logic, and `verify_loft` assumed the rectangle
   corner sat at 45° (it sits at 36.87° for a 40×30 rectangle) and asserted a
   polar-linear interpolation law. Both fixed after measuring the mesh.
   The corrected checkers still fail the planted errors.
3. A first chamfer calibration attempt (by an earlier agent) measured before
   the mesh was merged on load and recorded a false `watertight: false`.
   The final checker merges on load (`force="mesh"`).
4. `wheel_spokes` built fine in this recipe configuration. That does NOT
   contradict issue #61: #61 failures came through the generated-geometry
   path; this fixture is a deterministic recipe union. Both facts published.

## Honest limits

- Single machine (DGX Spark aarch64), pinned `usd_brep==1.0.0`. No claim
  about other kernels or platforms.
- STL-level measurement only (exported mesh). USDA round-trip verified in
  task 16; STEP not promised.
- Mesh probes carry their stated tolerances; nothing here claims sub-0.01 mm
  accuracy.
- The viewer screenshots/GIFs show the exported STL in the product's own
  viewer (mounted via the real app server); they are visual evidence, while
  the pass/fail column comes from the mesh measurements.

## Re-run it yourself (repo root)

```bash
export DOODLE_BREP_PYTHON=$PWD/workers/brep/.venv/bin/python
PYTHONPATH=. .venv/bin/python docs/brep/bench-features/run_bench.py        # rebuild + measure all
PYTHONPATH=. .venv/bin/python docs/brep/bench-features/audit.py            # re-verify every claim
PYTHONPATH=. .venv/bin/pytest -q                                           # full suite
```
