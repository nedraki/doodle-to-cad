# Task 15 — Targeted recipe edits (issue #32)

Feature: with a native (usd-brep) result displayed, an engineer selects one
supported target and requests one measured change. The app mutates the
validated recipe, rebuilds through the isolated worker, and publishes a
preview only when independent mesh measurements prove the change happened
where requested and nowhere else. Keep or discard decides what is saved.

Supported edits in this task:

| Selected target | Edit | Measured proof |
|---|---|---|
| Rectangular cutout (pocket) | New pocket depth | Selected floor moves by the requested amount (ray probe); every other floor and the outer bounds stay put; no-op or under-shooting changes are refused |
| Outer vertical edge group | Fillet radius | Each corner's arc matches the requested radius within 0.1 mm; corner material is gone; bottom contact slices keep their area |

Nothing outside the selection may move. A failed measurement returns HTTP 422
with the named checks and the saved result is untouched — this is asserted
end to end, not assumed.

## What to look at (5 minutes)

1. `screenshots/01_pocket_before.png` — block 60×40×20, three pockets (depths 3, 2, 5 mm).
2. `screenshots/02_pocket_selected_control.png` — pocket cut1 selected (yellow); the
   "New pocket depth" control appeared only because a supported target is matched.
3. `screenshots/03_pocket_preview.png` — preview at depth 7 mm. The status line lists
   each measured check; `checks/pocket_depth_status.txt` has the exact text.
4. `screenshots/04_pocket_after_keep.png` and `gifs/pocket_depth_edit.gif` — kept result;
   cut1 floor moved 5→7 mm, cut2/cut3 floors did not move.
5. `screenshots/05_noop_refused.png` — asking for depth 5.0 (the current depth) is
   refused: the change measurement sees no movement; the saved STL is unchanged
   (`checks/pocket_noop_saved_unchanged.json` compares the saved file before/after).
6. `screenshots/06_bookend_before.png` → `08_bookend_fillet_after.png`,
   `gifs/fillet_edit.gif` — outer vertical edges filleted at r = 3 mm, contact
   faces preserved (`checks/fillet_status.txt`).

## Values are derived, not chosen

- Pocket depth = original depth + 2 (5 → 7 mm). The +2 rule is fixed before the run.
- Fillet radius = pocket width / 4 (12 / 4 = 3 mm) — comfortably inside every
  12–40 mm edge it touches.
- All fixtures are deterministic; no random seeds are used in this folder.

## Can the checkers actually fail? Planted errors

- `checks/planted_wrong_radius_report.json` — a mesh built with radius 0.5 mm is
  presented as radius 3.0 mm. The verifier rejects it: all four corner checks fail
  (`ok: false`). The same fixture is asserted in
  `tests/test_targeted_edits.py::test_fillet_checker_rejects_planted_wrong_radius`.
- The no-op refusal above doubles as a planted under-shoot.
- `checks/api_guards.json` — stale selection version → 409; unsupported operation →
  422; wrong target for the operation → 422. Recorded bodies included.

## Re-run it yourself

From the repository root (worker venv present, `uv sync --extra dev` done):

```bash
export DOODLE_BREP_PYTHON=$PWD/workers/brep/.venv/bin/python
.venv/bin/python docs/brep/task-15-targeted/audit.py
```

The gate re-checks `SHA256SUMS`, the recorded statuses/guard codes, and re-runs
`tests/test_targeted_edits.py` (9 tests, including two planted-error fixtures).
Full suite at capture time: **220 passed** (`pytest -q`, worker active, no skips).

## Environment

`environment.json` — git rev, product and worker Python versions, usd-brep
version, capture time. Server: `uvicorn doodle_to_cad.app:app` on 127.0.0.1:8114
started from this worktree with `DOODLE_BREP_PYTHON` set (one stale-server
capture was discarded; only the re-run on the verified worker is kept here).

## Limits (honest scope)

- Edits are limited to the two supported target/operation pairs; anything else
  is refused before a build starts (no partial support, no silent approximations).
- Drawing-evaluation checks are not rerun for targeted edits; the preview is
  marked `unverified` for drawing fidelity, same as parameter previews (#31).
- Fillet verification assumes axis-aligned box corners (outer vertical edges);
  curved-edge fillets are covered by task #13 selectors but not by this verifier.
- The web flow requires the native backend; OpenSCAD results keep the old modify path.
