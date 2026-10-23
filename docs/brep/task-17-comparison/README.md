# Task 17 — Compare generation paths and decide the product default

Issue #34. Branch `hermes/brep-17-comparison`, base `brep-integration` at `4f05849`.
The frozen plan (corpus, model settings, tolerances, pass criteria) is
[TRIAL-PLAN.json](TRIAL-PLAN.json), committed at `frozen_at` **before any trial ran**.
`audit.py` re-verifies every claim below and asserts the plan predates every trial.

## How to reproduce

```sh
cp /home/sparkie/playground/doodle-to-cad/.env .env
uv sync --extra dev
uv venv --python 3.12 workers/brep/.venv && uv pip install --python workers/brep/.venv/bin/python -r workers/brep/requirements.txt
DOODLE_BREP_PYTHON=$PWD/workers/brep/.venv/bin/python PYTHONPATH=. \
  .venv/bin/python scripts/evaluate_brep.py trials --plan docs/brep/task-17-comparison/TRIAL-PLAN.json --port 8132
PYTHONPATH=. .venv/bin/python docs/brep/task-17-comparison/audit.py
```

Setup: one in-process uvicorn app on port 8132, `results/task-17-comparison`,
3 concurrent jobs, poll timeout 2400 s. Model auto-discovered from the local vLLM
server: `local-inference-lab/Qwen3.8-Flash-Next-NVFP4`, app-default thinking
settings, `agent_max_attempts=3`, `accept_score=70`. OpenSCAD ran through the
Docker image `openscad/openscad:latest`. Matrix: 8 drawings x 2 backends x 5
trials = 80 live generations, wall 88 minutes (see `environment.json`).
Seeds were not chosen; every submission kept its request, result copy, job
payload, view renders and measurements under `runs/<drawing>/<backend>/trial-NN/`.

## Claims

| Claim | Evidence |
|---|---|
| 80/80 planned trials ran; none silently skipped | `runs/index.jsonl` (80 rows), `audit.py:matrix_complete` |
| Drawing fidelity is scored separately from solid-build success | `audit.py:fidelity_separate_from_build`; columns below |
| Zero `unsupported_construction` outcomes across 80 runs | `audit.py` unsupported counts; every attempt produced geometry, an error, or a clarification |
| BRep kernel failures are deterministic, not load flakiness | `checks/serial-rebuild/serial-rebuild.json` (all failed recipes rebuilt serially, reproduced exactly) |
| BRep asked the frozen clarification question on every ambiguous/missing-thickness trial | `runs/ambiguous/usd-brep/*/questions.json` (5/5), `runs/missing_thickness/usd-brep/*/questions.json` (5/5) |
| The plan predates every trial | `audit.py:plan_frozen_before_trials` |
| Artifact integrity | `SHA256SUMS`, `audit.py:sha256sums` |

## Shared capabilities

Pass criteria are frozen in TRIAL-PLAN.json: build_success (independent trimesh
watertight + single component), sorted extents within 2%, genus == frozen
reference, volume within 2%, and harness-recomputed projection similarity
>= 0.45 in every assigned view (fidelity kept separate from build).
`overall_pass` requires all applicable checks. Counts are recomputed by
`audit.py` from the raw rows.

