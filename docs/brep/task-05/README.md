# Task 05: Drawing feature evidence

Issue: [#22](https://github.com/nedraki/doodle-to-cad/issues/22).
Branch: `codex/brep-05-drawing-evidence`. PR base: `brep-integration`.
Task 04 merged at `0cacd61`. `main` is unchanged.

## What changed

Open the test app with `?dev=evidence`. Upload or draw an image, then click
**Interpret drawing**. This developer-only flow ignores descriptive notes. It does
not generate a recipe, select a kernel, or construct a part. The normal generation
prompt and path remain unchanged.

OpenCV supplies the source-region catalog. Each region retains its source view,
measured box, contour ID, and coordinate mapping. The model describes features and
relationships and refers to those IDs. Invalid feature or region references are
rejected. One bounded schema-correction retry is allowed. Raw model output is saved.

Only this opt-in pass excludes groups below 5% of the largest group box area from
view-direction assignment. It retains every region and records excluded IDs. This
prevents annotation groups from displacing the wheel projections in the tested sheet.
A small real detail view may also be left unassigned; it is not deleted.

The result separates observed features, inferred relationships, assumptions,
unresolved values, and conflicts. Unsupported wall or cavity claims from an outer
outline are changed to unresolved. Claims without source references are unresolved.
Projected connections are classified as inferred: visible continuity does not prove
a connected 3D solid. The model's original status and the reason for each policy
change remain visible.

A separate measured table compares spans on axes shared by assigned views. It never
compares front width with side depth as if they were the same dimension. A difference
over 10% is flagged for review. Equal drawing scale and correct view assignment are
explicit assumptions. Pixel agreement is not a verified physical dimension.

The review panel shows the measured overlay, source references, feature claims,
relationships, conflicts, and unresolved values. It offers an evidence JSON download.
The UI is opt-in, not an authentication boundary. It does not display a CAD acceptance
score or claim that the interpretation is correct.

## Live drawings tested

Every run uses the drawing only, with front as the primary view and third-angle
projection. No descriptive notes, object names, reference CAD, or ground-truth
measurements are sent to the model.

| Case | Source | Review focus |
|---|---|---|
| Wheel | `benchmarks/brep-baseline/wheel/drawing.png` | Hub, rim, repeated spokes, projected connections |
| Bookend | `benchmarks/cases/001_l_bookend_multiview/source/drawing.png` | Four openings, measured positions, common projection axes |
| Knob | `benchmarks/cases/006_stepped_knob/source/drawing.png` | Separate upper/lower flanges and central region; hidden 3D ambiguity |
| Random: vent grille | `benchmarks/cases/012_vent_grille_grid/source/drawing.png` | Repeated openings and unresolved thickness |
| Ambiguous outline | `benchmarks/feature-evidence/ambiguous-outline.png` | No invented wall thickness or shell |

The random case was selected once with `secrets.choice` from available benchmark
folders, excluding the explicitly requested bookend and knob. `selection.json`
records the candidate list and selection. The test script reuses that selection.
The wheel is the existing synthetic baseline drawing, not the user's earlier doodle.

The final wheel run identifies eight radial spokes and both hub/spoke and rim/spoke
connections as inferred. The corrected front/right height spans are 433/433 pixels.
Bookend height spans are 437/456 pixels; knob height spans are 294/287 pixels. The
grille run identifies nine openings in a 3×3 pattern. The plain outline leaves
hollow-versus-solid construction unresolved. No benchmark CAD was generated in
these checks.

Each case directory contains the input, measured overlay, raw model output, JSON
response, interpretation fixture, and browser screenshots. `summary.json` records
case IDs and unresolved/conflicting claims. The ambiguous outline is also submitted
through the real developer button, not only through the API.

## Reproduce

```sh
DOODLE_RESULTS_DIR=results/brep-evidence-product .venv/bin/python -m uvicorn doodle_to_cad.app:app --host 127.0.0.1 --port 8085
CHROMIUM_EXECUTABLE=/path/to/chrome .venv/bin/python scripts/check_feature_evidence.py
DOODLE_BREP_PYTHON="$PWD/workers/brep/.venv/bin/python" .venv/bin/python -m pytest -q
```

The full suite passes **101 tests**, including existing OpenSCAD regressions.
The existing Starlette/httpx deprecation warning remains.

The live check uses the configured local model. It can take several minutes.
The test set covers invalid references, unsupported hidden geometry, projected
connections, measured shared axes, and preservation of conflicts and raw claims.

## Limits and review gate

Reference integrity does not establish semantic truth. A model can cite a real region
and still describe it incorrectly. The current pass does not measure each inferred
subfeature separately when OpenCV only isolates the whole outline. It does not verify
3D connections, opening depth, wall thickness, or exact physical dimensions.

The reviewed bookend output describes opening containment but labels that relationship
`connected`. That category is not a valid material-connection instruction. The knob
output separates its flanges but does not quantify their unequal sizes. These limits
remain visible in the saved claims; this output must not be compiled directly.

The earlier knob USD failure and generation acceptance errors remain unresolved.
This task records uncertainty before generation; it does not fix the old generation
path. User review is pending. Do not merge or start task 06 yet.
Integration commit: pending.
