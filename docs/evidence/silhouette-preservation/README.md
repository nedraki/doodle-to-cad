# Outer-silhouette preservation — evidence

Defect (verified): the grille front outline (11 vertices incl. shoulders) was
classified `circle` at 0.879 confidence because intent refinement measured
aspect/circularity after independent per-axis normalization (measured aspect
1.010 vs true paper aspect 1.609), the SCAD prompt let refinements override
the measured polygon, and the projections gate accepted max(IoU, edge-sim)
>= 0.45 — no dedicated boundary check.

Fix (4 layers):
1. geometry.py — outer profile now carries `polygon_dense_view_normalized`
   (eps 0.004) plus `curve_segments` (line/arc split with per-segment
   max_error). Front outline: 14 segments (12 lines, 2 arcs), fit_error 0.0125.
2. refine.py — classification measures paper aspect
   (`pixel_aspect_ratio_width_over_height`) and every primitive candidate must
   pass a fitted-primitive IoU >= 0.85. Outer fit record:
   {candidate: polygon, accepted: false} on this fixture (was circle 0.879).
3. pipeline.py — SCAD prompt: OUTER SILHOUETTE IS A HARD CONSTRAINT; refinements
   govern internal profiles only; polygon()+linear_extrude() from the measured
   outline; fillets never substitute for the shape.
4. evaluation.py — mandatory `silhouette` gate: per registered view,
   min(drawn-area coverage, CAD-area inside drawing) >= 0.93 at 3px tolerance.
   Calibrated probes: faithful 0.994, bbox rect 0.889 (fail), saved
   rounded-rect render 0.876 (fail), GT flat-plate render 0.893 (fail by
   design — the ink is the truth).

Live run (results/silhouette-e2e-02, model local-inference-lab/Qwen3.8-Flash-Next-NVFP4):
attempt-01 builds polygon(points=front_poly_cad)+linear_extrude — silhouette
fidelity 1.0 front/top, `silhouette` gate true. Attempt 3 (fidelity 0.241) was
ranked below attempts 1-2 by the gate-aware candidate rank. Remaining failures
(internal cutouts 5/9, feature positions) are a pre-existing separate defect
class, not the outer boundary.

Triptych: drawn outline | OLD rounded-rect plate (0.876, rejected) | NEW
generated body reproducing narrow top + diagonal shoulders (1.0).

## Internal geometry pass (silhouette-e2e-05, attempt 3)

After the silhouette fix, the internal elements failed for three reasons:
1. Seven louvre slits (paper aspect ~9-10) matched no primitive regime, stayed
   low-confidence polygons, and the generator dropped 4 of 9 openings.
   Fix: slit/bar classifier regime (SLOT_BAR_* in refine.py).
2. Global row-snap tolerance (0.213, inflated by tall slots) merged the slit
   row (v=0.437) with the headlight row (v=0.625, gap 0.188).
   Fix: pairwise _axis_groups tolerance.
3. The generator kept flipping the front-view v-axis (mirrored shoulders,
   headlights at the top). Fix: Pipeline.feature_placements_mm pre-converts
   every measured centre/polygon to CAD-world mm with the (1-v) flip applied;
   prompt instructs to use it verbatim.

Result (attempt 3): all gates true, silhouette 1.0/1.0, 9/9 front openings,
feature_position_fidelity 1.0, score 99.0. Rendered centroids match source to
<=0.005 normalized. model.scad builds the body from feature_placements_mm
contour_0 verbatim and cuts 7 stadium slots via a for-loop (slot_count=7,
pitch 7.55) plus 2 headlight cylinders (d=19.69) at z=28.4 = (1-0.621)*75.
Files: final-front-render.png, final-model.scad, e2e-run-pass.log,
triptych-final.png. Full suite: 132 passed.
