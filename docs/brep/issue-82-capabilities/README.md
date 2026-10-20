# BRep construction and edit demonstrations — issue #82

This is the **independent, manually authored track** of [#82](https://github.com/nedraki/doodle-to-cad/issues/82), based on `brep-integration` at `a59a476`. It does not close #82. No model calls were made, no product operations or defaults changed, and no files owned by #79 / PR #84 were edited.

[Open the visual review document](evidence/run-005/review.html), or browse the paired PNGs below. The document links every source, STL, native USD, observation, and edit record. Download the directory or serve the repository locally to view the HTML; GitHub's HTML source view does not render it.

**All geometric observations are provisional pending #81. User acceptance is uncollected.** A successful build or an observation within tolerance is not a claim of complete shape correctness or usefulness. The recipes are authored and code-reviewed here; they have not been accepted by the user. The later model-generated track depends on reliable records and review tooling from #79/#80.

## Capability matrix

“Demonstrated” below means the operation built through the current worker and the saved revision lifecycle completed. It does not mean independent geometry validation or human acceptance.

| Family | Supported manual construction and defined edit | Protected measurements | Evidence |
|---|---|---|---|
| Fillet | Outer vertical block edges, radius 3 → 5 → 6 mm; central through hole | 60×40×20 outside bounds; 8 mm hole | [before/after](evidence/run-005/fillet/review.png) · [sections](evidence/run-005/fillet/sections.png) |
| Chamfer | Global operation on a 50×40×20 block, radius argument 3 → 5 → 4 mm | Outside bounds; measured edge placement | [before/after](evidence/run-005/chamfer/review.png) · [sections](evidence/run-005/chamfer/sections.png) |
| Circular bend | Capped half arc, centreline radius 20 → 25 → 23 mm | Circular section diameter 8 mm | [before/after](evidence/run-005/arc/review.png) · [sections](evidence/run-005/arc/sections.png) |
| Straight-ended curved sweep | Rectangular 6×8 section, two 15 mm tangent ends, bend radius 20 → 25 → 23 mm | Section, straight-end lengths, minimum X/Y; end positions reported | [before/after](evidence/run-005/sweep/review.png) · [sections](evidence/run-005/sweep/sections.png) |
| Loft | Solid rectangle-to-circle transition; rectangle width 40 → 48 → 44 mm | Rectangle depth 30, top diameter 30, separation 50 mm | [before/after](evidence/run-005/loft/review.png) · [intermediate sections](evidence/run-005/loft/sections.png) |
| Shell | Open rounded 80×60×30 tray, outside radius 8; thickness 3 → 4 → 5 mm | Outside bounds and corner radius; cavity and floor measured | [before/after](evidence/run-005/shell/review.png) · [sections](evidence/run-005/shell/sections.png) |
| Combined features | Outer radius 6 + through hole + global chamfer, argument 1 → 2 → 1.5 mm | Outside bounds, corner radius, 10 mm hole core; mouth diameter reported separately | [before/after](evidence/run-005/combined/review.png) · [intersections](evidence/run-005/combined/sections.png) |
| Selected pocket | Production `box_cutout` target; first depth 3 → 5 → 6 mm | Neighbouring depths 2/5 mm; 60×40×20 outside bounds | [before/after](evidence/run-005/pocket/review.png) · [sections](evidence/run-005/pocket/sections.png) |

The circular bend is explicitly **arc-only**, not a substitute for a circular handle with straight ends. The separate rectangular sweep demonstrates the supported straight-ended path. General circular-section paths with tangent legs, arbitrary bracket-junction fillets, and individually selected hole chamfers are **not implemented by the current bounded product interface**. Suggested separate capability issues: selectable concave-junction fillets; selective hole-entrance chamfers; circular-section tangent-path sweeps. No general CAD operations are added here.

The combined fixture is a **global chamfer combination probe**, not selective hole editing. Its exported sections show changes at both the exterior and opening entrance while the mid-height hole core remains protected. Other operation orderings and intersections remain untested. In this kernel, the chamfer argument is the hypotenuse: measured setback ≈ argument / √2 and angle ≈ 45°. Inspect the intersections rather than assuming this from the operation's name.

## Construction effort and OpenSCAD comparison

The frozen [plan](evidence/run-005/plan.json) lists the exact manual modeling actions for each BRep recipe. These are authoring-step counts, not source-line counts or measured human working time. Parameter edits change one named value; the pocket edit uses one selected-target depth request. No manual geometry correction is applied between the initial and edited states.

| Case | BRep manual actions | OpenSCAD manual construction / effort |
|---|---:|---|
| Fillet | 4 | Define rounded 2D footprint with `offset`, extrude, subtract cylinder (3 construction actions) |
| Chamfer | 2 | Compute setback, define two inset boxes, hull them (4 actions) |
| Arc | 1 | Define circle section, translate to centreline radius, partial `rotate_extrude`, place at Z=0 (4 actions) |
| Sweep | 3 | Define annular half-ring, define two straight rectangles, union, extrude (4 actions) |
| Loft | 3 | Sample end profiles, define vertex correspondence, build side/cap faces, emit polyhedron (4 actions) |
| Shell | 3 | Define outer rounded profile, define inset cavity profile, extrude both, subtract with floor offset (4 actions) |
| Combined | 5 | Not attempted in this pack; this is not a claim that OpenSCAD cannot express it |
| Pocket | 5 including selection | Define box and three cutters, subtract (5 actions); edit one depth variable |

Both initial and edited OpenSCAD sources and outputs are retained for seven families. They compile through the existing product OpenSCAD boundary, using the installed container image. `$fn=96` is recorded. The loft comparator is a **polar-correspondence polyhedron approximation**, not the same native loft surface: endpoints alone do not establish equal intermediate sections or surface quality. No backend ranking or “BRep wins” claim is made. These sources show that construction control is possible in both workflows, with different explicit authoring work.

## Editing, selection and failure recovery

The runner calls production `revisions.preview`, `targeted_preview`, `keep`, and `feature_selection.choose` directly. Its build adapter uses production `build_brep` with rendering disabled; this is a backend/state-machine demonstration, **not a browser interaction test**. Offline views are rendered from the archived STL with the same camera and scale.

For each case: initial build → edit preview → verify original remains selected → keep → rejected edit → verify saved revision and source/STL/USD bytes unchanged → another edit → keep. The shell rejection requests 30 mm thickness within its declared numeric range, reaching the worker's cavity-preservation guard. Other negative edits are rejected during validation/planning. Logs distinguish those stages.

Selection uses the first pocket's geometric rule or, where supported, the bottom planar face. Arc and sweep have no matching saved bottom-face target in this pack: their status remains `none`, never silently redirected. A persistent face rule is not proof that every feature remains selectable. Explicit lost/split-target integration demonstrations remain a follow-up; existing product tests cover those behaviors.

Requested changes use 0.15 mm provisional mesh tolerance (angle 0.8°); protected scalar geometry uses 0.05 mm. These tolerances are declared before comparison and are not #81-approved. New tests reject an unchanged model presented as the edited model, and a widened block presented as preserving its outside width.

## Native versus export observations

Every successful BRep attempt archives the native USD and STL separately. The native probe reimports the USD in the isolated Python 3.12 worker and records native volume, face count, integrated surface area, and five XY sections sampled at 257 points per curve. Where possible it fits a sampled corner radius; that is **not exact analytic surface-radius verification**. The rounded-shell native corner fit is explicitly unavailable when its returned section curves do not provide enough lower-left samples; the sampled curves and other native measurements remain published.

STL observations use triangle-plane intersections and independent vertical triangle hits. They record extents, feature dimensions, five XY sections, an XZ centre section, volume, triangle count, watertightness and components. Native and mesh volumes are separately recorded with relative difference. Native bounding boxes can contain small kernel padding; do not treat that as a changed nominal dimension.

Production tessellation uses chord-height tolerance **0.05 mm**, plus **2 mm maximum edge length for lofts**. Triangles remain visible in the offline renders. Smooth native surfaces do not guarantee a fine export. The section close-ups and native samples support visual inspection, not a surface-quality certification.

## All attempts and known harness failures

[RUNS.json](RUNS.json) names the selected run and every superseded run, reason and replacement. Nothing was deleted or rerun in place. Each run has its own pre-build frozen plan and pending user-review record.

- `run-001`: missing SciPy stopped mesh section analysis. An early harness bug mislabeled successful exports as failed builds on measurement exceptions; archived STL hashes and worker diagnostics establish what happened. No claims use those booleans.
- `run-002`: retained NumPy boolean serialization failures and analysis-interpreter contamination of the native probe.
- `run-003`: mesh edit lifecycles completed; native curve sampling used an unavailable method.
- `run-004`: native probes worked, but an optional rounded-shell corner fit incorrectly aborted that lifecycle.
- `run-005`: selected evidence, with optional native-fit unavailability reported rather than treated as a build failure.

Historical mistakes are disclosed, not rewritten. Runtime failures and successful geometry remain distinguishable from harness failures in the logs and run ledger. The frozen sources are the authority for each run; later harness fixes do not rewrite prior evidence.

## Reproduce and verify

Use a **separate analysis virtual environment** containing this project's dependencies plus `requirements-analysis.txt`; do not install analysis packages into the native worker. The native worker requires the existing pinned Python 3.12 / usd-brep 1.0.0 installation.

```bash
# Install project + analysis dependencies in a separate environment.
uv venv /tmp/brep82-analysis --python 3.11
uv pip install --python /tmp/brep82-analysis/bin/python -e '.[dev]' \
  -r docs/brep/issue-82-capabilities/requirements-analysis.txt

# Read-only verification of the committed pack; no model/server/network calls.
/tmp/brep82-analysis/bin/python docs/brep/issue-82-capabilities/audit.py
/tmp/brep82-analysis/bin/python -m pytest -q tests/test_brep_capability_evidence.py

# New collection: choose a new directory. Existing output directories are rejected.
DOODLE_BREP_PYTHON=$PWD/workers/brep/.venv/bin/python \
DOODLE_OPENSCAD_DOCKER=openscad/openscad:latest \
  /tmp/brep82-analysis/bin/python docs/brep/issue-82-capabilities/run.py --out /tmp/brep82-new-run
/tmp/brep82-analysis/bin/python docs/brep/issue-82-capabilities/render.py /tmp/brep82-new-run
```

The committed manifest seals every evidence file and source in this pack. The read-only audit checks missing/extra/changed files, case and attempt coverage, summary agreement, frozen recipe edits, recomputed mesh observations, preservation and lifecycle records. `audit.py --seal` is a deliberate author action after reviewing changes, not an automatic repair or a validation command. User review decisions require a later explicit update; the current records remain pending.

## Handoff to #80 / #81 and the generated track

#80 can consume the relative artifact links, input contracts, hashes and pending `review.json` records. #81 must validate these observation methods before their booleans become correctness gates. Compare native and STL sections, calibrate tolerances, validate corner fits, test lost/split target behavior, and assess surface/intersection quality with the user.

Only then run drawings/notes for the same intended designs through the current local model. Keep those attempts separate from this manual track and retain every result. #82 remains open until that generated track and the user's visual/usefulness review are complete. This pack does not authorize model comparison, release, a default change, or closure of #82.
