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
`build_contract.classify_kernel_crash` matches two exact signatures and nothing else:

1. `No module named '_omni_solid'` -> `kernel_unavailable`, advice "Retry with the
   OpenSCAD backend" plus the reproducer fixture sha256.
2. `kernel produced an invalid solid` -> `kernel_unavailable` with the same advice
   but explicitly no reproducer claim. Evidence tier: 2 frozen rows
   (`wheel/usd-brep/trial-04|05`, independent recipes, identical message); the
   harness kept the error rows but not the failing recipes. A hand-built probe of
   8 mutations of the proven wheel fixture did NOT reproduce it
   (`logs/invalid-solid-probe.log`); one mutation reproduced the `disconnected_output`
   family of wheel trial-03 instead. Honest status: unconfirmed trigger class,
   containment is message-based only.

A generic `ModuleNotFoundError` keeps `build_failed` (no retry-hint laundering).
`tests/test_brep_kernel_containment.py` — 12 tests incl. planted errors: fake
crashing worker fires the classifier; unrelated crash maps to generic; successful
fake never misclassified; near-miss wordings ("invalid geometry", reordered
"invalid solid") do not fire.

## Files
- `UPSTREAM-REPORT.md` — filing text for usd-brep maintainers (measured behavior only)
- `logs/determinism.log`, `logs/shrink-ladder.json|.log`, `logs/fixture.sha256`,
  `logs/invalid-solid-probe.log`
- `scripts/probe_invalid_solid.py` — the 8-mutation negative probe, rerunnable
- `environment.json` — host/wheel/git fingerprint
- `logs/full-suite.txt` — full pytest output
- `audit.py` — rerunnable verification of every claim above
