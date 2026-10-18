# Task 16 — Worker release readiness (issue #33)

Question answered here: can a person other than the developer install the BRep
worker, get told what is wrong when something is missing, trust that a
cancelled or crashed worker stays contained, and know exactly which exported
files are supported?

## Issue checklist, item by item

| Issue check | Status | Evidence |
|---|---|---|
| Install and generate a part from a clean environment | **Pass** | `install-check.json` — 8/8 steps: throwaway venv outside the repo, `uv venv --python 3.12`, pinned `requirements.txt`, imports, real box build, watertight STL + USDA. Re-run: `scripts/check_worker_install.py`. |
| Concurrent jobs, cancel a job, simulate a worker crash | **Pass (module level)** | `tests/test_worker_release.py`: cancellation kills the worker pid (asserted via `/proc/<pid>` gone) and leaks no staging dirs; a crashing stub worker yields `build_failed` and cannot publish or modify the run directory. Recipe-job cancellation already kills the whole process group (`recipe_jobs.py` `start_new_session` + `killpg`). |
| No failed job changes the displayed result | **Pass** | `test_worker_crash_produces_diagnostic_and_keeps_previous_result` — run-directory contents identical before/after the crash; nothing publishes unless the worker exits 0 and passes checks. |
| External application import evidence | **Blocker recorded** | No named USD application exists on the aarch64 reference machine (`usdview`/Blender/FreeCAD absent). USDA claim restricted to same-library round-trip (`usd_brep.read_brep_from_file`, enforced in every build). See `docs/brep/worker-installation.md`. |
| Existing OpenSCAD behavior passes regression checks | **Pass** | Full `pytest -q` green with the worker active (see `logs/full-suite.txt`); OpenSCAD paths untouched by this change set. |
| Product demonstration + user review | **Pending user** | This folder + live app at the test server; user review recorded on the issue by the project engineer. |

## Startup capability check (new)

`GET /api/health` → `"brep_worker": {"available": true, "reason": null}`.
Broken worker → the reason names the fix, verified by tests for all three
failure shapes: wrong Python version (message includes the `uv venv` command),
wrong usd-brep version (message includes the `uv pip install` command),
missing interpreter path (message points to `docs/brep/README.md`).

## Worker limits (enforced, not documented-only)

RLIMIT_AS / RLIMIT_CPU / RLIMIT_FSIZE are imposed at launch; the worker
reports the limits it actually received in
`diagnostics.resource_limits`, asserted in
`test_resource_limits_are_actually_applied_to_the_worker` (8 GiB / 150 s /
512 MB in the test). A memory-limit kill yields the `worker_killed`
diagnostic including the env var to raise.

## Honest limits

- **pxr loader warnings:** 16 per build, recorded unresolved
  (`logs/worker-stderr-sample.txt`); cosmetic, exit code 0, artifacts verified.
- **Platforms:** only Linux aarch64 (DGX Spark) is tested; nothing else claimed.
- **STEP:** not supported, not promised.
- Cancellation coverage asserted at module level and by the existing
  process-group kill for recipe jobs; a browser-level cancel-click test is not
  in this folder (the app cancel endpoint calls the same code path).

## Re-run it yourself

```bash
export DOODLE_BREP_PYTHON=$PWD/workers/brep/.venv/bin/python
PYTHONPATH=. .venv/bin/python docs/brep/task-16-release/audit.py
```

Gate: SHA256SUMS, install-check report replay, release-test suite re-run,
health-shape assertions, README-claim spot checks. `environment.json` pins
what machine and revisions this evidence belongs to.
