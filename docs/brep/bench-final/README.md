# bench-final — product evaluation on the merged BRep line

**Date:** 2026-10-19 · **Head:** `3f5d76d` (brep-integration, incl. #61/#62/#67/#68)
**Matrix:** 23 drawings × 2 backends × 2 trials = **92 published rows** (zero dropped).
**Harness:** `scripts/evaluate_brep.py trials` (in-process server 127.0.0.1:8132,
local vLLM, parallel 3). **Plan:** `TRIAL-PLAN.json` (frozen before trials; one
honest revision logged in `plan_revisions`: wheel/handle/transition dimensions
100→120/54/60 to match the certified #34 plan; 12 cells rerun).

Corpus: the 17 benchmark cases (`benchmarks/cases/*`, incl. re-inked 003) +
6 feature drawings (chamfer block, rounded housing, arc handle, rectangular
sweep, rect→round transition, spoked wheel). References: 17 trusted
ground-truth STLs + 3 certified #34 references + 3 honest `no_ground_truth`
(`references/reference-measurements.json`). Unattended trials run with
`ask_missing_dimensions=false`, so the openscad numbers measure the product
**without** the #68 answer loop — see "thickness lottery" below.

> **Rev errata (2026-10-19, external review by Codex @ 907eed7).** Three
> reporting defects in the first version were confirmed against the rows and
> are corrected here: (1) bevelled_block was called a "GT pass" but has NO
> ground-truth reference — its `overall_pass` covers build+automatic-gates
> only; the true complete-reference match count is openscad **2/44**
> (`solid_transition` both trials), not the bevelled pair. (2) The BRep
> acceptance was reported as 0/31 using `status=='passed'`, which the
> evaluator can never emit; the **frozen plan** defines usd-brep acceptance
> as `status != 'failed'` → **1/31** (`006_stepped_knob`: automatic checks
> passed, still `unverified` — NOT fully accepted). (3) The first montage
> revision picked meshes by sorting `brep-*` run dirs and rendered edited
> revisions for 2 of 6 rows; montages are now rendered ONLY from the
> harness-archived `runs/.../stl/model.stl` after sha256 verification
> against the row (75/75 archived STLs match their rows). Visual captions
> that were based on impression, not measurement, are replaced by measured
> row data. Codex independently confirmed: full 92-cell matrix, no selective
> omission, 15 usd / 2 os errors, all row↔STL hashes, the corrected 12 cells.

## Headline numbers (recomputed by audit.py)

Acceptance = the frozen plan's definition (`TRIAL-PLAN.json`
`product_acceptance`): openscad `accepted` (score ≥ 70); usd-brep
`status != 'failed'` — for BRep that means **automatic checks passed, still
unverified**, never full acceptance (the path never auto-accepts fidelity).

| backend | done | plan-accepted | build OK | complete GT match¹ | median wall |
|---|---|---|---|---|---|
| openscad | 44/46 | 22/44 (50%) | 42/44 (95%) | 2/44 (5%) — `solid_transition` ×2 | 193 s |
| usd-brep | 31/46 | 1/31 (3%)² | 31/31 (100%) | 0/31 (0%) | 113 s |

¹ extents AND genus AND volume all pass against a real reference (39 openscad
rows have references; 3 are `no_ground_truth` and only get automatic gates).
² `006_stepped_knob` trial-1: `status=unverified` = "automatic checks
passed; still unverified". Under the stricter (unsatisfiable)
`status=='passed'` the count is 0; both were published to avoid spin.

Questions asked during trials: openscad 0 (ask off by design), usd-brep 9
(recipe clarifications, answered by policy).

## Strengths (evidence-backed)

- **OpenSCAD build reliability:** 95% watertight single-component; simple
  prisms/plates score 95–100 repeatedly (004 plate 99.9×2, 010 nameplate
  99.5, 102 knob 96.7).
- **Complete ground-truth match exists, but is rare:** `solid_transition`
  (rect→round) passes extents+genus+volume against the certified #34
  reference on both trials (score 94.4×2). Bevelled_block passes all
  AUTOMATIC gates both trials but has no reference — shape is NOT verified.
- **Gate precision (#62/#67 in production):** failures are specific and
  actionable — blind-pocket detection, opening-position mismatches with
  cad_mapping hints, degenerate-axis detection. Zero silent passes observed:
  every accepted mesh passed topology+openings+projections gates.
- **BRep kernel is safe-failing:** 100% of completed usd-brep builds are
  watertight; when it cannot build (organic vase: no lathe op) it refuses
  at the model stage with a precise message instead of emitting a wrong
  solid. 15 errors are clean refusals or contained kernel faults
  (1 = published #61 class).

## Weaknesses (evidence-backed)

- **usd-brep reaches plan-acceptance on 1/31 finished trials** (and that one
  is `unverified`, not accepted): 30/31 `status=failed`. Failure classes:
  top projection 17×, front projection 15×, front openings 14×, opening
  positions 10×. Detailed-feature generation on the direct path is not
  release-ready; OpenSCAD remains the accepted path.
- **usd-brep robustness:** 15/46 trials ended in errors, largest class
  `Construction plan rejected: Unsupported clarification` (6×), plus
  world-frame rejections (3×), 1 malformed recipe JSON, 2 kernel faults
  (1 contained).
- **Thickness lottery, quantified:** with ask off, openscad `volume_pass`
  is 2/39 (5%) and `extents_pass` 11% where a reference exists — the
  product *accepts* 22 meshes whose unconstrained axes are invented. This
  is the measured motivation for the #68 question flow (exercised
  separately in `docs/brep/issue-68-size-ask/` with the 4 mm jeep result).
- **Wheel volume excess on BOTH backends:** wheel passes extents+genus
  (genus 8 = all 8 spokes present) but fails volume: +18% (openscad
  50977 mm³) and +19% (usd-brep 51266 mm³) against the 43128.5 mm³
  certified reference. The earlier "wheel is healthy" reading was an
  overclaim; the wheel needs the volume investigation (opening detector
  expecting far fewer openings than 8 spoke gaps is also suspect —
  evaluation/input-interpretation issue).
- **Hard cases still fail on both backends:** 003 grille (outline + opening
  count), 101 bltouch bracket (plain plate replaces bracket), 103 motor
  holder, 104 cable holder, 013 wedge. Arc handle fails top+right
  projections (drawn straight legs absent).
- **Greek vase (lathe class):** genuinely unsupported on the BRep path —
  no revolve/lathe operation; refusal is recorded at the model stage, not
  a silent skip.

## Failure montages (`images/`)

`make_fail_montages.py` composes each row as **input drawing | usd-brep built |
ground truth**. Provenance is mechanical: the rendered mesh is the
harness-archived `runs/<drawing>/usd-brep/trial-NN/stl/model.stl`, sha256
verified against the row BEFORE rendering (mismatch aborts);
`images/provenance.json` binds every montage's sha256 to its row sha256, mesh
sha256 and panel sources; the in-image footer prints the row's measured
genus/extents/volume and its own failure text. `audit.py` recomputes those
hashes — swapping any image, or editing a row, fails the audit.

| image | verdict | measured defect (from the row) |
|---|---|---|
| `003_front_grille_multiview_t1.png` | failed | genus 8: holes/slots ARE built; outline+projections wrong, openings 8≠required 9, positions failed |
| `wheel_t2.png` | failed | genus 8 (all spokes present); front projection + opening positions failed; volume +19% vs reference |
| `constant_radius_handle_t1.png` | failed | genus 0, 48×24×8 mm; drawn straight legs absent; top + right projections failed |
| `007_angle_bracket_holes_t1.png` | failed | genus 3, volume 15250 mm³ ≈ solid 80×40×5 plate minus 3 holes: the L-shape was never built |
| `101_bltouch_bracket_t1.png` | failed | volume 8000 mm³ = exactly 40×50×4 plain plate: the bracket features were never built |
| `002_greek_vase_silhouette_t1.png` | error | model-stage refusal (ops list has no lathe/revolve); no mesh, published not skipped |

## Reproduce

```
# 1) trials (resume-safe; existing row.json are skipped)
DOODLE_BREP_PYTHON=$PWD/workers/brep/.venv/bin/python PYTHONPATH=. \
  DOODLE_RESULTS_DIR=results/bench-final .venv/bin/python \
  scripts/evaluate_brep.py trials --plan docs/brep/bench-final/TRIAL-PLAN.json \
  --out docs/brep/bench-final/runs --port 8132
# 2) tables
PYTHONPATH=. .venv/bin/python docs/brep/bench-final/aggregate.py
# 3) claim gate (exits non-zero if any README/RESULTS number drifts,
#    or any montage image/row/mesh hash binding breaks)
PYTHONPATH=. .venv/bin/python docs/brep/bench-final/audit.py
# 4) montages (needs wall app on :8114; refuses on hash mismatch)
PYTHONPATH=. .venv/bin/python docs/brep/bench-final/make_fail_montages.py
```

Phase A (kernel features, no model): `docs/brep/bench-features/` rerun on
this head — 10/10 jobs (`logs/run-merged-head.log`), frozen-evidence audit
13/13 after restoring committed artifacts.

## Limits

- 2 trials/cell — variance signals (012 grille identical scores) are
  indicative, not statistical.
- openscad trials answered no questions (ask off); a re-run with
  `ask_dimensions=true` + a GT answer policy would isolate the #68 uplift.
- usd-brep verdict semantics carry no numeric score (`product.status`), so
  backend score comparison uses openscad scores only.
- 12 cells of the original (wrong-dimension) attempt were deleted before the
  corrected rerun; the dataset proves complete coverage of the CORRECTED
  experiment, not preservation of every original attempt.
