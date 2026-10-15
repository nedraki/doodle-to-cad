# Task 07: drawing checks

The direct BRep path now saves `drawing-checks.json`. The result shows separate
build, geometry and drawing status. OpenSCAD remains the default.

Projection similarity and opening-position checks reuse the existing evaluator.
An opening must appear in its required view. A hole in another wall cannot satisfy
that requirement. Limits remain 0.45 for projection similarity and 0.5 for opening
position fidelity. They were fixed before the live richer-generation trials.

Projection checks do not prove exact radii, bevel angles or hidden section shape.
A candidate remains unverified when these checks or view assignments need review.
Drawing failures do not trigger the numeric construction corrector. There is no
second repair loop. After a parameter edit, the UI explicitly states that drawing
checks have not been rerun.

## Validation

The full suite passes 127 tests. It includes the previous correction cancellation,
exhaustion and evidence-preservation checks. `tests.txt` records the output.

`feature-report.json` measures sections of exported geometry independently of
recipe operation names. Correct rounded, bevelled and curved reference shapes pass;
sharp or straight substitutes fail. A rectangular section passes while a circular
substitute fails. These are deterministic geometry tests, not generated examples.
The fixed issue 42 feature tolerances are used. Sampling spacing is 0.1 mm.

The initial handle construction with a small overlap failed in the kernel. It is
recorded in `initial-feature-report.json` and `pipe-union-probes.txt`. A reference
with full coincident cap faces fuses into one solid and passes the section check.
This does not prove that every model-generated overlapping construction will work.
No kernel validation or declared joint constraint is bypassed.

`saved-drawing-report.json` applies the new checks to all four prior live candidates.
The wheel and cable holder fail drawing checks. The bookend and square knob remain
unverified; passing coarse projections cannot establish their detailed shape.
Screenshots show the new status in the real viewer with those saved meshes.

## Reproduce

```sh
python -m scripts.check_brep_drawing_features
python -m scripts.check_saved_brep_drawings
python -m pytest -q
```

Set `DOODLE_BREP_PYTHON` to the isolated worker. Model calls are not required for
these checks. The richer live generation and parameter-edit evidence follows in
issue #43. No benchmark lookup or expected dimensions enter the production model
prompt. Reference recipes remain deterministic test inputs only.
