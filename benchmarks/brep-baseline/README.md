# BRep task 01 reference set

Use these drawings to test future integration tasks. This set does not prove
that the current generator can produce all five parts.

| Case | Source | Intended result |
|---|---|---|
| Bookend | Existing user-supplied repository reference | 80 × 50 × 100 mm; four panel openings |
| Wheel | Synthetic engineering diagram | 120 mm diameter; eight spokes; one connected solid |
| Enclosure | Existing synthetic repository reference | 120 × 80 × 40 mm; open top; front window |
| Curved handle | Synthetic engineering diagram | Two straight legs and a curved bend; constant circular section |
| Transition | Synthetic engineering diagram | A solid rectangle-to-circle transition |

Each directory contains a drawing, an OpenSCAD reference, and a test manifest.
The manifest records dimensions, feature positions, relationships, tolerances,
source hashes, and missing information. Keep these values fixed during a trial.
Record any future change as a test-contract revision before the next trial.

The wheel is a proposed test case. It is not the user's failed wheel or an exact
reconstruction of its screenshot. The transition does not specify a unique
intermediate surface. Its reference uses a convex hull. Do not score a valid
loft against that surface as if the drawing required it.

The synthetic images are clean engineering diagrams. They are not evidence of
handwriting robustness. Use the existing bookend doodle and future user drawings
for that purpose. Material, manufacturing limits, and hidden dimensions can
remain unknown. Do not infer them from the expected reference model.

Run these commands from the repository root:

```sh
.venv/bin/python scripts/make_brep_baseline_fixtures.py
.venv/bin/python scripts/check_baseline_geometry.py
```

The first command regenerates the fixture files. The second checks source hashes,
reference dimensions, connectedness, watertightness, and the existing BRep cases.
Feature-position and wall-thickness tolerances are fixed for future checks.
The current script does not claim to measure every declared feature.

User review of these proposed reference cases is pending in issue #18.
