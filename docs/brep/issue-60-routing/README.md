# Issue #60 — Data-driven backend routing (opt-in `Auto`)

## What ships
- `doodle_to_cad/backend_router.py` — pure, deterministic rule function. No LLM,
  no randomness: same drawing bytes -> same recommendation.
- Form default is UNCHANGED (OpenSCAD). Users opt in with "Auto (data-driven
  rules)". The recommendation and its rule text are shown in the result panel
  and persisted to `results/<id>/routing.json` for audit.
- Rules, first match decides (all matches are still recorded as telemetry):
  K same drawing already hit a usd_brep kernel failure -> OpenSCAD
  F notes request fillet/chamfer/loft/shell -> usd-brep (5/5 vs 0/5, #34)
  V >=2 view groups -> OpenSCAD (24/40 vs 11/40 fidelity, #34)
  C >=6 circular profiles or >=8 closed internals -> OpenSCAD (both kernel
    defect classes live on these bodies, #61)
  D single view + explicit dimension -> usd-brep (5/5 vs 0/5, #34)
  - default -> OpenSCAD (incumbent)
- Escape hatch: the manual OpenSCAD/Direct-BRep choices remain; Auto never
  overrides an explicit pick. Kernel history (rule K) reads prior job.json
  error rows with `kernel_unavailable` or the two raw kernel signatures,
  matched by sha256 of the stored input.png — a drawing that crashed the
  kernel never gets sent back to it automatically.

## Validation (machine-auditable)
1. `scripts/validate_routing.py` (offline, frozen #34 set, no LLM/kernel):
   8 drawings, **0 disagreements**. 2 agree (bookend, enclosure: recommended
   OpenSCAD, which was the ONLY backend with accepted rows), 6 neutral
   (neither backend ever accepted). Honest limit: every frozen sheet is
   multi-view and was submitted WITHOUT notes/dimension, so rules F and D
   are not exercised there — they are covered by unit tests and the live demo.
   Output: `data/routing-matrix.json` (rerun:
   `PYTHONPATH=. .venv/bin/python scripts/validate_routing.py`).
2. `scripts/demo_routing.py` (live app, this server's results dir):
   single-view box + 80 mm dimension -> rule D -> Direct BRep (solid built);
   two-view circle grid -> rule V -> OpenSCAD (accepted result).
   Evidence: `data/live/*.json` + `results/*/routing.json`.
3. `tests/test_backend_router.py` — 14 tests: rule table, priority order,
   telemetry shape, kernel-history scan (same-image + kernel code only;
   non-kernel errors and other drawings ignored), frozen curved-handle class
   routed away from the kernel.
4. Bug found and fixed by the live demo: pre-creating `results/<id>/` broke
   the atomic publish rename in `recipe_jobs.py` (`os.replace`/`rename` needs
   a missing target). `routing.json` is now written only after publish
   (openscad path: after `generate` returns; direct path: inside
   `_save_brep_result`, which runs in the temp dir that is renamed into
   place). Rerun the demo to confirm: `DEMO PASS`.
5. `logs/full-suite.txt` — full pytest output on this branch.

## Telemetry for later re-calibration
Every Auto job records the firing rules and the signals dict
(view_group_count, profile counts, notes keywords, dimension, history hit) in
`routing.json`. When the next comparison matrix lands, recompute rules per
drawing exactly like `scripts/validate_routing.py` does and diff against
these files before changing any threshold.
