# Issue #61 — usd_brep 1.0.0 tessellation crash: reproducer, characterization, containment

## Defect (measured, not assumed)
`usd-brep==1.0.0` dies during tessellation with
`ModuleNotFoundError: No module named '_omni_solid'` when a boolean **union**
combines a **180-degree `arc_pipe`** (half-torus tube sweep) with a solid crossing
its terminal cap. Deterministic: 3/3 serial rebuilds (`logs/determinism.log`).
Frozen #34 data holds 3 crash rows — all `curved_handle/usd-brep` trials 01-03
(`code: build_failed`, raw worker-level). The earlier "#61 cluster on spoke/circular
patterns" phrasing is corrected by this dossier: spokes build fine
(`docs/brep/bench-features/artifacts/wheel`, 8-spoke recipe); the trigger class is
the arc_pipe-cap union.

## Minimal reproducer
`scripts/repro_omni_solid.py` + `scripts/fixtures/omni_solid_minimal.recipe.json`
(sha256 `0e0fa35a...e14cdf`, full hash in `logs/fixture.sha256`), driven through the
production worker entry `workers/brep/build.py`:

    DOODLE_BREP_PYTHON=$PWD/workers/brep/.venv/bin/python .venv/bin/python scripts/repro_omni_solid.py

Verdict line must read `3/3 behaved as expected (expected=crash,
signature="No module named '_omni_solid'")`; exit 0.

## Characterization ladder (`logs/shrink-ladder.json`, 20 cases, 0 misbehaving)
Arc alone builds; cylinder alone builds; box∪arc builds; arc90∪cyl builds;
180° arc∪cylinder-on-cap crashes; angle/axis/flip/difference probes recorded verbatim
(including `unknown` outcomes). Shrink path: full generated recipe -> slim -> minimal
v1 (3 ops), each step logged.

## Containment (shipped)
`build_contract.classify_kernel_crash` matches ONLY the exact signature and maps it
to FailureCode `kernel_unavailable` with advice "Retry with the OpenSCAD backend"
plus the fixture sha256 (`build_contract.py`, `workers/brep/build.py` main guard).
A generic `ModuleNotFoundError` keeps `build_failed` (no retry-hint laundering).
`tests/test_brep_kernel_containment.py` — 10 tests incl. planted errors: fake
crashing worker fires the classifier; unrelated crash maps to generic; successful
fake never misclassified.

## Files
- `UPSTREAM-REPORT.md` — filing text for usd-brep maintainers (measured behavior only)
- `logs/determinism.log`, `logs/shrink-ladder.json|.log`, `logs/fixture.sha256`
- `environment.json` — host/wheel/git fingerprint
- `logs/full-suite.txt` — 261 passed
- `audit.py` — rerunnable verification of every claim above
