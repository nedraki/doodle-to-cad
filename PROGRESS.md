# PROGRESS — doodle-to-cad reliability program

North star: the benchmark. Mission: expand benchmark → measure → fix coordinate
reliability → re-measure. Instructions archived in `initial_user_request.md`.

## Status legend
[ ] pending | [x] done | [~] in progress

## Phase 0 — Environment (done)
[x] venv rebuilt: old `.venv` pointed at a dead previous-user python path. New env: `.venv-new` (uv, py3.12, editable install). Run: `PYTHONPATH=$PWD .venv-new/bin/python ...` from this worktree.
[x] OpenSCAD restored: no host binary (apt needs sudo password). Docker fallback implemented in `doodle_to_cad/openscad.py` — set `DOODLE_OPENSCAD_DOCKER=openscad/openscad:latest` in `.env`. Compiles STL + renders 4 ortho views (~3 s/model). Pitfall found: `xvfb-run` hangs in that image; the fallback spawns `Xvfb :99` manually.
[x] Model endpoint OK: `http://127.0.0.1:8000/v1` (vLLM, container `local-vlm`), model auto-discovery prefers vision markers.
[x] `pytest -q` = 27 passed (main tree).
[x] Worktree: `../doodle-to-cad-bench` branch `benchmark-plus` off `b0c4507`.

## Phase 1 — Coordinate-system audit (done; smoking gun found)
Method: systematic-debugging probes `experiments/coord_contract_probe*.py`.
Measured where world +X/+Y/+Z land in each pipeline camera render (notch/hole
silhouette analysis + vision confirmation). Ground truth:

| view | camera string | measured sheet mapping | geometry.py contract | verdict |
|------|--------------|------------------------|----------------------|---------|
| front | `0,0,0,90,0,0,0` | u→+X, v(down)→−Z | u→+X, v→−Z | OK |
| top   | `0,0,0,0,0,0,0` | u→+X, v(down)→**−Y** (+Y renders UP) | u→+X, v→**+Y** | **FLIPPED** |
| right | `0,0,0,90,0,90,0` | u→+Y, v→−Z | u→+Y, v→−Z | OK |

