# Interactive benchmark run notes

## 003 — Front grille multiview

- Run result: `results/cafb6d44dac6`
- Model: `vendor-vlm/27b`
- Runtime: 170 seconds
- Outcome: revision needed, best score 72.1/100 (attempt 2)

### What worked

- Image interpretation identified a car grille, a front view and a top view.
- It identified the intended 120 x 60 x 10 mm envelope, two oval headlight cutouts,
  seven central slat cutouts, bilateral symmetry, and a depth taper.
- The supervisor detected the empty first result and requested an OpenSCAD repair.
- Attempts 2 and 3 compiled into a single-component watertight mesh.
- The best mesh passed topology (45/45) and projection gating.

### What failed

1. Attempt 1 generated unsupported `box(...)` calls. OpenSCAD ignored them and the
   top-level object was empty, so no STL was produced.
2. The initial `difference()`/body construction was invalid. It did not establish a
   complete positive solid before subtracting the cutouts.
3. The repair's `depth_taper_solid` intersection collapsed the intended panel into a
   96 x 5 x 5 mm bar with only 16 triangles.
4. The repaired mesh missed the 120 mm target by 20%; dimensions scored 16/20 and
   failed the mandatory dimension gate.
5. None of the required openings survived: the rendered front view had zero internal
   profiles, versus nine required by the drawing. Features scored 0/20 and failed the
   mandatory feature gate.
6. Front-view similarity was only 0.517. Top-view similarity was misleadingly high
   at 0.959 because the degenerate bar resembles the thin source top view.
7. Attempt 3 was identical to attempt 2 (same 72.1 score, 96 x 5 x 5 mm extents and
   missing profiles), so the final retry did not act on the previous repair feedback.
8. The web form visually restored the previous `a book end` note after it had been
   cleared. The saved run spec records an empty user description, so the submitted
   payload was clean, but the visible stale state is still a UI defect.

### Likely repair targets

- Reject unsupported OpenSCAD primitives during preflight, rather than reporting
  preflight success and waiting for compilation to fail.
- Require the base solid's bounding box to overlap the interpreted envelope before
  permitting taper intersections or cutouts.
- Verify every intended through-cut against the compiled mesh after each repair.
- Stop or change strategy when a retry produces identical geometry and scores.
- Make the controlled notes field and visible textarea share one authoritative state.

### Post-improvement rerun

- Run result: `results/bcdb447efbab`
- Model: `local-vlm/private-flash` (different from the original run)
- Runtime: 161.11 seconds
- Outcome: revision needed, best score 61.0/100 (attempt 2)
- All numbered candidates compiled; no compiler-repair subloop was needed.
- Maximum dimensions and the new axis-shape sanity gate passed on every candidate.
- Projection similarity improved substantially (front 0.919, top 0.950).
- The remaining construction error is semantic: the model built the grille openings
  largely as positive frame/slat pieces instead of nine subtractive through-profiles.
- Attempt 1 had nine disconnected components; repair reduced this to three, but the
  strict single-component topology gate still failed.
- The rendered front view exposed zero closed internal profiles, so features remained
  0/20 through all three attempts. Attempts 2 and 3 were identical at 61.0/100.
- This score is not directly comparable to the earlier 72.1/100 because the endpoint
  now serves a different model.

## 002 — Greek vase silhouette

- Run result: `results/40dd8c77d430`
- Model: `vendor-vlm/27b`
- Runtime: 229 seconds
- Outcome: revision needed, 20/100 on all three attempts

### What worked

- The drawing was interpreted as a rotational vase with a narrow base, wide body,
  narrow neck, flared rim, 120 mm height and approximately 85 mm width.
- The supervisor correctly detected that the first two attempts had the same parser
  failure and changed the third action from repair to clean regeneration.
- No subtractive feature was expected, so the feature score remained 20/20.

### What failed

1. Attempts 1 and 2 assigned module invocations to variables
   (`outer_solid = revolve...`), which is invalid OpenSCAD syntax. Both failed at
   line 97 and produced no STL.
2. The first repair reproduced the same source-level error byte-for-behavior; it made
   no measurable progress.
3. The supervisor's repair explanation became confused and self-contradictory about
   the coordinate plane required for a revolved 2D profile. This is overly long and
   gives the repair model an unreliable prescription.
4. Attempt 3 changed strategy but used an unknown `revolve` module. OpenSCAD ignored
   both calls, leaving the top-level object empty.
5. All three attempts passed preflight despite syntax that could be rejected cheaply:
   invalid module assignment in attempts 1/2 and unknown `revolve` in attempt 3.
6. No attempt produced a mesh, dimensions, topology, projections or downloadable STL.
   Every attempt remained at 20/100, with a measured maximum dimension of 0 mm.
7. Runtime reached 229 seconds for three results whose decisive compiler errors were
   immediately available.

### Likely repair targets

- Teach generation and repair to use OpenSCAD's real rotational primitive,
  `rotate_extrude()`, with a 2D radius/height polygon.
- Add parser/unknown-module validation to preflight before expensive evaluation.
- Feed the exact compiler diagnostic back to repair with a short, deterministic rule
  instead of free-form geometric speculation.
- Require a regeneration to differ structurally from the failed program and compile
  before consuming the final attempt.

## 001 — L-bookend multiview

- Active run result: `results/85ec81b4f63a`
- Model: `vendor-vlm/27b`
- Status after 405 seconds: stalled while requesting supervision after attempt 2

### Results available before the stall

- Attempt 1: 71.8/100. It produced a valid, watertight, correctly scaled mesh, but
  missed all four required slots and failed projection matching.
- Attempt 2: 92.4/100. Repair restored all four slots while preserving a watertight,
  one-component 120 x 40 x 120 mm mesh. Topology, dimensions and features all scored
  full marks.
- Attempt 2 still failed projection matching: front similarity 0.583 and right-view
  similarity 0.401, for 7.4/15 projection points.

### Current failure

- The supervisor request after attempt 2 disconnected without returning a response
  (`RemoteProtocolError: Server disconnected without sending a response`).
- The recorded recovery is `retry_without_thinking`, but the web request remained in
  the same compilation/rendering stage beyond 405 seconds with no attempt-3 artifact.
- This run therefore exposes a missing or ineffective timeout around the supervisor
  fallback request. The otherwise strong attempt-2 result is not returned to the UI.

### Post-improvement rerun

- Run result: `results/c219704fd9b1`
- Model: `local-vlm/private-flash`
- Runtime: 40.69 seconds
- Outcome: accepted on attempt 1 at 93.3/100
- No compiler-repair subloop or supervisor repair was needed.
- The mesh is watertight, one component, 100 triangles, and 120 x 60 x 80 mm.
- All four source internal profiles appear in the rendered front view.
- Topology, dimensions, shape sanity and features all passed at full score.
- Silhouette fidelity remains the weak area: front similarity is 0.522 and right-view
  similarity is 0.589, yielding only 8.3/15 projection points despite passing the
  current 0.45 per-view acceptance threshold.
