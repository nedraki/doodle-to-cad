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

## Headline numbers (recomputed by audit.py)

| backend | done | product-accepted | build OK | GT overall pass | median wall |
|---|---|---|---|---|---|
| openscad | 44/46 | 22/44 (50%) | 42/44 (95%) | 2/44 (5%) | 193 s |
| usd-brep | 31/46 | 0/31 (0%) | 31/31 (100%) | 0/31 (0%) | 113 s |

Questions asked during trials: openscad 0 (ask off by design), usd-brep 9
(recipe clarifications, answered by policy).

## Strengths (evidence-backed)

- **OpenSCAD build reliability:** 95% watertight single-component; simple
  prisms/plates/brackets score 95–100 repeatedly (004 plate 99.9×2,
  007 bracket 100, 010 nameplate 99.5, 102 knob 96.7).
- **Chamfer feature fully passes GT:** bevelled_block 2/2 overall_pass.
- **Wheel is healthy at its proper size:** both trials at 120 mm pass
  extents AND genus 8 (spokes present). The pre-fix "spokes missing" reading
  was a plan-dimension artifact, caught and corrected with the failure
  published — see `plan_revisions`.
- **Gate precision (#62/#67 in production):** the top failures are specific
  and actionable — blind-pocket detection ("mesh has 0 true through-holes,
  cut all the way through"), opening-position mismatches with cad_mapping
  hints, degenerate-axis detection. Zero silent passes observed: every
  accepted mesh passed topology+openings+projections gates.
- **BRep kernel is safe-failing:** 100% of completed usd-brep builds are
  watertight; when it cannot build (organic vase: no lathe op) it refuses
  with a precise message instead of emitting a wrong solid. 15 errors are
  clean refusals or contained kernel faults (1 = published #61 class).

## Weaknesses (evidence-backed)

- **usd-brep never reaches a passed verdict on these drawings:** 30/31
  `status=failed`, 1 `unverified`. Failure classes: top projection 17×,
  front projection 15×, front openings 14×, opening positions 10×. The
  tightened #62/#67 gates reject candidates that previously landed as
  "unverified". Detailed-feature generation on the direct path is not
  release-ready; OpenSCAD remains the accepted path.
- **usd-brep robustness:** 15/46 trials ended in errors, largest class
  `Construction plan rejected: Unsupported clarification` (6×), plus
  world-frame rejections (3×), 1 malformed recipe JSON, 2 kernel faults
  (1 contained).
- **Thickness lottery, quantified:** with ask off, openscad `volume_pass`
  is 5% and `extents_pass` 11% against GT — the product *accepts* 22 meshes
  whose unconstrained axes are invented. This is the measured motivation
  for the #68 question flow (which is exercised separately in
  `docs/brep/issue-68-size-ask/` with the 4 mm jeep result).
- **Hard cases still fail on both backends:** 003 grille (openings),
  101 bltouch bracket (both trials rejected), 103 motor holder, 104 cable
  holder, 013 wedge. Arc handle and rect→round transition score 87–94 but
  fail GT checks.
- **Greek vase (lathe class):** genuinely unsupported on the BRep path —
  no revolve/lathe operation (recorded as refusal, not silent skip).

## Reproduce

```
# 1) trials (resume-safe; existing row.json are skipped)
DOODLE_BREP_PYTHON=$PWD/workers/brep/.venv/bin/python PYTHONPATH=. \
  DOODLE_RESULTS_DIR=results/bench-final .venv/bin/python \
  scripts/evaluate_brep.py trials --plan docs/brep/bench-final/TRIAL-PLAN.json \
  --out docs/brep/bench-final/runs --port 8132
# 2) tables
PYTHONPATH=. .venv/bin/python docs/brep/bench-final/aggregate.py
# 3) claim gate (exits non-zero if any README/RESULTS number drifts)
PYTHONPATH=. .venv/bin/python docs/brep/bench-final/audit.py
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
