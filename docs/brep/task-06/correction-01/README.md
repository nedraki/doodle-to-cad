# PR 41 — Construction corrections

## Result

The repeated wheel, bookend, knob and cable-holder drawings produce checked BRep candidates. The browser checks pass for all four. Drawing fidelity is still unverified. The fresh knob has square flanges instead of cylindrical flanges; build success is not drawing acceptance.

All inputs use empty notes. The random case remains `104_cable_holder` so the before/after comparison uses the same input. No benchmark reference geometry is supplied to the model.

## General changes

- Give the model clearer rules for primitive origins, connector endpoints and positive joint overlap.
- Return specific placement, size and connection failures from the worker. Report the requested maximum dimension with placement errors, so a correction can address both problems.
- Permit at most two construction corrections. Rebuild and validate each corrected recipe before publication.
- Accept changes only to numeric geometry fields and existing parameter values. Keep feature IDs, kinds, dependencies, axes, rotation angles, parameter ranges and joint requirements unchanged. Reject empty corrections. Do not substitute benchmark recipes.
- Keep every attempted recipe, failure, correction request and model response. Cancel the job before publication if requested.
- Complete worker cleanup before reporting a completed job.

The correction step handles measured construction errors. It does not evaluate projections or drawing features. Issue #24 still needs those checks and their repair guidance.

## USD volume check fix

The installed `usd-brep==1.0.0` API defaults to `volume(relative_accuracy=1e-3)`. The application compared original and reloaded volumes at a tighter `1e-5` tolerance. This can reject an unchanged exported shape because the two numerical integrations differ.

Both sides now request `relative_accuracy=1e-8`. The acceptance tolerance stays at `1e-5`. No geometry repair or export-check bypass is used.

The unchanged first wheel recipe (`b326f3e9090a`) demonstrates the fault:

| Volume calculation | Before export, mm³ | After reload, mm³ | Result |
|---|---:|---:|---|
| Default accuracy | 51268.3772153 | 51289.0833714 | Rejected |
| Requested accuracy 1e-8 | 51285.5673954 | 51285.5671355 | Pass |

See `wheel/export-diagnostic/`. The original failed export and precise reproduction are retained separately. `benchmarks/brep-v2/volume-precision-wheel.json` is the regression fixture, copied from that live model output. It is never supplied as generation input.

## Fresh drawing generations

| Case | Run | Result | Remaining visual limit |
|---|---|---|---|
| Wheel | `e743731b0409` | Pass after one joint correction; 120 × 120 × 8 mm | Wheel lies in XY rather than the declared front XZ plane. |
| Bookend | `8929ff6228eb` | Pass; 100 × 40 × 120 mm | Bottom flange and closed upper opening are present; measured fidelity is not checked. |
| Knob | `baefc1f3ec29` | Pass; 100 × 100 × 120 mm | Incorrect square flanges and neck. |
| Cable holder | `83d09530fa45` | Pass; 10 × 58 × 120 mm | Curved profile is absent; circular feature is misplaced. The generated width parameter is unused. |

Each candidate loads in the viewer. An editable parameter changes measured geometry. Recipe, STL and USDA downloads match that edit. Reload restores the original candidate. `product-report.json` records the checks. Per-case folders contain screenshots, source and native 3D files.

The fresh wheel correction and the first successful cylindrical-knob replay were also checked against the final stricter guards; see `guard-revalidation.json`. The guards accept those observed changes.

## Saved-failure replays

The exact recipes from the prior failed wheel (`b84fcad7db3f`) and knob (`4c52461e6c88`) are tested separately. These are correction trials, not new drawing generations. They preserve the original feature types and joint requirements.

`replayed-failures/` retains all attempts, including a whole-recipe correction that made no change and a rejected small-patch response. The final implementation uses full recipe responses with numeric-only guards. It does not permit the model to change topology or remove constraints.

The first cylindrical-knob replay (`3195e79e3778`) passed after one correction. Later model trials include failures; do not infer reliable repair from one successful result. The final knob replay (`5626b4378905`) passes with its cylindrical features preserved. The final wheel replay (`d3fe50ee257c`) fails: the model returns a correction with no change. The app rejects it and publishes no part. This remains a repair reliability limit, even though the fresh wheel builds successfully.

## Validation

- Full suite: **120 passed** (`tests.txt`).
- Final requested-size and correction checks: **23 passed** (`final-focused-tests.txt`).
- Real-kernel checks cover correction success, cancellation during correction, attempt exhaustion, preservation of required joints, and the numerical export regression.
- All four fresh candidates pass viewer, edit, reload and native-download checks.
- OpenSCAD remains the default. `main` is unchanged. This work belongs to PR #41, based on `brep-integration`.

Keep PR #41 in draft for user review. Do not call these parts drawing-approved. No automatic backend selection or drawing-score supervisor is added.
