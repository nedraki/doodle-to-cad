# Demo assets

Everything here was captured against the **live app** (port 8066) with a real
local model (`Qwen3.8-Flash-Next-NVFP4` via vLLM) and real OpenSCAD compiles —
no mockups. Regenerate after any meaningful change with:

```bash
uv run python scripts/capture_demo.py       # full flow, ~4 min (runs a real generation)
uv run python scripts/capture_showcase.py   # 3D orbit + parametric edit, ~1.5 min (loads last result)
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
(orbit), `multiview_session.mp4` (full 2.5 min session),
`20–27_mv_*.png` (sheet stages, result, orbit, authoritative OpenSCAD
front/right renders), `multiview_model.scad` (the generated parametric source).

**Rejected-run evidence kept honest:** run `0d64ed50e5f5` (thinner 8% walls,
zero notes) was *rejected* by the supervisor — 95/100 with right-view
similarity 0.37 < 0.45 — after 3 attempts that fixed a missing 4th hole but
never resolved a wall/foot orientation flip. The gate works; the repair
instruction ("mirror depth, wall position") is too vague to fix a 90° intent
flip. That is the current known supervisor-prompt limitation.

## Highlights

| File | What it shows |
|---|---|
| `hero_flow.gif` | Full pipeline: pen draws an L-bookend doodle → launch → agentic generation → accepted 3D result → parametric sliders reshape the model live |
| `hero_3d.gif` | Orbiting the accepted model — the thumb hole sweeps into view, then a slider edit recompiles the mesh in place (camera untouched) |
| `demo_full.mp4` / `showcase_orbit.mp4` | High-quality MP4 versions of the same sessions |

## Screenshots

| File | Stage |
|---|---|
| `01_app_empty.png` | Fresh app: drawing sheet, model/OpenSCAD health chip |
| `02_doodle_drawn.png` | Hand-drawn front view + intent notes, ready to launch |
| `03_rocket_flight.png` | "CAD rocket in flight" — agentic pipeline working |
| `04_result_3d.png` | Accepted result: 95.1/100 supervisor score, live 3D viewer |
| `05_orbit.png` | User-orbited view of the model |
| `06_param_panel.png` | Modify mode: extracted parametric sliders |
| `07_param_live.png` | Live recompile — slider moved, mesh updated, "1 param(s) live" |
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
