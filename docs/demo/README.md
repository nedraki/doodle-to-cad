# Demo assets

Everything here was captured against the **live app** (port 8066) with a real
local model (`Qwen3.8-Flash-Next-NVFP4` via vLLM) and real OpenSCAD compiles —
no mockups. The current featured set (`kit_*`) is the v3 one-take session;
regenerate it with:

```bash
DOODLE_PORT=8066 uv run python run.py &
DISPLAY=:1 TAKE_DIR=…/stills VIDEO_DIR=…/raw uv run --no-project --python 3.11 \
  --with "playwright==1.62.0" python scripts/capture_demo_v2.py   # ~5 min, one real generation
uv run python scripts/cut_demo_kit.py <take>.webm <outdir> --ramp 27:219 \
  --beats blank=4 --beats hero_sheet=24 --beats rocket=60 --beats accepted=228 \
  --beats orbit=240 --beats param_edit=246 --beats width_hint=245.5 \
  --gif drawing=6:16 --gif orbit=231:12 --gif live_edit=243:7
```

Both open a visible Chromium window on `DISPLAY=:1` and record the session.
The scripts require the dev extra (`playwright`) and a Chromium download
(`uv run playwright install chromium`).

```bash
uv run python scripts/capture_demo_multiview.py  # benchmark-style bookend sheet, ~4 min
uv run python scripts/verify_stl.py results/<run-id>/model.stl --target-max 100
```

## The multiview bookend demo (best showcase)

`capture_demo_multiview.py` hand-draws a real engineering sheet with the app's
pen — front view: plate outline with four rectangular through-cutout loops;
right view: thin-L side profile, heights aligned. Notes carry only the family
hint "L-shaped bookend"; all hole geometry must come from ink alone.

Run `ba02a7a12ca1` was accepted **100/100 on attempt 1 (91 s)**. Independent
verification (`verify_stl.py`, Euler-characteristic topology):

| Check | Result |
|---|---|
| Through-holes (genus) | **4** — exactly the 4 cutouts, in the vertical back plate |
| Components / watertight | 1 / closed manifold (edge defect 0) |
| Extents vs 80:50:100 reference ratio | 73.1 : 47.8 : 100 (rel err ≤ 9%) |

Assets: `hero_multiview_flow.gif` (draw → generate), `hero_multiview_3d.gif`
(orbit), `28_mv_orbit_isometric.png` (fixed 3/4 render via OpenSCAD
`--camera`, the clearest single still of the four through-holes),
`20–27_mv_*.png` (sheet stages, result, orbit, authoritative OpenSCAD
front/right renders), `multiview_model.scad` (the generated parametric source).

## Current social kit (v3)

The end-to-end one-take kit (hero MP4 16:9, LinkedIn 1:1, Shorts 9:16,
GIFs, posters, social copy, PRODUCTION.md with the beat timeline and
verification numbers) lives **outside this repo** at
`~/playground/media-kits/doodle-to-cad/` — one folder per product under
`~/playground/media-kits/`. Legacy remix-era MP4s (`demo_full.mp4`,
`multiview_session.mp4`, `showcase_orbit.mp4`) and superseded raw takes are
archived under its `archive-legacy/`.

**The README now features this kit.** Run `5bffe8554f0c` (seeded `rng=7`
bookend sheet) is the single source: one continuous 251 s recording → two
drafts rejected at 95.1 → attempt 3 **accepted 100/100** (190.8 s) → orbit →
Modify-drawer live edit (width 73.11 → 109.66 mm, still genus 4 / manifold
at 109.66 × 47.78 × 100.00 mm per `verify_stl.py`). The kit assets are
mirrored into this folder with the `kit_*` prefix so the repo is
self-contained:

