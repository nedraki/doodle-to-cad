# Issue #67 — View registration silently drops internal profiles (fix + evidence)

Case: motor holder 103 (`benchmarks/cases/103_y_motor_holder`, live run `7c274ef76d20`).
The doodle shows **4 circles**, but every registered view's crop count summed to **2**
(front=0, top=2, right=0) — the hook elevation's pair was invisible to registration, so
no per-view gate could demand the lost openings and the product was **accepted at 95.8
with 2 of 4 bores**.

## Root cause (measured)

`scripts/issue67_diagnose.py` on the case drawing (logs `diagnose-before.txt`): the four
openings are thick-pen stroke rings, each an outer boundary + inner-edge child. The two
circles inside the top view's closed outline sit at hierarchy depth **2** (registered).
The hook elevation's outline is an open shape that does **not enclose** its two circles:
they are standalone ink islands at hierarchy depth **0/1** (contour_0 area=394
circularity=0.890 and contour_2 area=359 circularity=0.860, child ratios 0.30/0.26).
Both registration layers filtered on absolute hierarchy depth — `analyze_image`'s
`closed_internal_profile` (`depth >= 2`) and `evaluation._crop_internal_profile_count`
(`depth == 2`) — so the pair was counted **nowhere**: sheet said 2, registered crops
said 2, the drawing said 4.

## Fix (registration, not gates)

`doodle_to_cad/geometry.py`: a small round stroke ring (circularity ≥ 0.75, stroke child
covering 15–92 % of its own area, ≤ 15 % of its view group's dominant contour area, < 8 %
of sheet, center inside a view group) now registers as a `closed_internal_profile` at any
even hierarchy depth — captured from the RAW contour set before the top-80 truncation
(`orphan_opening_ring` flag on shapes). Thresholds from the corpus: hand-inked circles
measure circularity 0.84–0.92; view silhouettes ≤ 0.57 (a wobbly rectangle hit 0.570).

`doodle_to_cad/evaluation.py`:
* `_crop_internal_profile_count` counts the same orphan rings inside a crop (the depth-2
  rule is untouched, so single-view sheets are bit-identical).
