# Direct BRep generation — front grille, full operation vocabulary

Run `9f9fbc42cf6b`, branch `codex/brep-06-direct-generation`, commit `b227712`.
The pipeline built this part from the hand-drawn front view without OpenSCAD.
It emitted recipe v2 operations directly: `extrude` (protected profile
extrusion), `rotate`, `box`, `cylinder`, `difference`. The usd-brep kernel
built the solid in 0.207 s.

## Result (machine-checked)

| Check | Result | Evidence |
| --- | --- | --- |
| Connected solid | passed | watertight, 1 component (`run.log`) |
| Requested maximum | passed | 117.22 mm of 120 mm limit |
| Front projection | passed | similarity 0.998 (minimum 0.45) |
| Front openings | passed | 9 of 9 required |
| Front opening positions | passed | feature_position_fidelity 1.0 |
| Front outer silhouette | passed | silhouette_fidelity 1.0 |
| Top projection | passed | similarity 0.963 |
| Top outer silhouette | passed | silhouette_fidelity 1.0 |

Solid: extents 117.22 x 6.00 x 72.08 mm, watertight, Euler −16
(consistent with 17 through-cut faces), 724 triangles, USD round-trip true.
Source: `built.json`. The final LLM review step stays `unverified`
("Detailed drawing features and view assignments require review"), as in
the pre-change baseline. All numeric gates above are programmatic.

## What the drawing asked for, and what the model produced

`model.recipe.json` — 20 operations:

- `plate` extrude: the measured `polygon_mm` outer contour (17 line edges,
  verbatim from `geometry.json`) extruded with `depth: thickness`,
  `direction: -1`, then `rotate` (axis x, angle 90) stands it in XZ.
- 7 slat cutters (`box`, size from `slat_width`/`slat_height` parameters)
  and 2 headlight cutters (`cylinder`, `headlight_radius`), all spanning
  y = −0.1 .. thickness + 0.1 so they cut through.
- 9 `difference` operations plus the final `difference`.

Exposed parameters: `thickness` 6.0 (user clarification answer),
`slat_width` 4.86, `slat_height` 45.51, `headlight_radius` 9.845.

Rendered opening centroids match the drawn centroids within 0.002 of
normalised width and 0.012 of normalised height (`drawing-checks.json`,
source_opening_centroids vs rendered_opening_centroids).

## Clarifications (asked, answered, honoured)

`clarifications.json`: `uniform_thickness` on the plate answered 6.0 mm;
`opening_extent` on the grille openings answered `through`. The measured
millimetre coordinates came from `geometry.json` (measured ink spans, not
model guesses): `feature-evidence.json`, `geometry.json`.

## Corrections (bounded, guarded)

One construction correction ran. The first build floated the plate
(`minimum_z_mm = 1.6`; `construction-correction-1.request.json`). The
correction model lowered the rotate-pivot/extrude-origin Z fields. The
guard kept every non-numeric field fixed, so the protected profile could
not be redrawn (`construction-correction-1.recipe.json`). Earlier live
runs showed the guard rejecting an attempt to edit `loops` — the intended
behaviour.

## Environment fingerprint

usd-brep worker 1.0.0 (`built.json`), prompt versions
`drawing-brep-19`, `construction-numeric-fields-4`,
`construction-intent-12`. Worker python: `workers/brep/.venv` (3.12).

## Reproduce

```
DOODLE_BREP_PYTHON=$PWD/workers/brep/.venv/bin/python PYTHONPATH=$PWD \
  uv run pytest tests/test_direct_brep.py -q        # 27 passed
```

Re-running the live job needs the configured local model endpoint. The
saved `run.log` and JSON files above are the primary evidence; renders
are copies of the worker's own view images.

triptych.png: drawn input | built front | built isometric.
orbit.gif: front, isometric, right, top loop of the built solid.
