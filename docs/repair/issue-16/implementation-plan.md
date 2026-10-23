# Issue #16 — Targeted post-generation repair: "this part is close — change only what I describe"

Branch `hermes/issue-16-targeted-repair`, base `brep-integration@01de9dd`. Target `brep-integration` only; main is untouched.

## User example

A generated eight-spoke wheel is recognizable but the spokes stop short of the rim. From the displayed result the user presses **Fix this part**, writes "Connect every spoke to the rim. Keep the outer diameter, hub, spoke count, and thickness unchanged. Make the wheel one connected printable part.", and gets a separate candidate — built from the version currently on screen, including successfully applied parameter edits — with the changes, the preservation constraints and the validation results shown. Keep makes it current, Discard returns to the pre-repair version, Refine runs again from the displayed candidate. Downloads and parameter controls always match the displayed revision; a failed or stale repair cannot replace the last valid result.

## Implemented design

1. `doodle_to_cad/repair.py` — one endpoint seam `repair_preview(pipeline, settings, out, payload)`:
   - Input: `parent_id`, `selection_version`, `instruction` (non-empty, ≤2000 chars), optional `displayed {source, stl}` URLs. The displayed source must resolve to a real `.scad` inside the run directory, so the repair provably starts from what the browser shows (an `edited-*.scad` from applied parameter edits, or the revision's own source) and a foreign path or the bare original cannot be smuggled in. `started_from` records which.
   - Two model calls: an interpretation call that separates the requested change from the properties to preserve (advisory — a failure is recorded, the repair still runs deterministic checks), then the repair call. The model receives the correction text, the current displayed source, the original specification, the editable-parameter values, the measured mesh diagnostics of the displayed STL and the original drawing image. The prompt forbids redesigning and requires real overlap (≥1 mm) before unioning.
   - The candidate is compiled through the shared build contract into its own `repair-*/` directory. Model or compile failure raises an explained `HTTPException` (422 `model_failure` / `build_failed`), keeps the failed source on disk and never touches the selection.
   - Deterministic checks with documented tolerances (`PRESERVATION_TOLERANCES`, extents ±2 % relative or 0.5 mm absolute — the same convention as `benchmarks/brep-baseline/wheel/manifest.json`): compiles, watertight, connected components (counted separately from watertightness), extents preserved, editable-parameter changes reported, volume measured. The requested correction itself stays `unverified` and is reviewed visually plus via the model interpretation. Compilation alone never marks success.
   - The candidate is stored as a revision with its parent, kind `repair`, instruction and diagnostics, and published only after the selection counter is rechecked, so a stale repair cannot overwrite a newer keep. The candidate's evaluation is explicitly `unverified` — the original acceptance score is never carried over.
2. `doodle_to_cad/revisions.py` — revision records gained `kind`; `result_for` exposes it. No record-shape changes (the store was designed for this in task 13).
3. `doodle_to_cad/app.py` — `POST /api/results/{id}/revisions/repair`; `GET /params?revision_id=` works for OpenSCAD revisions with their own source (kept repairs, edits); `POST /parametrize?revision_id=` edits from a saved revision's source instead of the original `model.scad`, and successful edits are appended to `parametrize-history.jsonl`.
4. Web UI — **Fix this part** button + correction dialog (states which version the candidate starts from), repair summary panel (instruction, model interpretation, started-from, per-check status with before→after values and documented "measured vs visual" note), candidate banners, **Keep repair / Discard repair / Refine instruction** reusing the task-13 keep/discard machinery, stale-request epoch guards.

## Required checks (per issue acceptance criteria)

- Repair from the displayed version incl. applied parameter edits; never silently the original generation.
- Wheel: one connected watertight part after repair with outer diameter, hub, spoke count and spoke width preserved within the documented tolerances — measured with trimesh, not compilation.
- Change/preserve/validation summary distinguishes passed / failed / unverified.
- Keep, Discard and Refine are consistent; the pre-repair version stays recoverable.
- Downloads and parameter controls follow the displayed revision.
- Failed and stale repair requests cannot overwrite the last valid result.
- Tests cover repair after parameter edits, wheel connectivity and preserved dimensions, failure recovery and keep/discard behavior.

Implementation and validation: see README.md, initial-tests.txt, tests.txt, product-final/ and regressions/.
