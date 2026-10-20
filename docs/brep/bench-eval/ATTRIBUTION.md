# First-demonstrated-failure attribution (issue #81, milestone 3)

v2 — every row re-read from archived `row.json`/`result.json`/`model.scad`/
`model.recipe.json` bytes. v1 claims inherited from session notes that the
bytes did not support are corrected (see CASES.json `correction_record` and
EV-4's REFUTED status). Pipeline stages, checked in order per case; the
verdict is the FIRST stage with evidence of failure; later symptoms are
never blamed for an earlier failure. Classes: `model` (LLM response),
`pipeline` (parsing/execution/kernel/contract), `evaluator` (our checks),
`input` (brief/reference underspecification). No cause is assigned from a
screenshot; each row cites the artifact bytes.

| case / rows | first failing stage | class | evidence (retained bytes) |
|---|---|---|---|
| wheel openscad t1/t2 | **evaluator/image-measurement** — every explicit sheet fact passes (extents ✓ genus 8 ✓ fidelity ✓); product REJECTED both score-100.0 rows via the 27.8 mm heuristic (EV-3), and the only failing harness check is volume vs the author's undimensioned rim/spoke widths (EV-5) | evaluator + input | row.json checks + product.accepted=false@100.0; drawing-checks.json; reference.scad L4-6 |
| wheel usd t1 | **pipeline** — kernel non-manifold on spoke `union_2` (twice in frozen comparison; no minimal reproducer retained — disclosed) | pipeline | row.json error |
| wheel usd t2 | same evaluator/input family as openscad rows (+ harness fid False on a correct-shape part: EV-2 extraction undercount) | evaluator + input | row.json; drawing-checks.json |
| 004 openscad t1/t2 | **input** — thickness absent from ink/notes/form and never asked→never answered (EV-8); model silently guessed 10 mm (GT 5): extents/volume checks unachievable by any compliant model (EV-1 fixture proof). Shape was right: 3 openings ✓, product 99.9 | input + evaluator | request.json form (no thickness, ask_missing_dimensions=false); row.json ext [100,10,62] g3 |
| 004 usd t1 | **evaluator** — same correct part (3 mm, genus 3 ✓), orientation flipped vs openscad, fidelity flipped True→False: 'front expects 3, renders 0 / top expects 0, renders 3' (EV-7) | evaluator | row.json fidelity.topology both backends |
| 004 usd t2 | **model** — contract rejection 'Expected canonical world frame'; the canonical frames block is given VERBATIM in the model prompt (direct_brep.py:23), so this is a documented-contract violation. Rejected payload not retained (disclosed) | model (documented contract) | request/response bytes; direct_brep.py:23 prompt text |
| 007 openscad t1/t2 | **input/evaluator** — model built the CORRECT L-bracket (scad base+wall+3 holes, genus 3, product 100.0/99.7); extents/volume fail only on hidden depth 40/height 50 (EV-1). No model failure in these rows | input + evaluator | model.scad; row.json ext [80,43.13,51.01] |
| 007 usd t1 | **model** — flat plate [80,40,5] where notes+GT demand a bend; CAUGHT by harness (front similarity 0.35) AND product (accepted=False). EV-4 refuted — the bench sees this | model | row.json fidelity+product |
| 007 usd t2 | **model** — contract rejection 'Unsupported clarification or unknown feature'; the four permitted kinds are enumerated in the intent prompt — documented-contract violation (rejected payload not retained, disclosed) | model (documented contract) | row.json error; construction_intent.py kind set |
| 101 openscad t1 | **model** — genuine 3D part but genus 3 vs GT 5: flanges/tabs under-built on the richest ink in the corpus; reliably caught by the visible-topology check; product rejected 72.6 | model | row.json genus; product.failures |
| 101 openscad t2 | **model/pipeline** — same geometry, mesh validation failed (build_success false) | model (output) | row.json build |
| 101 usd t1/t2 | **model** — flat plates [40,50,4]/[40,50,3]; all checks correctly fail | model | row.json |
| 003 openscad t1/t2 | **model** — zero through-openings (genus 0) where ink shows 9 + wrong outline; product rejected with exact missing-cutter list — evaluator behaved perfectly here | model | row.json genus + product.failures |
| 003 usd t1 | **model** — 8 openings vs the 9 in ink (miscount on a fully-specified case); genus check reliably catches | model | row.json genus 8 vs GT 9 |
| 003 usd t2 | **model** — genus 2 | model | row.json |
| 008 openscad t1 | **model** — box WITHOUT the window (genus 0 vs 1; window is an ink-visible requirement — reliably caught) | model | row.json genus |
| 008 openscad t2 | **input/evaluator** — window correct (genus 1 ✓, product accepted 98.4); failing axes [81.68, 43.96] are the hidden depth/height (EV-1; only '120' in brief) | input + evaluator | row.json ext vs references |
| 008 usd t1/t2 | **model** — ignored the explicit '120' field ([100,50,40]/[100,60,40]); extents reliable here (120 IS in the brief) | model | row.json ext |
| handle openscad t1 | **model** — real arc band (good) but rod_diameter=9 vs ink Ø8 and leg 33.75 back-solved from the unlabeled '54' (EV-6) instead of the consistent reading (30+20+4) | model + input | model.scad constants; row.json |
| handle openscad t2 | **model** — build failed validation | model | row.json |
| handle usd t1/t2 | **model — RESOLVED by level-2 replay** — saved recipe bytes replay flat [48,30,8] faithfully; capability variant (arc_pipe → rotate 90° about x → cylinder legs → unions) reaches [48,8,54.0], volume 6174.2 vs GT 6170.5 (+0.1%). Pipeline exonerated; the model wired the arc to leg bottoms and never rotated it | model | replays/handle_*.diagnostics.json; replay_handle.py |

## What this means for the LLM-vs-pipeline question

1. **Genuine model failures (visible-requirement violations, reliably
   caught):** plate instead of bracket (007 usd), no openings at all (003
   openscad), 8 vs 9 openings (003 usd), plates instead of the 3-view
   bracket (101), window omitted (008 t1), ignored explicit dimension field
   (008 usd ×2), misread Ø8→9 (handle), flat recipes where rotation was
   available (handle usd).
2. **Failures that are OURS, not the model's:** hidden GT dimensions
   (EV-1: 004 thickness, 007 depth/height, 008 depth/height, 101 x/z),
   wheel volume vs author's undimensioned choices (EV-5), orientation-
   dependent fidelity (EV-7), broken wheel opening checks (EV-2), and the
   27.8 mm heuristic that rejected the two best parts in the corpus (EV-3).
   Frozen pass rates therefore both understate the model (wheel, 004, 007,
   008 openscad rows) and there is no inflation from EV-4 (refuted).
3. **Acceptance behaved better than v1 claimed:** it caught the 007 plate,
   the 003 blind pockets, the 101 under-build — EV-4 is dead. Its one
   proven failure direction is the wheel false rejection (EV-3).
4. **Pipeline defects: two solid, two open.**
   Solid: usd kernel non-manifold on spoke unions (no reproducer retained —
   disclosed); harness/worker view-orientation inconsistency feeding EV-7.
   Open (EV-9): two contract rejections where model-vs-contract blame is
   unresolved pending a contract-vs-recipe documentation comparison.
5. **Op-contract note:** `arc_pipe` ignores `frame`/`frames` and is
   XY-planar only; z-rising arcs need arc_pipe + rotate. The correct handle
   IS expressible (+0.1 % replay); the model never wrote it.

## Next probes

- DONE: EV-7 rotation probe (EV7_PROBE.md) — 004-class failure proven
  orientation-caused (best-of-24 IoU 0.76 vs 0.45 bar); wheel front not
  excused (0.27 — EV-2 primary). Harness fix (best-of-24-rotations scoring)
  must ship as a NEW plan revision + re-run, never on frozen numbers.
- Retention gap (proposed product issue): rejected construction plans and
  kernel-crash inputs must be written to the cell dir (attempts.json), so
  EV-9-class blame can be byte-verified for the exact offending value and
  the wheel spoke-union kernel crash can get a minimal reproducer.
- EV-7 fix prototype: assign view groups per-backend render orientation
  (or normalize part orientation before scoring), re-score 004/wheel rows.
- Live current-model baseline (level 3) only after these — with
  `ask_missing_dimensions` decided per experiment, recorded in environment.json (#85).
