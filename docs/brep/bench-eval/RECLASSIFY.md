# Re-scoring with proven-unreliable checks marked (issue #81)

Frozen bench-final verdicts are NOT modified. A check is ignored only
where CASES.json carries a VERIFIED evaluator/input defect; ignored does
not mean passed — the cell is judged by its remaining reliable checks.

A reclassified pass means only: the bench's *reliable* checks found no
failure. It is not a truth verdict — ATTRIBUTION.md still assigns some
reclassified cells to model failures (e.g. the 007 plate, whose genus
equals the bracket's: the bench simply has no reliable check left that
can see the bend). This file measures the bench, not the parts.

| backend | cells | overall_pass (frozen) | reclassified (reliable checks only) | unjudgeable (all measuring checks proven broken) |
|---|---|---|---|---|
| openscad | 46 | 2 | 9 | 0 |
| usd-brep | 46 | 0 | 2 | 0 |

## Cells whose verdict changes

- 004_flat_mounting_plate / openscad trial-01: False -> True (ignored ['extents_pass', 'volume_pass', 'fidelity_pass'] per EV-1+EV-7; still-failing reliable checks: none)
- 004_flat_mounting_plate / openscad trial-02: False -> True (ignored ['extents_pass', 'volume_pass', 'fidelity_pass'] per EV-1+EV-7; still-failing reliable checks: none)
- 004_flat_mounting_plate / usd-brep trial-01: False -> True (ignored ['extents_pass', 'volume_pass', 'fidelity_pass'] per EV-1+EV-7; still-failing reliable checks: none)
- 007_angle_bracket_holes / openscad trial-01: False -> True (ignored ['extents_pass', 'volume_pass'] per EV-1; still-failing reliable checks: none)
- 007_angle_bracket_holes / openscad trial-02: False -> True (ignored ['extents_pass', 'volume_pass'] per EV-1; still-failing reliable checks: none)
- 008_open_enclosure_window / openscad trial-02: False -> True (ignored ['extents_pass', 'volume_pass'] per EV-1; still-failing reliable checks: none)
- wheel / openscad trial-01: False -> True (ignored ['volume_pass', 'fidelity_pass'] per EV-5+EV-2; still-failing reliable checks: none)
- wheel / openscad trial-02: False -> True (ignored ['volume_pass', 'fidelity_pass'] per EV-5+EV-2; still-failing reliable checks: none)
- wheel / usd-brep trial-02: False -> True (ignored ['volume_pass', 'fidelity_pass'] per EV-5+EV-2; still-failing reliable checks: none)
