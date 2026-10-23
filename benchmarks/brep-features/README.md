# Richer BRep generation: selected drawings

Issue [#42](https://github.com/nedraki/doodle-to-cad/issues/42). Contract: **issue42-v1**.
Status: **proposed; user review pending**. This is a development set, not a holdout.

This task selects drawings and defines acceptance checks. It does not generate
parts or prove that the current model can use these operations. It changes no
product code. The drawings are synthetic engineering diagrams. They do not test
handwriting robustness. The existing bookend doodle remains a regression.

## Selected cases

| Drawing | Visible evidence and required result | Useful edit | Keep fixed | Capability / next task |
|---|---|---|---|---|
| [Constant-radius handle](../brep-baseline/curved_handle/drawing.png) | Circular section Ø8; two straight legs 30; semicircle centreline R20. One continuous solid. | Bend R20 → R24 | Section Ø8, straight lengths, XY plane | Existing arc pipe, cylinders and union; #43 |
| [Rounded housing blank](rounded_housing/drawing.png) | Solid 80 × 50 × 30 blank; four vertical corners R6; sharp top and bottom rim | R6 → R8 | Outer dimensions, centre, height and sharp rim | Existing box and vertical-edge fillet; #43 |
| [Bevelled block](bevelled_block/drawing.png) | Solid 60 × 40 × 20 block; all edges have a 2 mm, 45° bevel | Bevel 2 → 3 | Outer dimensions and centre | Existing global chamfer; verify API distance meaning in #43 |
| [Rectangular-section handle](rectangular_sweep/drawing.png) | S path with two opposite R20 quarter turns; straight ends 10; constant 6 × 4 section | Section width 6 → 8 | Centreline, end centres, thickness and section orientation | Missing bounded general sweep; #27 |
| [Solid transition](../brep-baseline/transition/drawing.png) | Bottom rectangle 60 × 40; top circle Ø30; common axis; height 60; capped solid | Top Ø30 → Ø36 | Bottom profile, height and common axis | Missing positioned profiles and loft; #28 |
| [Ambiguous outline](../feature-evidence/ambiguous-outline.png) | One rectangle. Depth, cavity and edge treatment are unresolved. | None until intent is known | Drawing and uncertainty record | Report uncertainty now; question flow #25 |

The rounded housing is a solid blank. It does not test walls or a cavity. Use
#29 for hollow bodies. The bevel case prevents rounding from being accepted as
a substitute for a visible flat bevel. The two handle cases have different
sections and paths. A circular arc pipe cannot satisfy the rectangular section.
An equivalent shape may pass the drawing check, but the general-sweep capability
check must also show a sweep recipe. Do not claim that OpenSCAD cannot make these
shapes.

The handle bend-radius edit intentionally changes end spacing and the envelope.
Do not claim to preserve those values. The loft drawing does not specify a unique
intermediate surface. Do not score a valid surface against the convex-hull
reference as if it were an exact target.

## Fixed measurement contract

[selection.json](selection.json) records source hashes, evidence pixel boxes,
normal form controls, expected values, edits, tolerances and unresolved details.
The evidence boxes use source image pixels. They are reviewer annotations, not
input to the production model. Preserve the existing drawings byte for byte.

- For the existing handle and transition, retain the task 01 limits: 2% per
  overall dimension and 1 mm for feature size or position.
- For the new drawings, allow 0.5 mm on overall dimensions. Allow 0.25 mm on
  section sizes, corner radius and bevel setback. Allow 0.5 mm on the S path.
- For bevel angles, allow 2°. For joins, allow 5° tangent mismatch. Also inspect
  continuity across the full section; a small material bridge is not sufficient.
- Compare protected dimensions before and after an edit within 0.05 mm. Check
  the edited value against its requested value using the feature-size tolerance.
- Require one watertight solid for each positive case. Place its minimum Z at
  zero within 0.001 mm. The ambiguity case has no expected solid.
- Check orientation in the declared axes. Translation can register the part;
  rotation or scaling must not conceal a wrong interpretation.

These are proposed acceptance limits, not measurements already implemented in
the app. Issue #24 implements the focused drawing checks. Use native geometry
for radii, face type and tangents where available. State mesh sampling error if
mesh sections are used. If measurement uncertainty exceeds the tolerance, return
**unverified**. Do not return pass. Human review must cover missing features,
section orientation, sharp versus rounded treatment, loft twist and unsupported
assumptions. Record the reviewer and result.

The first demonstration must include a wrong-feature candidate and a correct
candidate for each new check. Examples are a sharp box instead of the rounded
blank, a circular tube instead of the rectangular section, and a rounded edge
instead of a bevel. Do not adjust thresholds after inspecting generation results.
Revise this contract explicitly before a later trial if a check needs correction.

## Regressions and random selection

Keep the wheel, bookend, stepped knob and saved random cable holder. The next
additional random case is **102_lcd_knob**. `selection.json` records the eligible
development cases, selection method and drawing hash. Selection happened before
any new model trial. Do not redraw after observing a failure. Select and record
one additional random case before each later implementation trial.

## Model input and trial record

For the positive cases, send the drawing and the normal controls recorded in
`selection.json`. Notes and object hints are empty. Dimension labels on the
image are legitimate drawing evidence. The ordinary production capability
prompt is permitted. Do not send this contract, evidence boxes, reference CAD,
expected measurements or reference renders to the model.

Keep reference recipes only in deterministic geometry checks. Save the exact
submitted image and request payload so this separation can be audited.

For each future run, save model identity, prompt version, non-secret settings,
input hashes, recipe, each attempt, correction diagnostics, native geometry,
rendered views, parameter changes and download checks. Record unsupported cases
and failed attempts. Show drawing → generated part → edited part together.
Report geometric validity and drawing fidelity separately. A build alone does
not pass. For an ambiguous drawing, disclose assumptions and do not mark hidden
features as drawing-confirmed.

## Existing OpenSCAD evidence

The task 01 [reference checks](../../docs/brep/baseline-01/reference-checks.json)
record a connected, watertight handle of 48 × 54 × 8 mm and a transition of
60 × 40 × 60 mm. These are hand-authored OpenSCAD references, not model-generated
results. The transition uses a convex hull, not a tested loft implementation.

The task 01 [product report](../../docs/brep/baseline-01/README.md) records a live
OpenSCAD bookend and a working width edit. Its drawing check failed: three
openings were found, but four were required. That run used descriptive notes;
it is not an empty-note comparison for these new drawings.

No same-input live OpenSCAD results exist in this record for the new housing,
bevel or rectangular-section handle. Record those comparisons during #43 and
#27 where supported. Do not infer a performance advantage from reference CAD.
The BRep advantage to demonstrate is drawing-supported geometry plus useful,
checked edits. Compare outcomes and edit controls, not backend labels.

## Reproduce and review

From the repository root, with the application Python environment:

```sh
python scripts/make_brep_feature_drawings.py
python scripts/check_brep_feature_corpus.py
```

The drawing script requires Pillow and DejaVu Sans at the path in the script.
It makes the three new diagrams only. It does not change the existing baseline
or reselect the random case. The audit verifies hashes, regions and references;
it does not validate generated solids. See the saved [task report](../../docs/brep/task-42/README.md).

Review the proposed shapes, edit constraints and tolerances before implementation.
PR #41 remains draft. This task does not authorize its merge. Keep all future
implementation on `brep-integration`, with a separate task branch and test server.
Keep `main` unchanged.
