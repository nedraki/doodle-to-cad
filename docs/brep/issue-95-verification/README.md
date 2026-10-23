# Issue #95 — independent verification of the merged revolve work

Reviewer: Hermes demo-producer session, 2026-10-22 (evening). Base:
`brep-integration` at `88660e0` (post #96/#98/#99/#100). Fresh worktree,
worker Python 3.12 with `usd-brep==1.0.0`, model untouched (no live
generations were run in this audit). Rollback anchors: tags
`checkpoint/pre-issue95-verify` (`88660e0`),
`checkpoint/after-plan-raw-retention` (`742b383`),
`checkpoint/after-abc-checker` (`4b59926`).

## Verdicts on the Codex "solids of revolution" report

| # | Hypothesis | My verdict | What I re-checked myself |
|---|---|---|---|
| 1 | Missing exposed revolution op | **Confirmed — and genuinely fixed by #95** | `revolve` present in `FIELDS` and worker dispatch (`sm.rotational_sweep`); prompt + intent guidance present; archived trial-1 vase profile rebuilt **through the product adapter**: volume bit-identical to the native probe (relative diff 0.0), watertight, 1 component, USD round-trip passed |
| 2 | Model/planning failure | Confirmed as secondary; **residual open** | 2 of 9 bench-revolve rows still `invalid_recipe` (gate rejections). The gate itself is unchanged and plausibly correct; diagnosis was impossible because rejected plans were never persisted — fixed here, see below |
| 3 | Cylinder-union constraints | Not touched — separate family, agrees with report | n/a |
| 4 | Kernel lacks revolutions | Contradicted (agrees) | `/tmp/brep-revolution-investigation/` probes inspected; my adapter rebuild reproduces the native volumes |
| 5 | Invalid profiles / seam defects | Unsupported as cause (agrees) | Validator audit below found guards for every listed defect class |

## Machine checks I ran (all green)

- Full suite at `88660e0`: **355 passed, 1 skipped** twice, matching runs
  (the one skip is `test_brep_capability_evidence.py`, documented missing
  optional requirements). After the two fixes merged here: **356 passed,
  1 skipped**.
- `make_comparison.py` regenerates the bench-revolve table byte-identical
  from committed rows; per-trial `environment.json` present 24/24.
- `revolve_profile.py` guards read line by line: closure, r≥0, repeated
  vertices, axis-only loops, adjacent spike/fold-back, non-adjacent
  touch/cross, zero area — all fail closed with `ValueError`; the in-suite
  derived-seed fuzz (300 random loops) asserts ValueError-only escapes.
- Harness deterministic mode (3 reference parts) exits 0 through the real
  worker with the changed script.
- ABC draft cells: 8/8 GT meshes watertight, one component, winding
  consistent, max extent exactly 120.0 mm; recorded unit inference
  satisfies raw_extent × scale_to_mm = 120000 on all 8.

## Fixes merged in this audit

1. **Construction-plan raw retention** (branch
   `hermes/issue-95-plan-raw-retention`, merge `742b383`).
   `scripts/evaluate_brep.py` copied `construction-plan.json` (written only
   when validation passes) but dropped the `construction-plan*.raw.txt`
   transcripts `_json_call` had already written — so gate-rejected plans
   (`006` trial-02, `009` trial-01) left no witness of *why* the gate
   fired. `_copy_evidence` now carries every `construction-plan*` raw
   transcript, append-only (refuses overwrite), with a regression test in
   the issue-#85 choke-point style.
2. **ABC draft checker** (branch `hermes/abc-draft-checker`, merge
   `4b59926`): `scripts/check_abc_drafts.py` makes the draft claims
   re-verifiable (they were staged by a script that was never committed).
   Offline checks exit 0; the sha256 re-download against
   archive.nyu.edu bitstreams honestly reports UNREACHABLE (exit 2) while
   the archive REST is degraded — the run from this session found all 8
   endpoints returning 500/empty.

## Open, deliberately not "fixed" here

- The 2 `invalid_recipe` rows: root cause needs one live re-run (the fix
  above captures the raw plan next time). Live generations are on hold by
  user instruction.
- **Vase extents check is unpassable by either backend** at the frozen
  reference (openscad 107.53 mm vs GT 102.5 mm also fails extents; the new
  revolve rows build honest 80–90 mm bellies). This is reference/ink
  calibration — a user decision, not a code bug. Frozen references were
  not touched.
- `make_comparison.py` prints `environment.json present: False` while
  checking `runs/environment.json`, a file that exists in neither
  bench-final nor bench-revolve (harness #85 only ever wrote per-trial
  copies). Cosmetic; no claims depend on it.
- ABC external re-verification (sha256) pending archive recovery; retry
  loop was running during this session.

## Reproduce

    git worktree add <dir> brep-integration
    cd <dir> && uv sync --extra dev
    cp <main-checkout>/.env .env
    DOODLE_BREP_PYTHON=<main-checkout>/workers/brep/.venv/bin/python \
      PYTHONPATH=$PWD .venv/bin/python -m pytest tests/ -q
    PYTHONPATH=$PWD .venv/bin/python scripts/check_abc_drafts.py --no-network
