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