| drawing | backend | trials | pass | build | fidelity | unsupported | edits_ok | targeted_ok |
|---|---|---|---|---|---|---|---|---|
| bookend | openscad | 5 | 0 | 5 | 2 | 0 | 5 | 0 |
| bookend | usd-brep | 5 | 0 | 5 | 5 | 0 | 5 | 0 |
| wheel | openscad | 5 | 0 | 4 | 5 | 0 | 5 | 0 |
| wheel | usd-brep | 5 | 0 | 2 | 1 | 0 | 2 | 0 |
| enclosure | openscad | 5 | 0 | 5 | 5 | 0 | 5 | 0 |
| enclosure | usd-brep | 5 | 0 | 4 | 0 | 0 | 4 | 0 |
| curved_handle | openscad | 5 | 0 | 3 | 2 | 0 | 4 | 0 |
| curved_handle | usd-brep | 5 | 0 | 2 | 0 | 0 | 2 | 0 |
| transition | openscad | 5 | 0 | 5 | 0 | 0 | 5 | 0 |
| transition | usd-brep | 5 | 0 | 5 | 0 | 0 | 5 | 0 |
| profiles_empty_notes | openscad | 5 | 2 | 5 | 5 | 0 | 5 | 0 |
| profiles_empty_notes | usd-brep | 5 | 0 | 5 | 0 | 0 | 5 | 0 |
| ambiguous | openscad | 5 | 0 | 0 | 5 | 0 | 5 | 0 |
| ambiguous | usd-brep | 5 | 0 | 5 | 0 | 0 | 5 | 0 |
| missing_thickness | openscad | 5 | 0 | 5 | 0 | 0 | 5 | 0 |
| missing_thickness | usd-brep | 5 | 5 | 5 | 5 | 0 | 5 | 0 |

## Timing, recovery, clarification

`mean attempts` for usd-brep counts recipe-schema attempts (construction
corrections are in the rows); `recovered` counts runs whose first attempt
failed and the bounded app retry loop produced a built solid anyway.

| drawing | backend | wall s (mean) | param edit s (median) | mean attempts | recovered | questions |
|---|---|---|---|---|---|---|
| bookend | openscad | 216.0 | 0.55 | 2.6 | 1 | 0 |
| bookend | usd-brep | 141.3 | 2.78 | 1.0 | 1 | 0 |
| wheel | openscad | 187.1 | 1.27 | 3.0 | 0 | 0 |
| wheel | usd-brep | 175.5 | 2.95 | 0.6 | 2 | 0 |
| enclosure | openscad | 64.7 | 0.48 | 1.0 | 0 | 0 |
| enclosure | usd-brep | 108.6 | 2.83 | 0.8 | 0 | 5 |
| curved_handle | openscad | 386.6 | 0.76 | 3.0 | 0 | 0 |
| curved_handle | usd-brep | 102.7 | 18.23 | 0.4 | 0 | 0 |
| transition | openscad | 378.8 | 0.45 | 3.0 | 0 | 0 |
| transition | usd-brep | 107.2 | 3.12 | 1.2 | 1 | 0 |
| profiles_empty_notes | openscad | 268.3 | 0.56 | 3.0 | 0 | 0 |
| profiles_empty_notes | usd-brep | 128.8 | 2.82 | 1.4 | 2 | 0 |
| ambiguous | openscad | 135.6 | 0.47 | 3.0 | 0 | 0 |
| ambiguous | usd-brep | 103.4 | 2.75 | 1.0 | 0 | 5 |
| missing_thickness | openscad | 286.8 | 0.51 | 3.0 | 0 | 0 |
| missing_thickness | usd-brep | 130.2 | 2.97 | 1.0 | 0 | 5 |

## BRep-only capabilities

Richer first-class recipe operations, reported only for `usd-brep` builds.
These are never counted as OpenSCAD failures; OpenSCAD's code-generation path
has no equivalent editable operation and those checks are marked
not-applicable in the plan, not failed.

| drawing | recipes built | loft | shell | arc_pipe | sweep | extrude |
|---|---|---|---|---|---|---|
| bookend | 5 | 0 | 0 | 0 | 0 | 0 |
| wheel | 2 | 0 | 0 | 0 | 0 | 1 |
| enclosure | 4 | 0 | 4 | 0 | 0 | 0 |
| curved_handle | 2 | 0 | 0 | 2 | 0 | 0 |
| transition | 5 | 5 | 0 | 0 | 0 | 0 |
| profiles_empty_notes | 5 | 0 | 0 | 0 | 0 | 5 |
| ambiguous | 5 | 0 | 0 | 0 | 0 | 0 |
| missing_thickness | 5 | 0 | 5 | 0 | 0 | 0 |

