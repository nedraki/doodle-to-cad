# bench-final results — merged BRep line (plan 3f5d76d)

| backend | trials | done | product-accepted | accept rate | build OK | automatic overall_pass* | ref dims/topo/vol pass** | mean score | median wall (s) |
|---|---|---|---|---|---|---|---|---|---|
| openscad | 46 | 44 | 22 | 50% | 95% | 5% | 5% (solid_transition) | 91.3 | 192.5 |
| usd-brep | 46 | 31 | 1 | 3% | 100% | 0% | 0% (—) | None | 113.4 |

\* automatic overall_pass includes `no_ground_truth` rows — it is NOT a reference match.
\** extents+genus+volume all pass against a real reference; such rows may still
     fail projection/fidelity gates and are not full model acceptances.

## Per-check pass rates (done trials)

- **openscad**: build_success 95%, extents_pass 11%, genus_pass 55%, volume_pass 5%, fidelity_pass 64%, overall_pass 5%
- **usd-brep**: build_success 100%, extents_pass 10%, genus_pass 58%, volume_pass 0%, fidelity_pass 19%, overall_pass 0%

## Top gate failures

- **openscad**: 2×openings do not go through the solid: the drawing demands 9 openings a; 2×features exist but sit at the wrong positions in front view(s): match ; 2×features exist but sit at the wrong positions in top, right view(s): m; 2×mesh has 2 disconnected components; 2×features exist but sit at the wrong positions in top view(s): match ea; 2×maximum dimension is 49 mm; target is 54 mm (tolerance 5%)
- **usd-brep**: 31×Detailed drawing features and view assignments require review.; 17×top projection; 15×front projection; 14×front openings; 10×front opening positions; 9×right projection

## Unsupported operations recorded

- **openscad**: 44×False
- **usd-brep**: 31×False

## Per-drawing (accepted / overall_pass of trials)

| drawing | openscad | usd-brep |
|---|---|---|
| 001_l_bookend_multiview | 2/2 (pass 0/2) [97.5, 97.9] | 0/2 (pass 0/2)  |
| 002_greek_vase_silhouette | 2/2 (pass 0/2) [94.2, 94.4] | 0/2 (pass 0/2)  |
| 003_front_grille_multiview | 0/2 (pass 0/2) [74.4, 78.2] | 0/2 (pass 0/2)  |
| 004_flat_mounting_plate | 2/2 (pass 0/2) [99.9, 99.9] | 0/2 (pass 0/2)  |
| 005_bolt_flange | 0/2 (pass 0/2) [98.7, 100.0] | 0/2 (pass 0/2)  |
| 006_stepped_knob | 2/2 (pass 0/2) [97.2, 92.3] | 1/2 (pass 0/2)  |
| 007_angle_bracket_holes | 2/2 (pass 0/2) [100.0, 99.7] | 0/2 (pass 0/2)  |
| 008_open_enclosure_window | 1/2 (pass 0/2) [98.4, 98.4] | 0/2 (pass 0/2)  |
| 009_hex_prism_knob | 2/2 (pass 0/2) [97.9, 95.1] | 0/2 (pass 0/2)  |
| 010_nameplate_slots_vents | 2/2 (pass 0/2) [98.6, 99.5] | 0/2 (pass 0/2)  |
| 011_wall_hook | 2/2 (pass 0/2) [96.7, 97.8] | 0/2 (pass 0/2)  |
| 012_vent_grille_grid | 2/2 (pass 0/2) [94.6, 94.6] | 0/2 (pass 0/2)  |
| 013_wedge_ramp | 0/2 (pass 0/2) [84.0, 85.9] | 0/2 (pass 0/2)  |
| 101_bltouch_bracket | 0/2 (pass 0/2) [72.6, 49.8] | 0/2 (pass 0/2)  |
| 102_lcd_knob | 1/2 (pass 0/2) [96.7, 95.9] | 0/2 (pass 0/2)  |
| 103_y_motor_holder | 0/2 (pass 0/2) [69.7] | 0/2 (pass 0/2)  |
| 104_cable_holder | 0/2 (pass 0/2) [84.6, 76.0] | 0/2 (pass 0/2)  |
| bevelled_block | 2/2 (pass 2/2) [99.7, 99.7] | 0/2 (pass 0/2)  |
| constant_radius_handle | 0/2 (pass 0/2) [86.5, 74.0] | 0/2 (pass 0/2)  |
| rectangular_sweep | 0/2 (pass 0/2) [92.7] | 0/2 (pass 0/2)  |
| rounded_housing | 0/2 (pass 0/2) [72.1, 94.6] | 0/2 (pass 0/2)  |
| solid_transition | 0/2 (pass 0/2) [94.4, 94.4] | 0/2 (pass 0/2)  |
| wheel | 0/2 (pass 0/2) [100.0, 100.0] | 0/2 (pass 0/2)  |
