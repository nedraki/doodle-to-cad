# EV-7 probe — orientation-normalized fidelity upper bound

Run: `uv run python docs/brep/bench-eval/probes/probe_ev7_orientation.py`
(from the repo root, in the app venv; ~30 s, no model calls).

## Question
EV-7 says fidelity is orientation-dependent: the same correct part can pass
or fail depending on which way it is built. Does a correct part, rotated
into its best of the 24 cube rotations, pass the harness bar (>=0.45)?

## Method
Rasterize an orthographic silhouette of the archived STL under each of the
24 proper cube rotations (PIL polygon fill, 128 px), score foreground IoU
against the drawing crop of the view group the harness assigned
(`assign_view_groups` — the same registration the harness uses), report the
best and mean over rotations per direction.

**Calibration (read before trusting absolute numbers).** This IoU proxy is
NOT the harness similarity metric — it is a conservative lower proxy. On
`004/openscad/t1` the harness reports 0.991/0.992 (its own profile metric);
this probe's best is 0.78/0.46. Use relative movement and the pass bar only
as evidence, not the absolute values.

## Results

| row | harness scores | probe best (front) | probe best (other) | reading |
|---|---|---|---|---|
| 004 usd-brep t1 (fid FAILED) | front 0.33, top 0.381 | **0.76** | top **0.77** | Orientation explains the failure: a rotation doubles both scores far past the 0.45 proxy bar. The part is correct; the registration picks the wrong view. |
| 004 openscad t1 (fid PASSED) | front 0.991, top 0.992 | 0.78 | top 0.46 | Control row: proxy tracks the harness ranking. |
| wheel usd-brep t2 (front FAILED) | front 0.35, right 1.00 | 0.27 | right 0.70 | Orientation does NOT fully explain the wheel: no rotation approaches the proxy level the passing `right` view reaches. The missing-spoke/topology problem (EV-2) is separate and real. |

## Consequences
- EV-7 stands (VERIFIED by this probe for the 004-class failure): the
  harness compares a FIXED view registration against silhouettes whose
  orientation the model chose freely. A compliant model that builds a plate
  standing on its edge is scored against the wrong crop and fails.
- Fix direction (harness side, allowed under the no-backend-changes rule):
  before scoring, try the 24 cube rotations of the STL and keep the best
  assignment (or assign groups from part axes rather than image layout).
  This is a scoring change — it must be re-frozen with a new plan revision
  and re-run, never silently applied to the frozen bench numbers.
- The wheel front failure is NOT excused: EV-2 (opening extraction /
  missing spokes) remains the primary blame there.
