# Issue #62 — Acceptance-gate calibration (genus floor)

## What this issue claimed
The #34 frozen comparison showed the product agent accepted **7/40 OpenSCAD runs** that
fail the frozen strict checks (example: bookend accepted at score 83 with 2 of 4 holes;
later live reproductions: a blind-pocket enclosure accepted at 98.4 with 0 through-holes,
a grille whose 9 "openings" were bottom-edge notches). This dossier measures candidate
calibration rules on machine-verified evidence, adopts the defensible one, and records
with data why the rest were rejected.

## Method
`scripts/calibrate_gate.py` re-scores every frozen #34 trial (80 rows: 8 drawings x 5
trials x 2 backends) plus 9 live trials (jeep 012, 003 grille regression, motor holder
103, and the 6 main-vs-branch A/B runs) offline through `evaluate_candidate` with
identical inputs (input image, spec, renders, STL), recording `through_holes`
(Euler genus), per-view crop/rendered profile counts, and per-axis mesh-vs-ink
derived-size ratios. The pre/post-gate passes come from the SAME process via the
harness `--no-gate` toggle — never from a race between two code states.
All numbers in `data/` are reproducible by re-running the harness.

## Adopted rule — R3 genus floor (in `openings_through_check`)
When strict, watertight, single-component, and some registered view demands
`N` internal openings: the mesh's Euler through-hole count must be >= N.
Rendered closed circles are not proof — blind pockets and edge notches render
identically; only topology proves the wall was removed all the way through.

Measured on the frozen set:
- removes exactly **2** false accepts: bookend/openscad/trial-05 (0 holes vs 4 demanded),
  enclosure/openscad/trial-04 (0 holes vs 2 demanded);
- rejects **0** of the 6 trusted accepted rows (zero FRR);
- newly rejects **0** runs that were previously correctly rejected (no rescues either —
  rule is purely additive on rejections).

## Rejected rule — R1 mesh-vs-ink dimension floor (documented with data, not opinion)
Any window (0.25/0.35/0.5) on labeled or sorted mesh-vs-derived-size ratios produces
false rejections of trusted rows: `wheel/usd-brep` trial-01 (false accept) and trial-02
(trusted, GT-exact) share identical ratio signatures [0.842, 4.317, 1.0] — the bounding
boxes are identical; only the 8-hole vs 1-hole topology differs — and the trusted
`profiles_empty_notes` rows contain ratio 0.424. No threshold separates the classes.
See `data/metrics.json` (`rejected_rule_R1`).

## Classes NOT addressable by the gate (follow-ups, with cases)
1. **Drawing-vs-GT proportion discrepancy** — accepted rows where the mesh is faithful
   to ink but the reference STL disagrees (enclosure/bookend frozen rows; grille 003:
   ink-derived depth 19.81 mm vs reference 3 mm; jeep 012: 4 mm GT thickness is not
   recoverable from a single-view doodle). Gate cannot enforce what the drawing does
   not contain. Follow-up: ask the user for all three dimensions when the drawing does
   not constrain an axis (clarification path exists).
2. **View-registration drop** — motor holder 103: two sketch circles never reached any
   registered view (crop=0), so no per-view rule could demand them. Follow-up issue:
   crop/registration must not silently discard internal profiles.

## Artifacts (all re-verifiable via `python audit.py`)
- `data/runs.jsonl` — frozen set under the PRE-change gate (baseline, 80 rows)
- `data/runs-newgate.jsonl` — frozen set with the shipped gate (diff = 2 removals)
- `data/runs-live.jsonl`, `data/runs-live-newgate.jsonl` — 9 live trials, same pair
- `data/metrics.json` — machine-recomputed decision summary (`calibration_decision.py`)
- `logs/full-suite.txt` — 262 passed
- `environment.json` — host/package fingerprint at capture time
- `scripts/calibrate_gate.py` (repo `scripts/`) — harness; `tests/test_evaluation_openings.py`
  — 11 tests incl. end-to-end OpenSCAD plate pair (through vs blind pocket)
