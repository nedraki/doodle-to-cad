# BRep worker — installation, limits, and supported files (issue #33)

Verified on the reference machine: NVIDIA DGX Spark, Ubuntu 24.04.4 (aarch64),
2026-10-18. See `docs/brep/task-16-release/environment.json` for exact versions.
Steps 1–3 ran from a clean throwaway venv via `scripts/check_worker_install.py`
(report: `docs/brep/task-16-release/install-check.json`, 8/8 pass).

## Install (pinned, tested)

```bash
uv venv --python 3.12 workers/brep/.venv
uv pip install --python workers/brep/.venv/bin/python -r workers/brep/requirements.txt
```

`requirements.txt` pins `usd-brep==1.0.0`, `numpy==2.5.4`, `trimesh==5.1.1`,
`networkx==3.6.1`. The worker needs Python 3.12 exactly; the web app uses its
own environment and never imports the worker libraries in-process.

The app auto-detects `workers/brep/.venv`. A custom location is selected with
`DOODLE_BREP_PYTHON=<path to worker python>`. No USD runtime installation is
required or attempted: the `usd-brep` wheel is self-contained and never links
a system USD.

## Startup capability check

`GET /api/health` includes:

```json
"brep_worker": {"available": true, "reason": null}
```

When unavailable, `reason` names the exact fix (missing worker path, wrong
Python version, or wrong usd-brep version, with the install command). A build
attempt with a broken worker fails the same way before any geometry work.

## Worker limits and failures (contained by design)

- Each build runs in its own process, killed at 120 s wall time.
- rlimits applied at launch (reported back in `diagnostics.resource_limits`):
  memory `DOODLE_BREP_MEMORY_LIMIT_MB` (default 16384 MB), CPU
  `DOODLE_BREP_CPU_LIMIT_S` (default 150 s), file size 512 MB. A worker killed
  by the memory limit yields the `worker_killed` diagnostic with the raise
  command, not a generic failure.
- Cancelling a job sets a per-run event; `build_brep` polls it and kills the
  worker process (asserted by `tests/test_worker_release.py` — the pid is
  gone and no staging directories leak). Recipe jobs additionally kill the
  whole process group (`start_new_session` + `killpg`).
- A crashed worker never changes the displayed result: nothing is published
  unless the worker exits 0 and passes mesh/USD checks. `build_failed` keeps
  any `construction-error.json` message; the last good result stays served.

## Supported exports and platforms

| File | Guarantee |
|---|---|
| `model.stl` | Always available. Watertight single component is enforced before publish. |
| `model.usda` (ASCII USD) | Schema includes the custom BRep data. Verified by round-trip **with the same library** (`usd_brep.read_brep_from_file`) — volume and watertightness re-checked after import. |
| STEP | **Not promised.** No verified STEP exporter exists in this codebase; do not advertise it. |

Platform support actually tested: Linux aarch64 (this machine). Other
platforms are untested, not claimed broken.

**Open blocker (external application):** the release asks for import proof in
one *named external* USD application. The reference machine has none
(`usdview`, Blender, FreeCAD absent on this aarch64 server), and the
`pxr.Ar`-style Python bindings are not part of the wheel. Until the test runs
on a desktop with a named app, the USDA claim stays limited to
"reader-verified within usd-brep; external application verification pending".
Recorded in `docs/brep/task-16-release/README.md`.

## Known limitation: pxr loader warnings (recorded, unresolved)

Every worker build prints 16 warnings like this on stderr:

```
Warning: in _LoadLibModules at line 329 of /builds/omniverse/usd-ci/USD/pxr/base/tf/scriptModuleLoader.cpp
-- Error loading lib ar's module 'pxr.Ar': ModuleNotFoundError: No module named 'pxr'
```

Cause: the self-contained wheel ships the USD C++ libraries but not their
optional Python modules; TF's script-module loader reports each one at load.
Builds, exports, and checks are unaffected (exit code 0; artifacts verified).
The product code never imports `pxr`. Resolution kept open on purpose —
silencing it would require modifying the pinned wheel's payload. Full sample:
`logs/worker-stderr-sample.txt`.

## Re-run the checks

```bash
PYTHONPATH=. .venv/bin/python scripts/check_worker_install.py   # clean install, 8 steps
PYTHONPATH=. .venv/bin/python docs/brep/task-16-release/audit.py
DOODLE_BREP_PYTHON=$PWD/workers/brep/.venv/bin/python .venv/bin/pytest tests/test_worker_release.py -q
```
