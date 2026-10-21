# BRep capability demonstrations (issue #82) — trusted-recipe track

Human-authored recipes, no LLM in the loop. Every cell is reproducible:

```
<analysis-python> docs/brep/bench-capabilities/build_capabilities.py \
  --worker-python <worker-venv>/bin/python --output <new-run-directory>
```

The runner validates each recipe with the product's own `validate_recipe`
(verbatim import), builds it through the worker (`workers/brep/build.py`),
then measures the archived STL and the worker diagnostics. The worker's own
verdict outranks the bytes: a build carrying `construction-error.json` or a
non-zero worker exit is FAILED even when an STL was written (the round-trip
guard can abort after export — a guard nobody obeys is decoration).

Edits are PARAMETER-ONLY: identical operation sequence, one parameter value
changed (`ops_identical: true` is recorded). Protected dimensions must not
move; changed dimensions must reach the requested value. Current checks use
0.05 mm for outer bounds and 0.15 mm for tessellated feature measurements.

## Correction to the original edit claims

The original `results.json`, `evidence/`, and demo server remain historical.
Their edit PASS flags did not establish bevel size, wall thickness, or hole
diameter; sweep section/leg and loft bottom-profile protection were incomplete.
Do not use the historical table below as proof of those measurements.

The corrected runner measures sections for chamfer setbacks at two heights,
bend radius and section width/height, leg length, both loft ends, shell side
walls and floor, corner fillets, and both pierced-wall hole diameters. The
45-degree chamfer uses the existing kernel radius convention: setback =
`chamfer_c / sqrt(2)`; the bounding box does not shrink. Measurements are
checked on initial and edited meshes. Tests reject unchanged initial meshes
against every successful edited contract and detect unrelated dimension drift.

Each invocation requires a new output directory and saves recipes, frozen
plan, runner sources, environment, complete stdout/stderr, diagnostics and
incremental results. Existing directories and attempts are refused. Timeouts
are retained. Any failed initial or edit cell gives exit status 1, including
exploratory failures. The known c1 round-trip defect remains a failure.

See [RUNS.md](RUNS.md) for retained development attempts and the selected run.
These remain trusted human-authored demonstrations, not LLM scores or human
acceptance. Analysis dependencies match ../issue-82-capabilities/requirements-analysis.txt.

## Historical matrix (run of 2026-10-20, `results.json` is the machine copy)

| case | capability | initial | parametric edit | note |
|---|---|---|---|---|
| c2_chamfer_block | chamfer, all-edges | **PASS** | **PASS** (c 1.5→3) | 12 bevel facets verified by normal dedup; bbox is NOT a valid chamfer probe — bevel endpoints preserve extents (recorded trap) |
| c3_sweep_handle | curved sweep, tangent legs, rect section | **PASS** | **PASS** (bend_r 30→40; section 8×3 and legs preserved) | volume matches hand calc within 5% |
| c4_loft_transition | loft rect→circle | **PASS** | **PASS** (circ R 30→34; span protected) | |
| c5_shell_tray | open-top shell, protected outer | **PASS** | **PASS** (wall 3→2; outer [100,70,25] unchanged ±0.01) | volume matches analytic cup within 2% |
| c6_combined | fillet + shell + pierced window coexist | **PASS** | **PASS** (win Ø10→16; outer + genus 2 preserved) | two tunnels, one per pierced wall — measured, not assumed |
| c7_chamfer_stress | drill-then-chamfer (exploratory) | **PASS** | — | kernel survived all-edge chamfer over hole rims; genus 2 kept |
| c1_fillet_enclosure | fillet + through-holes | **FAIL — worker's own round-trip guard** | n/a | see defect below |

## c1: genuine defect found by the trusted track

`fillet(outer_vertical r6)` on a drilled plate: the worker computes native
volume **374,721.415 mm³** — matching the closed-form value
384,000 − 2·π·4²·80 − 4·(36 − π·36/4)·40 = **374,721.4** within one part per
million — but its USD round-trip check reloads **390,806.4 mm³** and rejects
the build:

```
USD round-trip volume check failed: original_volume_mm3=374721.415175;
reloaded_volumes_mm3=[390806.37089063344]
```

The difference, **16,084.96 mm³, equals exactly 4× one Ø8×80 hole volume**
(π·4²·80 = 4,021.24; ratio 4.0000003). Injection-probe forensics (#90
comment): the reloaded solid tessellates to a FILLED filleted box
(not watertight, 402 faces) whose kernel volume = filleted slab + BOTH
cutter cylinders — after the USD hop the `difference` behaves like a
`union`. The exported USDA is topologically correct (it contains the two
r=4 hole cones and four r=6 fillet cones): the defect lives in
usd-brep==1.0.0's `import_breps`. Deterministic 4/4
(`probes/probe_roundtrip.py`); the STL side is correct (374,744 mm³
tessellated, genus 2, watertight), and the worker's guard correctly refuses
to bless the USD. (An earlier revision of this file described the delta as
"the two through-holes / holes fill" — wrong arithmetic; corrected per the
forensics.)

## Authoring effort (trusted path cost, per the issue's ask)

Cases were authored in one pass against the version-2 contract
(`construction_recipe.validate_v2`): every case passed the worker on the
first authoring attempt once the contract was followed (op field sets are
exact; `depends_on` must equal the op's left/right/body references —
`tool` is not a field, `difference` is `left`/`right`). Operation/parameter
counts per case are in `results.json → author_effort`.

## Honest limitations

- Chamfer applies to ALL edges (`build.py` `chamfer_fillet`); hole-inlet
  chamfer is not expressible today.
- Sweep supports one bend with optional straight ends (contract), not
  multiple bends.
- "Native vs export measured separately" is published per cell:
  `diagnostics.solid_volume_mm3` (native) vs `measure.mesh_volume_mm3`
  (tessellated STL). c1 is the case where the two DISAGREE with each
  other across the USD hop — which is exactly why both are recorded.