Transition was built as a real two-profile `loft` in 5/5 recipes; the missing
thickness shell fixture built as `box + fillet + shell` with an exposed
`thickness` parameter in 5/5 recipes and asked its thickness question 5/5.

## Failure retention and findings

- **Bookend depth**: both backends consistently made the panel ~60 mm deep
  instead of 50 mm (sorted extents and volume fail; 0/10 overall passes).
  BRep passed front-view similarity every trial (0.51–0.81) while the depth was
  wrong — exactly the "right holes, wrong dimensions" case issue #34 warns about.
  Fidelity similarity from the front view cannot see depth; the independent
  measurement checks caught it.
- **Wheel on BRep**: 3/5 hard kernel failures (`disconnected_output`,
  `kernel produced an invalid solid` on the circular spoke pattern). This
  matches the known wheel failure documented in task-14. OpenSCAD built 4/5
  with good similarity (5/5 fidelity) but wrong volume (solid disc instead of
  open spokes in 2 trials).
- **curved_handle on BRep**: 3/5 failed deterministically inside
  `usd_brep 1.0.0` `tessellate(chord_height_tolerance=0.05)` on
  `arc_pipe + cylinder` unions with `ModuleNotFoundError: _omni_solid` (a
  packaging defect in that wheel for this body class). Serial-rebuild evidence
  retained; the 2 completed recipes used two `arc_pipe` segments.
- **Enclosure on BRep**: 4/5 built with the correct window genus but the
  front-view similarity was 0.28–0.35 (open-top silhouette mismatch), so 0/5
  fidelity. OpenSCAD was the opposite: 5/5 fidelity, 0/5 volume (walls and
  cavity not dimensioned like the reference).
- **Transition**: both backends pass front view (1.00 openscad / 0.54 brep) and
  fail the top view (0.25 / 0.19); both built watertight solids with correct
  extents in 5/5. Neither is close on the top-view gate.
- **Ambiguous opening**: BRep asked the through/recess question 5/5 and, after
  the frozen "through" answer, built 5/5 with correct extents, genus 1 and
  volume (13.8 L ±2%), failing only the top-view gate (0.427 vs 0.45).
  OpenSCAD built 2 disconnected components in 5/5 (the product itself rejected
  all five: "mesh has 2 disconnected components").
- **profiles (empty notes)**: the only OpenSCAD overall passes (2/5). BRep
  produced geometry identical to the reference recipe's volume in 5/5 yet
  top-view similarity stuck at 0.313 — suspected BRep top-view render/crop
  artifact, retained as a failure; needs a viewer-side check in a follow-up.
- **missing thickness (known-failure fixture)**: BRep asked the thickness
  question 5/5, applied the frozen 3 mm, built the shell 5/5 and passed
  fidelity 5/5 (its checks exclude genus/volume/extents — no ground truth by
  design). OpenSCAD built solids 5/5 but never reproduced the open hollow form
  (fidelity 0/5).
- **Unsupported operations**: zero `unsupported_construction` or
  `unresolved_design` outcomes. The BRep path attempted every drawing; five
  wheel/curved_handle runs ended as deterministic `build_failed` kernel
  outcomes and are reported above, not skipped.
- **Targeted edits**: 0/80 runs had a selectable targeted-edit target (the
  selection catalog exposes box-cutter pockets and outer vertical edges; none
  of these parts have box-cutter pockets). The targeted-edit path itself is
  covered by task-15 evidence; here it is reported not-applicable, not failed.
- **Product gate vs harness gate**: the OpenSCAD agent accepted
  (7/40)
  runs that failed the stricter frozen checks (mostly volume/extents misses).
  The 70-score accept gate and the 0.45 per-view similarity floor are
  calibration candidates, tracked with the routing issue proposed in
  [DECISION.md](../DECISION.md).

## Limits

Five trials per cell estimate pass rates only coarsely. One model, one host,
one day. Reference-based checks use the frozen task-01 corpus (synthetic
engineering drawings, not handwriting). STL bytes are archived for failures and
small runs; every run STL is sha256-pinned in its row.
