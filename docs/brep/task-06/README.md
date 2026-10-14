# Task 06 — Direct BRep generation

## Scope

Select **Direct BRep (experimental)** in the drawing form. The app reads one drawing sheet, interprets its features, asks the model for a version 2 recipe, and builds the recipe in the isolated worker. It does not generate or translate OpenSCAD part code.

OpenSCAD remains the default. The existing conversion button remains a separate path. The BRep path does not switch backends when it fails.

The geometry worker checks the solid, connected components, declared joints, mesh, and USD round trip. The result remains an **unverified candidate**. These checks do not prove that the part matches the drawing. Task 07 adds drawing checks and bounded geometry repair.

## Development branch

- Previous task: PR #40 merged into `brep-integration` at `6eb322336d531d7ce1307d3ced3966c7f1756b76` after user approval.
- Task branch: `codex/brep-06-direct-generation`.
- PR base: `brep-integration`.
- `main` remains at the pre-BRep version.

## Operation subset

Boxes, cylinders, union, difference, fillet, chamfer, circular arc pipe, and rotation about a world axis through a specified pivot. Rotation is added in this task because the wheel drawing has diagonal spokes. The worker copies the source body before rotation. Rotation angles must be greater than zero and at most 360 degrees.

The `/api/backends` response lists the supported operations. The model must report unsupported construction. The app also rejects invalid recipes before starting the kernel.

The direct path currently accepts one image sheet. Put multiple projections on that sheet. Separate view uploads and trace-as-drawn mode return explicit errors. The maximum dimension must be 1–256 mm. The worker always requires one connected, watertight part.

## Evidence

`selection.json` records the random selection before generation. The agreed drawings are wheel, bookend and knob. The random case is `104_cable_holder`. Inputs have empty descriptive notes. The model receives no reference recipe, reference CAD or benchmark ground truth.

Each run saves input, measured regions, interpretation, recipe prompt, model output, schema failures, model identity, prompt version and generation controls. A successful run also saves recipe JSON, STL, USDA, four rendered views and build diagnostics. Failed runs save diagnostics without `result.json`; they do not replace a completed result.

The worker uses a fixed `preview.scad` file containing only `import("model.stl");` to render the finished mesh. This is a preview dependency, not generated part code or an OpenSCAD-to-BRep conversion.

`initial-wheel-attempt` records a cancelled preliminary run before rotation support was added. Do not count it as a successful build. The real form cancellation check is in `form-report.json` and `direct-form-progress.png`.

`summary.json` records the live generation outcomes. `product-report.json` records viewer, parameter edit, reload and download checks. Each part directory contains input, screenshots and saved 3D artifacts where generation succeeded. Keep failed and repeated runs for review.

## Reproduction

Start a separate server with `DOODLE_RESULTS_DIR=results/brep-direct-product` on port 8086. Run:

```sh
.venv/bin/python scripts/check_direct_brep.py
.venv/bin/python scripts/check_direct_brep_product.py
DOODLE_BREP_PYTHON=$PWD/workers/brep/.venv/bin/python .venv/bin/pytest -q
```

Use `BREP_CASES=wheel` to repeat one case. Use `DOODLE_TEST_URL` to select another test server. The random choice is reused from `selection.json`.

## Review gate

User review is pending. Do not merge this task or start task 07 until the result and limits have been reviewed.

## Preliminary trials

- `bc04753b0b52`: cancelled when the missing rotation operation was identified. Saved under `initial-wheel-attempt`.
- `f0e9a0a9018a`: wheel failed schema validation. The model omitted the top-level output field in both recipe attempts. Saved under `wheel/preliminary-artifacts` and `initial-summary.json`.
- `5c69c01c0ff4`: bookend trial cancelled when the prompt was replaced. Saved under `initial-bookend-attempt`.

Prompt version `drawing-brep-3` uses one complete version 2 example. It replaces the mixed version 1 example and version 2 instructions used by the preliminary trials. All final benchmark trials use this version.

## Final outcomes

All four runs used empty notes and a maximum dimension of 120 mm. Model: `local-inference-lab/Qwen3.8-Flash-Next-NVFP4`. Prompt: `drawing-brep-3`.

| Drawing | Run | Build result | Review result |
|---|---|---|---|
| Wheel | `b84fcad7db3f` | Rejected | One connected mesh, but minimum Z is -66 mm and extents are 132 × 8 × 132 mm. The model centred the wheel on Z=0 and extended spokes beyond the rim. |
| Bookend | `1e429a45b4d5` | Solid, mesh and USD checks pass | Incorrect interpretation. The flange is on the side instead of the bottom. The upper opening breaks through the top edge. Extents: 100 × 30 × 120 mm. |
| Knob | `4c52461e6c88` | Rejected | The model declared a 100 mm³ overlap at each neck/flange joint. The cylinders only meet at their end faces; measured overlap is zero. This is a joint-contract failure, not proof that the fused solid is disconnected. |
| Random: cable holder | `5334ea603c04` | Solid, mesh and USD checks pass | Incorrect interpretation. The curved end profile is absent. The circular feature from the end view becomes a blind pocket in the broad face. Extents: 10 × 60 × 120 mm. |

The wheel diagnosis was reproduced from the unchanged saved recipe after adding precise measurements to the worker error message. See `wheel/geometry-failure.log`. The original job error is also retained.

The knob also gives both flanges one diameter parameter and loses the unequal sizes in the drawing. The cable-holder recipe exposes `width` and `slot_pitch` parameters that its operations do not use. Record these as generation limits; do not present them as useful edits.

For both published candidates, the browser check confirms:

- The viewer loads the actual STL.
- A used parameter changes the measured geometry: bookend width 100 → 102 mm; cable-holder depth 60 → 61.2 mm.
- Recipe, STL and USDA downloads match the edited candidate.
- Reload restores the saved original candidate. It does not promote an edit to the original.
- No generated OpenSCAD part source exists. The only SCAD files are fixed mesh preview imports.

Screenshots: `bookend/part.png`, `bookend/result.png`, `bookend/edited-result.png`, and corresponding files under `random/`. Failure screens are saved under `wheel/` and `knob/`.

The `artifacts/<run-id>/` folders contain the native generated files and subsequent edit revisions. Failed runs contain recipes and error evidence, but no accepted 3D output. Tests use controlled recipes separately from live model trials.

## Validation decision

The software checks pass: **113 tests**, plus the real browser form, cancellation, viewer, edit, reload and download checks. A real-kernel test also builds an eight-spoke wheel with all eight rim joints and a USD round trip.

**The live benchmark gate does not pass.** Two of four drawings produce publishable solids. Neither published candidate is a correct reproduction of the drawing. The required live wheel result is missing.

Keep the PR in draft and issue #23 open. Do not claim task 06 is complete. Task 07 is the planned drawing-check and geometry-repair work, but its start still requires review of this gate. No task 07 work was started.
