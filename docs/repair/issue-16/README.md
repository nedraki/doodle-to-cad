# Issue #16 — Targeted post-generation repair: "this part is close — change only what I describe"

Issue #16. Branch `hermes/issue-16-targeted-repair`. Base `brep-integration@01de9dd`; target `brep-integration` only. Main untouched.

## What changed

On an OpenSCAD result, a **Fix this part** button opens a correction box. One sentence describes the single change wanted; the app builds a separate **repair candidate** from the version currently displayed — including successfully applied parameter edits — and shows it with: your correction, the model's interpretation (requested change vs properties intended to stay unchanged), what it started from, and a check list with measured before→after values. **Keep repair** makes it current, **Discard repair** returns to the pre-repair version, **Refine instruction** builds again from the displayed candidate. Every step is a revision with its parent; the original files, parameter values and generation report stay available and downloads plus parameter controls always match the displayed revision. A candidate is explicitly *unverified* for drawing acceptance — the original generation score is never carried over.

Measured checks (trimesh-backed, never compilation alone): compiles, watertight, connected components (counted separately from watertightness — several watertight bodies are still not one part), extents within the documented tolerance (±2 % relative or 0.5 mm absolute), editable-parameter changes reported rather than hidden, volume measured. Whether the requested correction is semantically achieved stays `unverified` and is judged visually next to the interpretation. Model, compile or validation failures return an explained error and leave the last valid displayed result untouched; a stale keep/repair loses against a newer selection (409).

## Wheel case (the motivating example)

The pre-repair wheel is a **controlled fixture** (`scripts/make_repair_fixture.py`, derived from `benchmarks/brep-baseline/wheel/reference.scad` with spokes pulled 5 mm short of the rim), seeded into the app — the generation step is not a model-quality claim. The repair itself is real: live model calls through `POST /api/results/{id}/revisions/repair`, driven from the browser (test server on port 8116 only).

| Check (trimesh, independent of the app's own) | Before | After | Verified |
|---|---|---|---|
| Connected components | 2 | **1** | measured |
| Watertight | true | **true** | measured |
| Extents X/Y/Z (OD, thickness, OD) | 120 / 8 / 120 | **120 / 8 / 120** | measured |
| Hub full-cover radius | 15 mm | **15 mm** | measured |
| Spoke count (r=40 band) | 8 | **8** | measured |
| Spoke arc width (r=40) | 8.03 mm each | **8.03 mm each** | measured |
| Material in former gap band r=50–53 | none | **8 spokes bridging** | measured |
| Requested correction semantics | — | review | **visual + model interpretation only** |

The kept source shows the minimal intended edit: `spoke_reach` 34 → 40 (spokes now overlap the rim wall by 1 mm), every other parameter untouched. `product-final/report.json` holds all values; `product-final/kept-model.scad` and `product-final/artifacts/` the files. Screenshots: `broken.png`, `repair-candidate.png`, `repair-kept*.png`, `second-candidate.png`, `discard-restored.png`. The isometric view renders the 5 mm overlap subtly, so `repair-kept-front.png` is the view to judge visually; the radial probes above are the authoritative connectivity evidence (one watertight component plus material bridging the former gap band at r=50–53).

Refinement evidence (`refine-*.png`, `refine-report.json`): candidate 1 → **Refine instruction** → candidate 2 whose `parent_id` is candidate 1 (refine operates on the displayed candidate), and Discard returns to `original` with both candidates still in history.

## App demonstration sequence (product-final/)

1. Seeded broken wheel renders; check list shows 2 components.
2. Fix this part → wheel instruction → candidate: all checks pass (`connected_components 2→1`), selection still `original`.
3. Keep repair → downloads and parameter controls follow the candidate; original downloads stay under "Original generation downloads".
4. New candidate from the kept part ("Make the hub slightly larger") → Discard → kept repair restored, hrefs match.
5. Stale keep (old selection_version) → 409; displayed version unchanged.
6. Separate refine run: candidate → refine → parent chain verified; discard returns to original.

## Test suite

`initial-tests.txt` records the suite as left by the previous agent: **4 failed, 230 passed** — all four were test-side defects (a `stub_mesh` substring match that pytest's `test_repair_*` tmp dir names falsely matched; a test reading the wrong message part; two endpoint tests missing an `api.pipeline` stub, which would have hit the live model). Root-caused and fixed with the design intent kept; a no-change-parameters `passed` case was added. `tests.txt`: **234 passed, 0 skipped, 0 failed** (211 pre-existing + 23 repair tests), Python 3.11.16, BRep worker venv present (usd-brep 1.0.0) so no skips.

## Failures and attempts retained

- `initial-tests.txt` — the 4 failing tests above.
- `product-run1-crashed-after-keep/` + `product-run1-source-text-crash.log` — first full product run: repair kept successfully, then the *capture script* (not the app) crashed reading a non-existent `source_text` key from the API response. Its complete evidence (including a one-attempt successful repair) is retained.
- `invalid-runid-failure.txt` — first seeding attempt used a non-hex run id; real "Unknown run" response recorded.
- `rtree-missing-failure.txt` — reproduced `ModuleNotFoundError` that trimesh's `mesh.contains()` raises without the dev-only `rtree` package (worktree venv; pyproject unchanged).
- `regressions/` — fresh OpenSCAD generations (seed 20261018 in `selection.json`): knob **accepted (99)**; wheel 82 **not accepted — 2 disconnected components** (exactly the condition this feature repairs); bookend 94.9 and cable holder 87.8 rejected on projection/feature scores; random `103_y_motor_holder` 85.8 not accepted. No clarifications requested, none guessed.

## Limits and honest labels

- Semantic achievement of the correction is **visual-only** by design (`requested_correction: unverified`); the measured evidence is connectivity + preserved dimensions.
- The repair requires an OpenSCAD parent; BRep results are out of scope for #16.
- The pre-repair wheel is a synthetic fixture, and the regression wheel's failure is the model's generation behavior, unchanged by this work.
- `refine` inherits the same trust model: every candidate is a separate revision; discards remain in history as evidence.
- Model nondeterminism: the wheel repair succeeded on the first attempt in both scripted runs; the refine flow tolerates and retains failed attempts rather than guaranteeing convergence.

## Provenance and how to reproduce

Branch `hermes/issue-16-targeted-repair` @ base `brep-integration@01de9dd`, PR to `brep-integration` (not merged by this task). Server: `uv run uvicorn doodle_to_cad.app:app --host 127.0.0.1 --port 8116` from the worktree with `.env` from the main checkout (model served at `http://127.0.0.1:8000/v1`, never restarted by this task). Captures: `scripts/check_repair_product.py`, `scripts/check_repair_refine_ui.py`, `scripts/check_repair_regressions.py`, `scripts/make_repair_fixture.py` (chromium `chromium-1243/chrome-linux-arm64` with swiftshader flags). Playwright logs: `product-final-run.log`, `refine-ui-run.log`, `regressions-run.log`.
