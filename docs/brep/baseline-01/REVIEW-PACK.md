# Task 01 baseline — user review pack

Issue: [#18](https://github.com/nedraki/doodle-to-cad/issues/18) — last open gate:
"Attach the product demonstration and record user review".
Prepared: 18 October 2026. Prepared by: Hermes review-pack agent, on request of the
project engineer. Owner review target: **10 minutes**.
Evidence folder: [README.md](README.md) (this directory). Re-verification run:
[reverify-2026-10/](reverify-2026-10/). Integrity: [SHA256SUMS](SHA256SUMS).

## 1. What the baseline recorded, in plain language

The baseline froze a starting point for BRep work before generation tasks begin:

- **Reference contracts.** Five drawings (bookend, wheel, enclosure, curved handle,
  transition) each with a machine-readable manifest of expected dimensions, features,
  relations, and fixed tolerances. These are the acceptance yardstick for future
  generation work. Four of the five are synthetic engineering diagrams, agreed to be
  test fixtures, not user doodles.
- **Green checks.** Three BRep recipe builds plus parameter edits (solid, mesh, and
  USD round-trip checks), their OpenSCAD equivalents, and the five reference solids
  all passed dimension, watertightness, and connectedness checks.
- **One retained failure, kept on purpose.** One real end-to-end run through the
  browser — the OpenSCAD bookend doodle — produced a candidate that scored **92.1**
  (above the acceptance threshold of 70) but **failed a mandatory drawing-fidelity
  gate**: the front view shows 3 openings where the drawing demands 4. The supervisor
  rejected it and all three attempts were preserved untouched
  ([generation/](generation/)).

**Why a baseline may contain failures.** A baseline records what the system does
today, not what it promises tomorrow. The rejected run is the single most useful
artifact here: it proves the supervisor's mandatory gates do catch a high-scoring
but wrong part (a score of 92.1 did not buy acceptance), and it fixes a concrete
known-defect to measure future generation tasks against. Deleting it would hide the
exact evidence the owner is asked to accept. Nothing in this pack was filtered,
retouched, or re-run to look better; raw files keep their original bytes.

## 2. The five reference contracts

Tolerances are fixed for all five cases and must not be changed to pass a candidate:
reference dimension ±0.05 mm absolute; generated dimension ±2% relative; feature
position ±1.0 mm; feature size ±1.0 mm; wall thickness ±0.5 mm; feature-count error
0; connection gap 0.0 mm. Every contract expects exactly **1 connected component,
watertight**.

| Case | Expected extents (mm) | Key features / relations | Contract files |
|---|---|---|---|
| Bookend | 80 × 50 × 100; wall 3 | Base + panel one solid; **4 cutouts** through the panel along Y (boxes `cut1..cut4` in XZ) | [manifest](../../../benchmarks/brep-baseline/bookend/manifest.json) · [drawing](../../../benchmarks/brep-baseline/bookend/drawing.png) · [reference.scad](../../../benchmarks/brep-baseline/bookend/reference.scad) |
| Wheel | Ø120 disc, 8 thick (120 × 8 × 120); rim inner Ø108, hub Ø32, spoke width 8 | 8 spokes each overlapping hub **and** rim; one solid; **no axle bore** in contract | [manifest](../../../benchmarks/brep-baseline/wheel/manifest.json) · [drawing](../../../benchmarks/brep-baseline/wheel/drawing.png) · [reference.scad](../../../benchmarks/brep-baseline/wheel/reference.scad) |
| Enclosure | 120 × 80 × 40; wall 3, floor 3 | Walls + floor one solid; **top open**; front window opens into cavity | [manifest](../../../benchmarks/brep-baseline/enclosure/manifest.json) · [drawing](../../../benchmarks/brep-baseline/enclosure/drawing.png) · [reference.scad](../../../benchmarks/brep-baseline/enclosure/reference.scad) |
| Curved handle | 48 × 54 × 8; section Ø8; bend centerline radius 20; legs 30 | Two straight legs + bend one solid; constant circular section; ends capped | [manifest](../../../benchmarks/brep-baseline/curved_handle/manifest.json) · [drawing](../../../benchmarks/brep-baseline/curved_handle/drawing.png) · [reference.scad](../../../benchmarks/brep-baseline/curved_handle/reference.scad) |
| Transition | 60 × 40 × 60; bottom rectangle 60 × 40; top circle Ø30; height 60 | Both profiles share the Z axis; solid and capped; **intermediate surface deliberately unspecified** (reference uses a convex hull — do not score lofts against it) | [manifest](../../../benchmarks/brep-baseline/transition/manifest.json) · [drawing](../../../benchmarks/brep-baseline/transition/drawing.png) · [reference.scad](../../../benchmarks/brep-baseline/transition/reference.scad) |

Deliberate contract caveats (also in [benchmarks/brep-baseline/README.md](../../../benchmarks/brep-baseline/README.md)):
the wheel is a proposed eight-spoke test case, **not** a repair of the user's failed
wheel screenshot; unknowns (material, manufacturing, projection standard for the
synthetic cases) stay unknown and must not be inferred from the reference model.

## 3. The retained failure you are being asked to bless

One live browser run, no mocks: `docs/demo/kit_sketch.png` uploaded, notes
"L-shaped bookend", target 100 mm, model
`local-inference-lab/Qwen3.8-Flash-Next-NVFP4`, three attempts in 186.9 s
(job `498951c1ba2b`, see [generation/result.json](generation/result.json)).

| Attempt | Score | Mandatory gates failed |
|---|---:|---|
| 1 | 72.4 | features, projections (front similarity 0.35) |
| 2 | 82.4 | features, projections |
| 3 (selected) | **92.1** | **features** |

Attempt-3 evidence — [attempt-03/evaluation.json](generation/attempt-03/evaluation.json):

- `score: 92.1`, `accepted: false`, `mandatory_gates.features: false` (all other
  gates true; scores: topology 45/45, dimensions 20/20, features 15.0, projections 12.1).
- `profile_topology.front`: source demands **4** internal openings; rendered shows **3**.
  Missing opening centroid `(u=0.259, v=0.14)` — the lower-left cutout was never cut.
  Feature-position fidelity 0.75.
- Failure text: *"required internal profiles are missing: front view demands 4,
  best rendered view has 3 … add cutters there: (u=0.259,v=0.14)."*
- Mesh itself is healthy: watertight, 1 component, 132 triangles,
  extents 73.05 × 47.99 × 100 mm, volume 78316.3 mm³.

**Why rejection was correct.** Acceptance is gate-first: the numeric score (92.1 ≥
threshold 70) can never override a failed mandatory feature gate. The part as built
is not the drawn part — a missing through-cutout is a functional defect, not a
cosmetic one. Recording it (rather than re-rolling until a pass) is what makes the
baseline honest, and it demonstrates the supervisor enforces the bookend contract's
`count_error: 0` tolerance on openings.

Side-by-side: input [openscad-input.png](openscad-input.png) vs rejected result
[openscad-generated.png](openscad-generated.png); rendered front
[generation/attempt-03/view-front.png](generation/attempt-03/view-front.png) —
compare with the 4 openings in
[bookend drawing.png](../../../benchmarks/brep-baseline/bookend/drawing.png).
No failed attempt was removed; the directory also keeps raw model outputs,
supervisor transcripts, and repair logs.

## 4. Review in 10 minutes

| # | Min | Look at | What you are deciding |
|---|---:|---|---|
| 1 | 2 | This pack + [README.md](README.md) result table | The summary matches what you expect task 01 to be |
| 2 | 3 | §3 + [openscad-input.png](openscad-input.png), [openscad-generated.png](openscad-generated.png), [attempt-03/view-front.png](generation/attempt-03/view-front.png) | The 3-vs-4 opening failure is real, and rejecting it was right |
| 3 | 3 | The five drawings + manifests in §2 | The contracts, dimensions, and tolerances are fair and fixed (especially: wheel has no axle bore; transition intermediate surface is unscored) |
| 4 | 1 | [reverify-2026-10/reverify-geometry.log](reverify-2026-10/reverify-geometry.log) and [reverify-tests.txt](reverify-2026-10/reverify-tests.txt) | Today's re-run is green (5/5 contracts, 211 tests) |
| 5 | 1 | In the repo root: `cd docs/brep/baseline-01 && sha256sum -c SHA256SUMS` | Evidence integrity (expect all `OK`) |

**What "approve" means.** Your approval records the review on the last open checkbox
of issue #18 ("Attach the product demonstration and record user review"), closes
task 01's gate, and unblocks task 02 (direct drawing-to-BRep generation work per
issue #15 open items). It means: the baseline as recorded — including the kept
failure and the five fixed contracts — is the accepted starting point. It does
**not** mean the current generator is approved for release, and it does not merge
or close anything by itself: the parent engineer merges the review-pack PR and
records the gate on #18.

**To approve, reply with exactly:**

> I have reviewed the task 01 baseline evidence and the user review pack on branch
> hermes/brep-01-reviewpack, including the retained OpenSCAD bookend failure
> (92.1, rejected for 3 openings instead of 4) and the five fixed reference
> contracts. I approve the baseline. Record user review on issue #18 and unblock
> task 02.

If something must change, reply instead:

> I do not approve the task 01 baseline yet. Required changes: <list>. Keep #18 open
> pending a revised pack.

## 5. Fresh re-verification on current brep-integration (2026-10-18)

Run today by the review-pack agent against `brep-integration@01de9ddc2afc7a577bec2902940c4884932169ca`
in a fresh worktree. Full logs in [reverify-2026-10/](reverify-2026-10/):
[reverify-geometry.log](reverify-geometry.log),
[reverify-report.json](reverify-2026-10/reverify-report.json),
[reference-checks.json](reverify-2026-10/reference-checks.json),
[recipe-checks.json](reverify-2026-10/recipe-checks.json),
[environment.json](reverify-2026-10/environment.json),
[reverify-tests.txt](reverify-2026-10/reverify-tests.txt).
Runner: [scripts/reverify_baseline_2026_10.py](../../../scripts/reverify_baseline_2026_10.py)
(same checks as `scripts/check_baseline_geometry.py`, outputs redirected so frozen
evidence bytes are untouched).

Environment: worker venv `workers/brep/.venv` (Python 3.12.3; usd-brep 1.0.0,
trimesh 5.1.1, numpy 2.5.4) via `DOODLE_BREP_PYTHON`; OpenSCAD via docker
`openscad/openscad:latest`; no server was started (`DOODLE_PORT=8118` reserved;
inference port 8000 untouched).

Five reference solids (source-hash verified, dimensions within the fixed ±0.05 mm
tolerance, watertight, 1 component):

| Contract | Dimensions | Mesh | Result |
|---|---|---|---|
| bookend | 80.0 × 50.0 × 100.0 mm | watertight, 1 comp | **pass** |
| wheel | 120.0 × 8.0 × 120.0 mm | watertight, 1 comp | **pass** |
| enclosure | 120.0 × 80.0 × 40.0 mm | watertight, 1 comp | **pass** |
| curved_handle | 48.0 × 54.0 × 8.0 mm | watertight, 1 comp | **pass** |
| transition | 60.0 × 40.0 × 60.0 mm | watertight, 1 comp | **pass** |

Supporting BRep recipes (build + parameter edit, watertight + USD round-trip) and
their OpenSCAD equivalents: bracket, enclosure, curved_pipe — **3/3 pass**.

Regression suite: `.venv/bin/pytest -q` → **211 passed, 0 skipped** (2 deprecation
warnings), kernel-active, exit 0.

**Not re-run today, stated plainly:** the live browser generation (three OpenSCAD
attempts via `scripts/check_baseline_product.py`) was **not** repeated — it makes a
real model call whose output would differ and would overwrite frozen evidence.
The 2026-10-13 `generation/` artifacts and `product-checks.json` stand as recorded;
their bytes are pinned in [SHA256SUMS](SHA256SUMS). The geometry script still does
not measure every manifest feature position or wall thickness (unchanged limitation,
see README "Reproduce").

## 6. Integrity

[SHA256SUMS](SHA256SUMS) covers every file in this folder (baseline evidence,
product-demo images, generation attempts, and this pack) except SHA256SUMS itself.
Verify from the repository root:

```sh
cd docs/brep/baseline-01 && sha256sum -c SHA256SUMS
```

Any `FAILED` or missing entry means the evidence was altered after packaging — stop
and re-request the pack.

---
*Status: pack complete; **awaiting owner review**. Issue #18 remains open; nothing
here closes or merges it.*
