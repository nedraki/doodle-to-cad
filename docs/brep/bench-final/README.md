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

> **Rev errata (2026-10-19, external reviews by Codex @ 907eed7 and @ 820800f).**
> Round 2 (@ 820800f) fixed: absolute paths in `provenance.json` (the audit
> could read another checkout — now checkout-relative and enforced), panel
> input/GT source hashes recorded but unverified (now verified), the
> "complete-GT-match" label (renamed ref dims/topo/vol pass, kept separate
> from `automatic overall_pass`), and footer overlap in montages.
> Round 1 (@ 907eed7) fixed: Three
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
>
> **Round 3 hardening (issue #79).** The audit could still read rows from the
> author's `/tmp/doodle-brep-32` tree and treated a total row count as proof
> of coverage. Now: every artifact (rows, meshes, inputs, views, references
> and their source models, montages, the plan) is sha256-sealed in
> `MANIFEST.json` and the audit refuses to run against a checkout whose bytes
> differ (abort names trial + path; a corrupt row aborts too — nothing is
> skipped and no passing report is written). Cell coverage is the frozen
> plan's exact drawing/backend/trial set (missing, duplicate and unexpected
> cells are each detected). Every metric is defined once in `metrics.py`,
> which generates both README and RESULTS tables; audit recomputes and
> compares verbatim. Completion, valid solid, drawing check, reference
> dims/topo/vol and user acceptance stay separate measurements; absent
> references are not-applicable (never failures) with the n/a count shown;
> end-to-end rates run over ALL submitted trials and conditional rates are
> labeled. The generators no longer hardcode the author's directory. Genus is
> never described as a spoke count and matching extents+volume is never
> described as complete shape agreement (guarded by wording checks).

## Headline numbers (recomputed by audit.py from metrics.py)

Acceptance = the frozen plan's definition (`TRIAL-PLAN.json`
`product_acceptance`): openscad `accepted` (score ≥ 70); usd-brep
`status != 'failed'` — for BRep that means **automatic checks passed, still
unverified**, never full acceptance (the path never auto-accepts fidelity).
Both tables recompute from ONE definition (see "Metric definitions" below):
the first is end-to-end over ALL submitted trials, the second is conditional
over completed trials only. Absent references are *not applicable*, never
counted as failures; every cell shows numerator/denominator and the n/a count.

