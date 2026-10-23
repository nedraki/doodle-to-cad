# Current-model baseline (#81 / #102)

All 24 cells from the revised plan are retained. Two earlier interrupted submissions are retained separately: 26 total submissions, 24 in the verified-environment matrix. The interruption is infrastructure evidence, not a model-quality verdict.

No model prompts or production geometry algorithms changed. Orientation scores are diagnostic only. These small repeated trials establish a descriptive baseline, not overall recognition improvement. User acceptance is pending.

| Backend | Submitted | Completed jobs | Valid solids | Supplied dimension passes | Measurable meshes |
|---|---:|---:|---:|---:|---:|
| openscad | 12 | 12 | 11 | 9 | 12 |
| usd-brep | 12 | 10 | 10 | 8 | 10 |

Pass counts use all submitted cells as denominator. Failed builds are retained. See each row for measured-only comparisons; a valid solid is not drawing acceptance.

| Case / backend / trial | Job | Solid | Supplied maximum | Measured extents | Genus (reference check) |
|---|---|---|---:|---|---|
| [003_front_grille_multiview / openscad / 1](runs/003_front_grille_multiview/openscad/trial-01/row.json) | done | pass | 126 mm: fail | [123.077, 75.693, 7.52] | 0 (fail) |
| [003_front_grille_multiview / openscad / 2](runs/003_front_grille_multiview/openscad/trial-02/row.json) | done | pass | 126 mm: pass | [126.0, 7.52, 78.72] | 5 (fail) |
| [003_front_grille_multiview / usd-brep / 1](runs/003_front_grille_multiview/usd-brep/trial-01/row.json) | done | pass | 126 mm: pass | [126.0, 10.0, 80.0] | 7 (fail) |
| [003_front_grille_multiview / usd-brep / 2](runs/003_front_grille_multiview/usd-brep/trial-02/row.json) | error | fail | 126 mm: fail | — | — (not measured) |
| [004_flat_mounting_plate / openscad / 1](runs/004_flat_mounting_plate/openscad/trial-01/row.json) | done | pass | 100 mm: pass | [100.0, 9.65, 61.98] | 3 (pass) |
| [004_flat_mounting_plate / openscad / 2](runs/004_flat_mounting_plate/openscad/trial-02/row.json) | done | pass | 100 mm: pass | [100.0, 9.65, 61.98] | 3 (pass) |
| [004_flat_mounting_plate / usd-brep / 1](runs/004_flat_mounting_plate/usd-brep/trial-01/row.json) | done | pass | 100 mm: pass | [100.0, 60.0, 5.0] | 3 (pass) |
| [004_flat_mounting_plate / usd-brep / 2](runs/004_flat_mounting_plate/usd-brep/trial-02/row.json) | done | pass | 100 mm: pass | [100.0, 60.0, 3.0] | 0 (fail) |
| [007_angle_bracket_holes / openscad / 1](runs/007_angle_bracket_holes/openscad/trial-01/row.json) | done | pass | 80 mm: pass | [80.0, 43.13, 51.01] | 0 (fail) |
| [007_angle_bracket_holes / openscad / 2](runs/007_angle_bracket_holes/openscad/trial-02/row.json) | done | pass | 80 mm: pass | [80.0, 43.13, 51.01] | 3 (pass) |
| [007_angle_bracket_holes / usd-brep / 1](runs/007_angle_bracket_holes/usd-brep/trial-01/row.json) | error | fail | 80 mm: fail | — | — (not measured) |
| [007_angle_bracket_holes / usd-brep / 2](runs/007_angle_bracket_holes/usd-brep/trial-02/row.json) | done | pass | 80 mm: fail | [40.0, 20.0, 40.0] | 3 (pass) |
| [008_open_enclosure_window / openscad / 1](runs/008_open_enclosure_window/openscad/trial-01/row.json) | done | pass | 120 mm: pass | [120.0, 81.68, 43.96] | 1 (pass) |
| [008_open_enclosure_window / openscad / 2](runs/008_open_enclosure_window/openscad/trial-02/row.json) | done | pass | 120 mm: pass | [120.0, 81.68, 43.96] | 1 (pass) |
| [008_open_enclosure_window / usd-brep / 1](runs/008_open_enclosure_window/usd-brep/trial-01/row.json) | done | pass | 120 mm: pass | [120.0, 80.0, 40.0] | 1 (pass) |
| [008_open_enclosure_window / usd-brep / 2](runs/008_open_enclosure_window/usd-brep/trial-02/row.json) | done | pass | 120 mm: pass | [120.0, 80.0, 60.0] | 1 (pass) |
| [constant_radius_handle / openscad / 1](runs/constant_radius_handle/openscad/trial-01/row.json) | done | pass | 54 mm: fail | [48.37, 8.16, 55.438] | 0 (pass) |
| [constant_radius_handle / openscad / 2](runs/constant_radius_handle/openscad/trial-02/row.json) | done | fail | 54 mm: fail | [48.923, 8.972, 33.832] | None (fail) |
| [constant_radius_handle / usd-brep / 1](runs/constant_radius_handle/usd-brep/trial-01/row.json) | done | pass | 54 mm: fail | [48.0, 30.0, 8.0] | 0 (pass) |
| [constant_radius_handle / usd-brep / 2](runs/constant_radius_handle/usd-brep/trial-02/row.json) | done | pass | 54 mm: pass | [48.0, 53.994, 8.0] | 0 (pass) |
| [wheel / openscad / 1](runs/wheel/openscad/trial-01/row.json) | done | pass | 120 mm: pass | [120.0, 120.0, 9.5] | 8 (pass) |
| [wheel / openscad / 2](runs/wheel/openscad/trial-02/row.json) | done | pass | 120 mm: pass | [120.0, 119.343, 9.5] | 8 (pass) |
| [wheel / usd-brep / 1](runs/wheel/usd-brep/trial-01/row.json) | done | pass | 120 mm: pass | [120.0, 120.0, 8.0] | 8 (pass) |
| [wheel / usd-brep / 2](runs/wheel/usd-brep/trial-02/row.json) | done | pass | 120 mm: pass | [120.0, 120.0, 8.0] | 8 (pass) |

## Reading the results

- Reference-only thicknesses, depths and volumes are not model requirements. Historical `overall_pass` remains in raw rows but is not used as a reliability headline.
- Wheel feature extraction and noisy view registration remain uncertain. A failed silhouette score does not by itself establish a model failure.
- A passed genus check establishes tunnel count, not opening location or complete shape.
- `ATTRIBUTION.md` records supported failure locations and unresolved causes. The interactive review page shows every cell, including errors.

[Open the visual review](review.html) · [Before/after registration](before-after.png) · [All measurements](results.json)
