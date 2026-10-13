# Task 04: Saved recipes in the generation job flow

Issue: [#21](https://github.com/nedraki/doodle-to-cad/issues/21).
Branch: `codex/brep-04-recipe-jobs`. PR base: `brep-integration`.
Task 03 merged at `0433057bd8af328f21cc7f53e4e4f57af039532c`.
`main` remains unchanged.

## Product flow

Open the BRep test instance with `?dev=recipes`. Select a saved JSON recipe in
**Developer: saved recipe**, then click **Build saved recipe**. This input is hidden
on the normal page. It does not change the drawing generation default or call a model.
The query option exposes a developer UI; it is not an authentication boundary.

The app validates the recipe and checks the worker executable, Python version, and
installed kernel version before it creates a job. The job uses the existing registry,
status endpoint, cancel endpoint, result viewer, parameter editor, and download links.
Progress identifies solid construction, mesh checks, view rendering, and publication.
The result shows BRep and the completed geometry checks. It has no drawing score.

Reloading the tab resumes the active recipe job. Reloading after completion restores
the result. Completed results can also load from disk after an app restart. Active
jobs remain in memory and do not resume construction after a server restart.

## Cancellation and publication

The app launches a fixed Python module as a new process group. The kernel and local
renderer processes inherit this group. Cancellation kills the group and waits for
termination before completing the cancellation response. Docker renderers carry a
unique job label; cleanup targets only containers with that label. Docker cleanup is
bounded and requires a responsive daemon.

Temporary source, mesh, and logs remain outside the served results directory. The app
publishes the complete result with one directory rename after the build passes. A
cancelled or failed build cannot become the current result. Previous revisions remain.
The kernel retains its 120-second timeout; the full job has a 900-second limit.

This flow applies to the new saved-recipe job route. Existing synchronous recipe build,
conversion, and parameter-edit endpoints retain their behavior.

## Validation

The full suite passes: **92 tests**. It includes real process-group cancellation,
missing/incompatible worker rejection, successful kernel jobs, and disk-backed reload.
The existing Starlette/httpx deprecation warning remains.

The browser check uses `benchmarks/brep-v2/bookend.json`, without a model call:

- The developer input is absent on the normal page.
- The saved recipe builds and displays in the current viewer.
- Reload during the job and after completion restores the same result.
- Changing a hole width updates the source and STL. Source, STL, and USD links work.
- The result has no inherited drawing acceptance score.
- Cancellation observes an actual kernel process during construction. Both runner
  and kernel stop. No result is published for the cancelled job.

`report.json` records these checks. Screenshots show progress and the completed part.
`worker-disabled.json` records a separate live drawing-generation check with
`DOODLE_BREP_PYTHON=/missing/brep-worker`. Recipe submission must fail before job
creation while normal OpenSCAD generation still produces a result. This checks
backend independence, not exact drawing fidelity. The live run completed in
100.08 seconds and produced one watertight OpenSCAD part (run `af5d486531c1`).

## Reproduce

```sh
DOODLE_RESULTS_DIR=results/brep-job-product .venv/bin/python -m uvicorn doodle_to_cad.app:app --host 127.0.0.1 --port 8083
CHROMIUM_EXECUTABLE=/path/to/chrome .venv/bin/python scripts/check_recipe_jobs_product.py
DOODLE_BREP_PYTHON="$PWD/workers/brep/.venv/bin/python" .venv/bin/python -m pytest -q
```

Open `http://127.0.0.1:8083/?dev=recipes` for manual review.
For the worker-disabled check, start a separate instance on port 8084 with a separate
results directory and an invalid `DOODLE_BREP_PYTHON`, then submit a drawing normally.

## Review gate

User review is pending. Do not merge or start task 05 yet. Integration commit: pending.
This task does not fix the earlier knob USD round-trip failure or drawing-fidelity
errors. It does not add model-generated version 2 recipes or automatic backend choice.