* Demanded openings is now the **sum of registered per-view crop counts** — each
  registered view demands its own openings and one solid must satisfy all views. The
  features gate compares per view (a view rendering nothing can no longer hide behind
  another view's satisfaction). For sheets with openings in one view only — the shape of
  **all 80 frozen #34 rows, measured** — sum == the old best-view max.
* Registration-gap fail-safe: if the sheet shows > 1 more internal profiles **inside a
  registered view** than crops counted, demand the sheet total (the guard is
  registered-group-scoped: rings in unregistered clusters — title blocks, notes — must
  not inflate the demand; see iteration history below).

## Offline acceptance — motor-103 (`scripts/calibrate_gate.py --live`)

Field path: `docs/brep/issue-62-gate/data/runs-live-newgate.jsonl`, row with
`drawing == "motor-103-accepted"`, field **`demanded_openings.total`**.

| | before (frozen #62 row) | after |
|---|---|---|
| crop counts (front/top/right) | 0 / 2 / 0 | 0 / 2 / **2** |
| demanded openings | **2** (`profile_topology` best-view max) | **4** (`demanded_openings.total`) |
| through_holes | 2 | 2 |
| verdict | **accepted @ 95.8** | **rejected @ 75.8** (features=False, openings_through=False) |

Failures now raised: “right demands 2, renders 0, top demands 2, renders 2 …” and
“the drawing demands 4 openings across the registered views … the mesh has 2 true
through-holes — blind pockets or edge notches”.

## Frozen 80-row pass — demanded-count changes: NONE

`scripts/calibrate_gate.py` was run at base `24946c7` (data snapshot
`data/runs-newgate-base-24946c7.jsonl`) and on this branch; every row compared
(`logs/calibrate-*.txt`):

* verdict flips: **0 / 80**; crop-count changes: **0 / 80**; demanded-total changes
  (new total vs old best-view max): **0 / 80**; 26 trusted rows: verdicts identical.
  Every frozen row has openings demanded by at most one view (measured: 0 rows have
  non-zero crop counts in > 1 view), so sum == max by construction.
* Live rows unchanged except motor-103 (intended flip). `grille-003-regression` score
  drifted 81.1 → 74.5 (per-view feature score no longer lets `top`'s 3 rendered holes
  partially satisfy `front`'s demand of 9) — verdict unchanged (rejected both times).
* Iteration history (measured, not hidden): the first guard iteration escalated on any
  sheet-vs-crop gap and flipped **5 trusted `profiles_empty_notes` usd-brep rows**
  (accepted → rejected) because that sheet's 4 depth-2 rings live in a big group the
  view assigner never registered (it registers thin text strips as views there). The
  registered-group filter above restores those 5 verdicts; verified 0 flips after.

## Tests

`tests/test_view_registration.py` (12 tests): deterministic cv2-planted sheet — closed
view with 2 enclosed circles + an **open** hook elevation carrying 2 unenclosed circles
(the planted error). Asserts the old rules count 2 of 4 (`_old_sheet_count == 2`,
hook-view `_old_crop_count == 0`) while the fixed rules count 4 and 2; per-view
assignment 2/2/0; sum == sheet; demanded-openings guard escalation, no-escalation at
gap ≤ 1, per-view features gate, and the 2-of-4-bores rejection through
`evaluate_candidate`. Full suite: **304 passed, 2 warnings** (baseline at base commit:
292 passed, 2 warnings) — `logs/suite.txt`.

## Reproduce

```bash
cd /tmp/doodle-brep-67   # branch hermes/issue-67-registration (base 24946c7)
DOODLE_BREP_PYTHON=$PWD/workers/brep/.venv/bin/python PYTHONPATH=. .venv/bin/pytest -q
.venv/bin/python scripts/issue67_diagnose.py                       # before/after logs
.venv/bin/python scripts/calibrate_gate.py --live                  # motor demanded 4
.venv/bin/python scripts/calibrate_gate.py                         # frozen 80 rows
.venv/bin/python docs/brep/issue-67-registration/audit.py          # 26/26 checks
```

## Contents

* `audit.py` — rerunnable, asserts every claim above (26 checks incl. full-suite count).
* `logs/` — `diagnose-before.txt`, `diagnose-after.txt`, `suite.txt`,
  `calibrate-frozen.txt`, `calibrate-live.txt`, `audit-last-run.txt`.
* `data/` — `runs-live-baseline.jsonl` (pre-fix #62 row), `runs-newgate-base-24946c7.jsonl`
  (frozen baseline at base commit), `live-job/` (frozen live-job inputs: `input.png`,
  `registered-right.png`, `registered-top.png`, `evaluation.json` from `attempt-01/`).
* `environment.json` — git head/branch, python versions, worker kernel via
  `importlib.metadata.version("usd-brep")` == 1.0.0 (`usd_brep` has no `__version__`).

## Known limitations (measured or reasoned)

* Same openings mirrored in two registered views (left AND right registered) would be
  counted twice by the demanded total. Not observed in the corpus (80 frozen + 9 live
  rows): multi-view demand exists only on motor-103, where 4 distinct bores is ground
  truth.
* `_profile_centroids` (position fidelity) was left unchanged: it still detects only
  depth-2 rings, so orphan openings are demanded by count but not yet pinned by
  position. Extending it was measured to change projection scores on rows the count fix
  doesn't touch; deliberately deferred.
* Hand-inked round glyphs (o, e) inside a view group could register as rings; the
  dominance cap (≤ 15 % of the group's largest contour) and min-area floor bound the
  damage, and the fail-safe direction (over-demanding openings) matches the issue's
  intent.