`ref dims/topo/vol` = extents AND genus AND volume all true against a real
reference (39 openscad rows have references; 3 drawings are
`no_ground_truth` and only get automatic gates). **This is NOT a full model
match**: both `solid_transition` rows still FAIL projection/fidelity and
`overall_pass` — they are dimension/connection-count/volume passes only.
Matching outside dimensions and volume can still miss feature placement.
The separate `automatic overall_pass` metric (bevelled_block ×2) includes
`no_ground_truth` rows and is not a reference match; the two totals coincide
at 2 by accident and must never be conflated (Codex review round 2).
The `006_stepped_knob` BRep row is `unverified`: reported separately from
failed and from full acceptance. Under the stricter (unsatisfiable)
`status=='passed'` the historical count stays 0 and is published labeled.
User acceptance is NOT collected in this dataset — a score is never user
acceptance (the review workflow lands in #80).

<!-- AUDIT:TABLE:BEGIN (generated by aggregate.py from metrics.py - audit.py compares verbatim) -->
End-to-end rates over ALL submitted trials (every trial the harness was asked to run, including errors and refusals):

| backend | submitted | completed | valid solid | drawing/fidelity | ref dims/topo/vol (X=no-ref) | plan-accepted | unverified (BRep) | user acceptance |
|---|---|---|---|---|---|---|---|---|
| openscad | 46 | 44/46 (96%) | 42/46 (91%) | 28/46 (61%) | 2/46 (4%) (5 no-ref) | 22/46 (48%) | 0/46 (0%) | not collected |
| usd-brep | 46 | 31/46 (67%) | 31/46 (67%) | 6/46 (13%) | 0/46 (0%) (4 no-ref) | 1/46 (2%) | 1/46 (2%) | not collected |

Conditional rates over COMPLETED trials only (clearly labeled: these exclude errored trials from the denominator):

| backend | done | valid solid | drawing/fidelity | ref dims/topo/vol (X=no-ref) | plan-accepted | strict full accept (hist.) | median wall (s) |
|---|---|---|---|---|---|---|---|---|
| openscad | 44 | 42/44 (95%) | 28/44 (64%) | 2/44 (5%) (5 no-ref) | 22/44 (50%) | 0/44 (0%) | 185 |
| usd-brep | 31 | 31/31 (100%) | 6/31 (19%) | 0/31 (0%) (4 no-ref) | 1/31 (3%) | 0/31 (0%) | 122 |
<!-- AUDIT:TABLE:END -->

## Metric definitions (single source: `metrics.py`)

<!-- AUDIT:METRICS:BEGIN (generated from metrics.py - audit.py compares verbatim) -->
Every metric is defined once, in `metrics.py`; the tables above recompute
from these definitions. A metric records numerator/applicable-denominator
and keeps these separations: completion != valid solid != drawing check
!= reference match != user acceptance.

- **completed** (`completion`, basis: submitted): Trial reached the terminal state job_status == 'done' with a published result record. Error and cancelled trials are outcomes, not completions, and stay published.
- **valid solid** (`valid_solid`, basis: done): Harness re-measured the run STL independently: watertight AND exactly 1 component (checks.build_success). This measures the solid only; it says nothing about drawing agreement.
- **drawing/fidelity** (`drawing_fidelity`, basis: done): Harness re-ran projection scores on (source drawing, run geometry evidence, run view renders); every assigned direction scored >= 0.45. Drawing agreement only; not dimensions, not volume, not a reference match.
- **ref extents** (`ref_extents`, basis: done_with_reference): Sorted run extents vs sorted reference extents, every axis within 2%. Applies only where a real reference exists.
- **ref genus** (`ref_topology`, basis: done_with_reference): genus == frozen reference genus where a ground truth exists. Genus counts topological connections (tunnels/holes); it does NOT prove feature placement and never establishes a spoke or opening count.
- **ref volume** (`ref_volume`, basis: done_with_reference): abs(volume - reference volume) / reference volume <= 0.02 where a ground truth exists.
- **ref dims/topo/vol** (`reference_dims_topo_vol`, basis: done_with_reference): extents AND genus AND volume all pass against a real reference. This is NOT complete shape agreement: matching outside dimensions, connection count and volume can still miss feature placement, and such rows may fail the projection gates.
- **automatic overall_pass** (`automatic_overall_pass`, basis: done): checks.overall_pass == true: every automatic gate the harness could evaluate is green. Includes no-ground-truth rows, so it is NOT a reference match and never called one.
- **plan-accepted** (`plan_acceptance`, basis: submitted): Frozen-plan product acceptance (TRIAL-PLAN.json product_acceptance): openscad result.success (agent accepted, score >= 70); usd-brep evaluation.status != 'failed'. For usd-brep 'not failed' means automatic checks passed, still unverified - NOT full acceptance. Counted over ALL submitted trials (end-to-end) and over completed trials (conditional).
- **strict full acceptance** (`strict_full_acceptance`, basis: submitted): usd-brep evaluation.status == 'passed'. The current evaluator never emits 'passed' (brep_checks.py emits failed|unverified), so this count is 0 by design; it is published under its historical frozen-plan label, not silently changed.
- **automatic-checks unverified** (`automatic_checks_unverified`, basis: submitted): usd-brep rows with evaluation.status == 'unverified': automatic checks passed, no human verification yet. Reported separately from failed and from full acceptance.
- **user acceptance** (`user_acceptance`, basis: submitted): User decision 'accepted' recorded on the review page (#80) bound to the displayed artifact hash. Never derived from a score. Not collected in this dataset until decisions exist.
<!-- AUDIT:METRICS:END -->

Questions asked during trials: openscad 0 (ask off by design), usd-brep 9
(recipe clarifications, answered by policy).

## Strengths (evidence-backed)

- **OpenSCAD build reliability:** 95% watertight single-component; simple
  prisms/plates score 95–100 repeatedly (004 plate 99.9×2, 010 nameplate
  99.5, 102 knob 96.7).
- **Reference dims/topology/volume pass exists, but is rare:**
  `solid_transition` (rect→round) passes extents+genus+volume against the
  certified #34 reference on both trials (score 94.4×2) — while still
  failing projection/fidelity. Bevelled_block passes all AUTOMATIC gates
  both trials but has no reference — shape is NOT verified. These two
  counts are different measurements (both happen to equal 2).
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
  (genus 8 counts tunnels; it does NOT prove 8 spokes — the opening detector
  measured 8 openings vs 9 required and the position checks failed) but
  fails volume: +18% (openscad
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
| `003_front_grille_multiview_t1.png` | failed | genus 8 recorded (connection count only — it does not prove hole placement); outline+projections wrong, openings 8≠required 9, positions failed |
| `wheel_t2.png` | failed | genus 8 (connection count only — feature placement NOT proven by genus); front projection + opening positions failed; volume +19% vs reference |
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
# 2) tables (atomic writes; re-syncs the generated blocks in README.md)
PYTHONPATH=. python3 docs/brep/bench-final/aggregate.py
# 2b) re-seal the evidence manifest after ANY evidence change (see trust_note)
python3 docs/brep/bench-final/make_manifest.py
# 3) claim gate (exits 1 if any README/RESULTS number drifts or any hash
#    binding breaks; exits 2 with trial+path on a missing/corrupt artifact,
#    writing no report; pass runs record audit-result.json atomically with
#    an environment fingerprint)
python3 docs/brep/bench-final/audit.py
# 3b) adversarial self-test: plants defects in disposable copies (raw
#     tamper, re-sealed tamper, removed/duplicated cells, image swap, fake
#     GT reference, acceptance flip, README drift) and requires the audit to
#     CATCH every one — a check that cannot fail is decoration
python3 docs/brep/bench-final/audit_selftest.py
# 4) montages (needs wall app on :8114; refuses on hash mismatch)
PYTHONPATH=. .venv/bin/python docs/brep/bench-final/make_fail_montages.py
```

Phase A (kernel features, no model): `docs/brep/bench-features/` rerun on
this head — 10/10 jobs (`logs/run-merged-head.log`), frozen-evidence audit
13/13 after restoring committed artifacts.

## Limits

- `environment.json` was declared in the plan's `evidence_layout` but the
  harness never wrote it at trial end. The execution environment survives in
  the frozen plan's `model_settings` and the sealed `logs-trials.log`
  server-model lines; the audit cross-checks they agree. This gap is
  disclosed in `MANIFEST.json` — not papered over with reconstructed data.
- 2 trials/cell — variance signals (012 grille identical scores) are
  indicative, not statistical.
- openscad trials answered no questions (ask off); a re-run with
  `ask_dimensions=true` + a GT answer policy would isolate the #68 uplift.
- usd-brep verdict semantics carry no numeric score (`product.status`), so
  backend score comparison uses openscad scores only.
- 12 cells of the original (wrong-dimension) attempt were deleted before the
  corrected rerun; the dataset proves complete coverage of the CORRECTED
  experiment, not preservation of every original attempt.