| File (in README order) | What it shows |
|---|---|
| `kit_sketch.png` | The as-drawn input sheet: front plate + 4 cutout loops, L side profile |
| `kit_view_front.png` / `kit_view_right.png` / `kit_view_isometric.png` | Fixed-camera supervisor renders: 4 through-holes, clean L profile, all holes in one 3/4 frame |
| `kit_drawing.gif` (0.4 MB) | The pen drawing the sheet |
| `kit_flight.png` | "CAD rocket in flight" with live stage feedback |
| `kit_accepted.png` | Acceptance moment: green "✓ CAD accepted · 100/100", "best of 3 attempt(s)" |
| `kit_orbit.gif` (1.2 MB) | Orbiting the accepted bracket |
| `kit_width_hint.png` | Slider hover → on-model dimension overlay points at the feature |
| `kit_live_edit.gif` (0.5 MB) | Hover hint → slider drag → live recompile, in one beat |
| `kit_param_edit.png` | Drawer after the edit: "Edited · compiled" badge, feature highlight, "1 param(s) updated" |
| `kit_model.scad` | The 214-line parametric SCAD incl. the model's `doodle-meta` block |

Capture: `scripts/capture_demo_v2.py` (one Playwright session, real
generation); cut: `scripts/cut_demo_kit.py` (single `--ramp` over the
generation wait, no splices); posters: `scripts/make_posters.py`.
Older assets (`hero_*`, `20–27_*`, `01–07`, `30–34`, `param_drag_v2.gif`)
are from earlier sessions — kept for history and the honest-fidelity notes
below; `multiview_model.scad` is the earlier `ba02a7a12ca1` run's source
(accepted 100/100 on attempt 1, 91 s).

**Rejected-run evidence kept honest:** run `0d64ed50e5f5` (thinner 8% walls,
zero notes) was *rejected* by the supervisor — 95/100 with right-view
similarity 0.37 < 0.45 — after 3 attempts that fixed a missing 4th hole but
never resolved a wall/foot orientation flip. The gate works; the repair
instruction ("mirror depth, wall position") is too vague to fix a 90° intent
flip. That is the current known supervisor-prompt limitation.

## Highlights

| File | What it shows |
|---|---|
| `kit_*` (set) | **Featured in the README**: the v3 one-take story — draw → flight → best-of-3 acceptance 100/100 → orbit → live parametric edit (see the kit section above) |
| `hero_flow.gif` | (earlier session) Full pipeline: pen draws an L-bookend doodle → launch → agentic generation → accepted 3D result → parametric sliders reshape the model live |
| `hero_3d.gif` | (earlier session) Orbiting the accepted model — the thumb hole sweeps into view, then a slider edit recompiles the mesh in place (camera untouched) |
| `kit_v3` (in media-kits) | One-take social kit: hero MP4 + channel crops + GIFs + posters — see section above |

## Screenshots

| File | Stage |
|---|---|
| `01_app_empty.png` | Fresh app: drawing sheet, model/OpenSCAD health chip |
| `02_doodle_drawn.png` | Hand-drawn front view + intent notes, ready to launch |
| `03_rocket_flight.png` | "CAD rocket in flight" — agentic pipeline working |
| `04_result_3d.png` | Accepted result: 95.1/100 supervisor score, live 3D viewer |
| `05_orbit.png` | User-orbited view of the model |
| `06_param_panel.png` | (pre-v2 UX) Modify mode overlay card — kept for history; superseded by `30_param_drawer.png` |
| `07_param_live.png` | (pre-v2 UX) Live recompile in the overlay card — superseded by `33_param_numeric_recompiled.png` |
| `30_param_drawer.png` | Parameter drawer (v2 UX): right-side modal, slider + numeric + steppers per row |
| `31_param_after_edit.png` | Edited model in viewer after live recompile, drawer closed |
| `32_param_row_closeup.png` | One drawer row close-up: value, unit, slider, ±0.01 steppers, range hint, per-row reset |
| `33_param_numeric_recompiled.png` | Typed value 88.75 mm → recompiled, "1 param(s) updated" |
| `34_param_front_highlight.png` | Front view with feature highlight + dimension overlay after a width edit |
| `param_drag_v2.gif` | Drag-to-recompile on the v2 drawer (2026-09-28 capture) |
| `10–12_showcase_*.png` | Orbit sweep frames showing the thumb hole from both faces |

`raw/` holds the untouched Playwright recordings (kept out of git via
`.gitignore` — they are large; the MP4/GIF derivatives are the committed
artifacts).

## Honest note on fidelity

The supervisor accepted the bookend at 95.1/100 and the thumb hole is real in
the geometry, but it was cut in the foot plate rather than the vertical wall
(visible when orbiting) — the supervisor's projection-similarity check does not
yet penalise this. A good example of what the scoring gate catches today vs.
what it misses.