Consequence: the spec's `cad_mapping` tells the SCAD generator to map the top
view's downward direction to +Y (depth-back). A feature doodled at the top of
the top-view (back of the part) gets placed at the front → mirrored in depth
vs the user's drawing. Matches user-reported symptom. Also disagrees with
drafting convention (front face is adjacent to the front view, so the top
view's bottom edge is the front face) AND with OpenSCAD's own renderer, so the
evaluator's projection IoU punishes correct placement on the depth axis.

Fix (planned in Phase 4): `top.v_maps_to: "-Y"`, `bottom.v_maps_to: "+Y"`,
re-check left/rear signs (camera conventions: rear u→−X, left u→−Y).
Update `tests/test_core.py::test_view_geometry_has_explicit_cad_coordinate_mapping`.

## Phase 2 — Benchmark expansion (next)
Plan: 10 new parametric cases + generator script (`benchmarks/tools/gen_cases.py`).
- Single source of truth per case: mm parameters → ground-truth SCAD → STL (compiled with the
  Docker OpenSCAD) → derived 4 views (pipeline cameras) → synthetic doodle sheet
  (jittered hand-drawn strokes: front + top/right placed per third-angle, wobble, overshoot).
- Families: flat bracket w/ holes (extrude), gear/round plate w/ bolt circle (circular
  repetition), revolve knob/pawn (rotate_extrude), bent stand (multi_face_union),
  enclosure w/ window (shell+cutout), hex prism (polygon extrude), nameplate w/ slots
  (repetition), hook (thin extrude), grille (many cutouts), wedge (loft).
- All ≤ 256 mm cube (BambuLab X1C).
- Real-STL-download hybrid (Thingiverse/MakerWorld/McMaster) deferred: licensing +
  nondeterministic meshes complicate ground truth; synthetic parametric cases give
  verified SCAD↔STL equivalence. Note for future agent: hybrid cases still welcome.
- Splits: mostly development; a couple held as validation once labels confirmed.

## Phase 3 — Baseline + app runs (in progress)
[x] `benchmarks/run_pipeline.py` recreated (source had been deleted; only .pyc remained).
    Drives POST /api/generate with each case's drawing.png + manifest controls; scores
    against ground-truth mesh (extent ratios, volume ratio, build-envelope fit) plus the
    pipeline's own gates. Modes: assisted (object hint + dimension) / raw.
[x] Pre-fix server: port 8081 (code at b0c4507 + probes only). Post-fix server: 8082.
    Baseline tag `pre-fix` running against 8081; post-fix tag will run against 8082.
    Smoke 007 pre-fix: score 91.4 but projections gate failed (front IoU 0.428); the
    bracket's holes were interpreted into the wrong flange => view/axis interpretation flaw confirmed.

## Phase 4 — Surgical fixes (EXECUTED, commit 8f3af0e + e24076f)
1. **Top-view v-sign** `geometry.py axis_contracts`: `top.v_maps_to:"-Y"`, `bottom:"+Y"`.
   Measured with probes (notch at +Y renders at TOP edge of top view). Matches OpenSCAD
   cameras AND third-angle drafting. Test added.
2. **assign_view_groups** rewritten (evaluation.py):
   - primary = area-weighted score + layout nudges only among LARGE groups (title
     scribbles can no longer steal slots; equal-area stacks assign LOWER to front).
   - slot claims use strongest-claimant (closeness x alignment) instead of arrival order.
   - first-angle handled correctly (top view sits BELOW front).
3. **Cluster calibration**: `_view_groups` dilation softened (kernel //55, iterations 1);
   doodle generator layout guarantees >=150px gaps + drafting alignment (top-over-front
   shares x-centre). All 13 cases detect the declared number of groups (was 8/13).
4. **Features gate**: no longer compares sheet-wide profile count vs one view; uses the
   best registered view's crop-local profile count. Kills the "9 vs 0" phantom failure.
5. **Build-envelope gate**: extents must fit 256 mm BambuLab cube (new mandatory gate
   `build_envelope`) + SCAD prompt now states the cube and the Z=0 build-plate rule.
All 33 unit tests pass.

## Phase 4b — (DONE, commits 0d1abd3 + 05f0a1f + fc45c1e)
6. Feature-position fidelity in evaluator (`_profile_centroids` + `_position_fidelity`):
   each doodle opening must have a rendered opening within 0.16 (greedy 1:1). Calibrated:
   all 13 GT doodle-vs-GT-render pairs score 1.0 where openings exist (2 blind spots fixed:
   render opening detection now uses enclosed-background CC + edge-hierarchy recovery).
7. Through-cutter traversal rule added to SCAD prompt (near-face cylinder cuts nothing —
   root cause of 007/005 hole failures).
8. Supervisor prompt discipline: rambling thought-dump JSON broke the parse and KILLED the
   repair loop (attempt-01 terminal). Brevity rules fixed it (post-fix2: loop survives).
9. ROOT CAUSE of position drift: the SCAD generation call never received the measured
   view geometry — only the spec (features as prose) + images. Model free-handed hole
   positions the evaluator then pinned. Fix: generation_input now carries
   measured_view_geometry (view centres + cad_mapping) + prompt rule to honour it.

## Phase 5 — A/B results so far
pre-fix (b0c4507):        8/13 accepted, mean 91.3
post-fix (0d1abd3):       9/13 accepted, mean 93.0 (+4 fixed: 006/008/010/013; -3 regressed: 001/004/007 —
                          the fidelity gate newly EXPOSES mispositioned holes; generation then
                          repaired into identical failed SCAD because supervisor JSON died (8) and
                          generator never saw measured positions (9))
post-fix2 (05f0a1f, subset 001/004/007): 2/3 (001 96.5, 004 99.7 recovered; 007 still fid=0.33)
v2 (fc45c1e, full): running against 8082 — results below when done.

## Phase 5b — hybrid real-STL cases (DONE: 4 cases)
`benchmarks/tools/gen_hybrid_case.py` — download real STL (sha256+URL recorded, mesh never
edited) -> analytic normalize wrapper (scale to target mm, min-Z at build plate) -> GT STL +
pipeline-camera renders via Docker OpenSCAD -> doodle sheet: silhouette + enclosed openings
extracted with the evaluator's own CV primitives, re-inked jittered-hand style.
Cases: 101_bltouch_bracket (Bondtech CR10s), 102_lcd_knob / 103_y_motor_holder /
104_cable_holder (prusa3d Original-Prusa-i3 @ branch MK3S). All validate; all 3-group detect.
Hybrid sheets exposed the primary-view flaw: FLAT parts have a footprint (top) view far
larger than the thin front profile -> area-based primary picked 'top'. Fix (a9ada0a):
front = layout HUB (only group with BOTH a vertical and a horizontal projection link);
axis-specific tie-breaks follow drafting convention. 33 tests incl. 4 layout scenarios.

## Phase 5c — infra reliability fixes (from run forensics, not guesses)
- supervisor rambling broke JSON parse -> loop died attempt-01 (brevity rules + fallback).
- supervisor timeout (90s multimodal) -> loop break; now deterministic repair directive.
- vLLM ReadTimeout -> whole request 500'd; now bounded retries (CAD_TRANSPORT_RETRIES=2).
- runner captures HTTPError bodies (was bare "HTTP 500").

## Phase 6 — DEFINITIVE RESULTS (tag `final`, HEAD f78ee26 + hybrid-sheet fix)
Synthetic (13, baseline b0c4507): 8/13 -> 12/13 accepted, mean 91.3 -> 95.9.
  Fixed vs baseline: 005 flange (82->100), 006 knob (90->100), 008 enclosure (77->98),
  010 nameplate (77->96), 013 wedge (86->95). All pass all 7 gates incl. build_envelope.
  One case (003 grille) wobbled to F75 in one run -> re-running (tag final2); it passed
  T96-98 in every earlier run => treated as LLM temperature flakiness unless it repeats.
Hybrid real-STL (4 new): 0/4 accepted (mean 82) — the frontier. All compile, watertight,
in envelope; failing gates = features/projections. Evidence path verified sound
(measured openings + cad_mapping reach the generator), supervisor loop engages, repairs
attempted (3 attempts each). Root cause: real parts have non-prismatic topology
(combs, channels, gussets) the spec->SCAD step under-constrains; the doodles demand
5 enclosed openings from views where the model builds flat plates.
=> NEXT WORK (for next agent): hybrid failures are a SPECIFICATION-depth problem, not
coordinates. (Verified done: supervisor diagnosis sees original sheet + candidate
renders, pipeline.py:172-174; repair turn sees candidate renders, :205-207.) Candidates:
(b) add per-view opening-count constraints to the construction_plan preflight — e.g.
"right view demands 5 openings along u=0.32/0.57 rows" must appear as 5 cutters,
(c) accept partial credit & rank candidates by fidelity,
(d) few-shot: one worked comb/channel example in SCAD_PROMPT for non-prismatic bodies.
NOTE v4 was killed mid-run (stale evaluator); v5 superseded by `final` for the same reason.

## Phase 7 — user-feedback features (interactive viewer, sliders, intent refinement)
User feedback (2026-09-18): pipeline duplicated doodle imperfections instead of
inferring intent; static images only; no parametric editing. Three commits:
1. d17c4e6 UI: three.js interactive viewer (auto-rotate until user grabs, free
   orbit, persistent scene — replaceStl NEVER resets camera) + Modify opens a
   LEFT param panel; sliders recompile top-level SCAD params -> edited STL
   (model.scad untouched; GET /api/results/{id}/params, POST .../parametrize).
2. 48f9fa8 params: unit comments as slider labels, commented-out assignments
   rejected, count-before-size unit classification.
3. 59d9a45 refine.py: deterministic intent refinement fed to SCAD generator —
   wobbly circle -> true circle(), near-equal sizes unified, row/col centre
   snaps, grid-pitch loop hint. `refine_mode` control: Smart CAD (default) vs
   Trace as drawn. Calibration: true circle circ=0.906, 5:4 rect 0.771, so
   CIRCLE_MIN_CIRC=0.78 + aspect window. Tests: 40 passed.
final3 (runner dimension fix): 9/16 measured — synthetic regressions vs `final`
(001 TimeoutError transport, 003/010 scale/gate misses, 006 90.8) => LLM
run-to-run variance is real; single runs are noisy, A/B needs repeated runs or
per-case best-of. Hybrid first accept: 103_y_motor_holder 93.0.
A/B protocol: run tag `reg1` (same server, same cases) vs final3 — refinement
is default-on; judge by per-case score delta, not headline count, AND watch
for regressions on cases whose GT is intentionally non-ideal (002 vase!).

### reg1/reg2 A/B + coordinate forensics (Sept 18)
- reg1 (refine layer ON): synthetic 11/13 accepted, mean synthetic 95.6 (vs 85.1
  final3). Zero refine-induced regressions incl. organic 002. Hybrids still hard.
- reg2 forensics found THREE root causes (all fixed + tested, 41 tests):
  1. preflight token bans scanned comments -> '// bounding box (0,0,0)' tripped
     box() ban, false-failed compilable 103 (now compiles; 70 pts).
  2. SCAD_PROMPT top-view prose contradicted its own formula (v=back vs
     Y=(1-v)*depth) -> depth mirroring. Prose fixed + explicit chirality rule.
  3. Supervisor got a vague 'projections poorly match' string -> could not act.
     Failure text now names the weak view + similarity + repair hint.
- Chirality measured three ways (probe solids + GT renders): pipeline right cam
  (azimuth 90) has view-LEFT = FRONT(-Y) = u=0. GT 001 tall panel at Y~0 renders
  view-LEFT; reg2 model built it view-RIGHT => semantic mirror despite correct
  measured outer polygon. New rule: outer polygon is silhouette truth, never
  mirror to satisfy part-name priors; no invented curvature (003 grille case).
- reg3 = re-measure 001/003/101/102/103/104 with fixes 1-3.

### reg3/reg4 (cutter axis + evaluator fairness)
- reg3: 001 ACCEPTED (chirality rule verified); 104 hybrid ACCEPTED first time;
  003 features stuck: headlight cylinders had Z-axis (vertical tunnels), not
  rotated to Y. -> cutter-perpendicularity prompt rule.
- reg4 scores up (101 95.3, 102 96.0) but 0 accepted; TWO evaluator-side bugs:
  1. shape_sanity window .35-1.65 vs noisy LLM size estimates: 101 mesh == GT
     (Y=60mm) yet spec said 30 -> ratio 2.0 -> false fail. Window now .22-2.6
     (catches axis collapse, ignores estimate noise). GT-vs-mesh extent gate
     (dimensions, 5%) remains the real anchor.
  2. refine grid hint only recognized circle grids; 003's seven-slot row got
     no loop hint and hand placement keeps losing edge items -> linear row
     hint for circle/rect/slot rows (regression test added; 42 tests).
- 003 attempts show crop=9, rendered=5-6: model CAN cut 9 (crop proves GT
  demands 9) but loses 2-3 per construction; supervisor failure text now
  counts per view. If reg5 still <9: consider per-openings few-shot in prompt.

## Handoff notes for other agents
- Run everything from the worktree with `PYTHONPATH=$PWD`.
- NEVER restart/kill the vLLM container (port 8000) without user approval.
- OpenSCAD = Docker only here; keep `DOODLE_OPENSCAD_DOCKER` set.
- Generated benchmark artifacts live under each case's `derived/`; `source/` and
  `ground_truth/` are immutable + sha256-pinned (validate.py enforces).

## Next-work pointer (session 2026-09-18 close)
- WIP commit 2d5b919: doodle_to_cad/sizes.py derive_physical_sizes() — deterministic mm from measured ink spans + authoritative max dimension. Validated offline on 103 (recovers 60/40/24-class sizes where the LLM spec said depth 30). NEXT: call in pipeline.generate after label_view_geometry, inject result into generation_input as derived_sizes and into spec.dimensions (overriding LLM estimates), SCAD prompt rule "use derived_sizes mm values", clamp top-level params post-compile when extents miss target by >5%.
- reg6 lesson baked in: evaluator names the exact (u,v) centres of missing openings (d78b3f7).
- Site for user benchmarking: http://127.0.0.1:8082 at 2d5b919, 43 tests green.
