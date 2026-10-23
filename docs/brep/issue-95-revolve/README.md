# Issue #95 — bounded revolve: live demo evidence

Branch `hermes/issue-95-revolve`, implementation commit `88fa0ec`, base
`origin/brep-integration` @ `dbc96d1`. Worker Python 3.12.3 with
usd-brep==1.0.0, product venv trimesh 5.1.0, model
`local-inference-lab/Qwen3.8-Flash-Next-NVFP4` (auto-discovery, port 8000),
evidence server `127.0.0.1:8135`.

## Hypothesis verdicts (Codex report, independently re-verified)

| # | Hypothesis | Verdict | Evidence I re-checked |
|---|---|---|---|
| 1 | Missing exposed revolution op | **CONFIRMED — fixed here** | `usd_brep.rotational_sweep` exists in worker venv; zero references in recipe FIELDS/dispatch/prompt at `dbc96d1`; vase trial-1 error names the op gap |
| 2 | Model/planning failure | Confirmed, secondary | `../bench-final/runs/002_greek_vase_silhouette/usd-brep/trial-01` (`unsupported_construction`), `trial-02` (`unresolved_design`), `006_stepped_knob/trial-02` (`invalid_recipe`) |
| 3 | Cylinder-union constraints | Real, separate family | joint1 overlap guidance in archived prompts; not touched here |
| 4 | Kernel lacks revolutions | Contradicted | `/tmp/brep-revolution-investigation/*.json`: 4 probes, native vs analytic agreement, round-trip < 1.8e-8 |
| 5 | Invalid profiles/seam defects | Unsupported for these failures | — |

## What the fix exposes

One recipe operation, validated before any kernel launch and built behind all
existing worker guards (manifold, watertight mesh, one component, Z=0
placement, staged USD round-trip publish):

    {"id":"part","kind":"revolve","origin":[0,0,0],"axis":"z",
     "profile":[[r,z],...]}

Closed radius-height polygon, fixed +Z, full 360 degrees.
Validator: `doodle_to_cad/revolve_profile.py`. Fixtures
(`tests/test_revolve.py`, KERNEL-gated): cylinder, annulus, stepped knob,
solid vase (matches the archived native probe volume to 1e-4 relative) and a
hollow vessel at 117398.97 mm3, 1.5e-8 relative to the analytic Pappus value.
Full suite at this commit: 344 passed, 11 skipped.

## Live app demo (product path, not raw worker)

`POST /api/generate`, backend `usd-brep`, drawing
`benchmarks/cases/002_greek_vase_silhouette/source/drawing.png`,
dimension 120, certified notes from the frozen bench-final plan row.

| Trial | Notes | Verdict | Built mesh (trimesh, independent of product gate) |
|---|---|---|---|
| `A-certified` | plan-row notes verbatim; user answered the opening_extent clarification with "leave a bottom, 116 mm" | built; product `status=unverified` (usd-brep rows are verdict-by-review by design) | watertight, 1 component, genus 0, 80×80×120 mm, V=82086.9 mm3; single `revolve` op, 16-vertex hollow profile, params: height/max_radius/wall/floor/recess_depth |
| `B-hollow-specified` | notes add open top, wall 4 mm, floor 4 mm | built in 113 s | watertight, 1 component, genus 0, 90×90×120 mm, V=98661.9 mm3; single `revolve` op, 7 editable params incl. belly/neck/rim radii |

Ground truth for reference: watertight, genus 0, 102.5×102.5×120 mm,
V=116828.8 mm3. Both builds are **thinner in the belly than GT** — the ink
proportions are the remaining fidelity gap; the construction class is now
correct (one hollow revolved solid, wall and floor honoured).

Before/after: on `dbc96d1` the same drawing produced zero meshes
(`unsupported_construction` / `unresolved_design` — archived under
`../bench-final/runs/002_greek_vase_silhouette/usd-brep/`).

## Reproduce

    git worktree add /tmp/doodle-brep-95 hermes/issue-95-revolve
    cd /tmp/doodle-brep-95 && uv sync --extra dev
    cp <main-checkout>/.env .env
    DOODLE_PORT=8135 DOODLE_BREP_PYTHON=<repo>/workers/brep/.venv/bin/python \
      PYTHONPATH=$PWD uv run python run.py &
    PYTHONPATH=$PWD uv run python docs/brep/issue-95-revolve/demo_driver.py [A-certified|B-hollow-specified]
    # Trial A asks opening_extent; answer like the UI:
    curl -X POST http://127.0.0.1:8135/api/generate/<job>/answer \
      -H 'content-type: application/json' \
      -d '{"question_id":"<id>","choice":"recess","depth_mm":116}'
    CHROMIUM_EXECUTABLE=<chromium> PYTHONPATH=$PWD \
      uv run python docs/brep/issue-95-revolve/make_evidence.py

## Files

Per trial dir: `request.json` (form + input sha256), `job.json` (full server
state incl. clarification question/answer), `model.recipe.json`,
`model.stl`, `model.usda`, `construction-plan.json`,
`clarifications.json`, `drawing-checks.json`, view PNGs, `triptych.png` +
`orbit.gif` with `provenance.json` binding montage sha256 → panel artifact
sha256 → job id. Captions quote measured row values only.
