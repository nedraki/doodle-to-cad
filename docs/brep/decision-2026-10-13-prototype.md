# Decision: keep BRep optional; defer default adoption

Evaluation performed 13 October 2026 for issue #15, on Linux ARM64 with
CPython 3.12.3 and `usd-brep==1.0.0`. Application tests use Python 3.11.

The prototype supports finer edits when the saved recipe exposes those details.
It does not recover arbitrary features from an STL. Fillets and curved sweeps
require fewer application-level geometry constructions than their OpenSCAD
counterparts. This limited run does not establish higher general reliability.

## Deterministic geometry and editing

Three explicit recipes and equivalent OpenSCAD references were built. Timings
include fresh worker startup, STL verification, and USD export/reimport for BRep;
OpenSCAD timings include STL compilation only. These are single measurements,
not a controlled throughput comparison. See [raw results](evaluation.json) and
[`scripts/evaluate_brep.py`](../../scripts/evaluate_brep.py).

| Case | BRep build | BRep edit | OpenSCAD build | Result |
|---|---:|---:|---:|---|
| Four-hole bracket | 0.295 s | 0.301 s | 0.708 s | 60 × 40 × 80 mm; 31,500 mm³; genus 4 |
| Filleted enclosure | 0.327 s | 0.340 s | 0.923 s | 60 × 40 × 25 mm; valid rounded outer corners and open pocket |
| Curved swept solid | 0.351 s | 0.315 s | 0.496 s | 23 × 23 × 6 mm; valid capped circular sweep |

All three baseline and edited BRep models pass kernel manifold checks,
independent watertightness, winding, connectedness, positive volume, build-volume
limits, a ≤2% solid/mesh volume difference, STL reload, and USD volume round-trip.
All three OpenSCAD references are watertight single components with matching
extents. The bracket volume is identical; curved mesh volumes vary with the
backends' different tessellation settings.

Edits tested: move/enlarge hole 1; increase enclosure wall thickness and outer
corner radius; increase sweep bend radius and tube radius. Four-hole topology
survives the bracket edit. Independent wall sections confirm all four baseline
openings' positions and dimensions. An oversized fillet fails without overwriting
prior artifacts; a timeout test also confirms that no partial revision is published.

The browser test verifies 20 bracket controls, a hole-width rebuild, matching
recipe/STL/USD revision downloads, invalid input rejection, and reset.

## Existing generated part

One existing accepted bookend was translated by the configured local model
(`local-inference-lab/Qwen3.8-Flash-Next-NVFP4`). It produced 20 parameters, including
separate opening coordinates and sizes. Overall dimensions and genus 4 were
preserved. Mesh volume differed by approximately 0.0025%; independent XZ sections
at Y=5 mm found five loops (outer boundary plus four holes), with maximum boundary
difference below 0.005 mm. Enlarging one opening by 2 mm rebuilt successfully and
preserved genus 4. See [measurement/provenance](translation-trial.json) and the
[saved generated recipe](generated-bookend.recipe.json).

This is **one reconstruction trial**, not repeated drawing-to-CAD evaluation.
The prototype deliberately labels model-generated BRep candidates as unverified
against the drawing. The original supervisor score is not transferred.

## USD packaging and compatibility

The wheel includes OpenUSD runtime libraries and schema resources, but does not
include the Python `pxr` namespace. Its USD script loader attempts imports such
as `pxr.Ar` and emits warnings. These warnings reproduce during export/import;
they remain in each revision's `worker.log`. The geometry round-trip passes despite
them. No additional `usd-core` was installed and warnings were not suppressed.
This is contained, not fixed upstream.

USDA output explicitly declares `metersPerUnit = 0.001` and `upAxis = "Z"`.
The named round-trip target tested is **usd-brep 1.0.0 itself**. Its custom
`BrepArray` schema requires a compatible consumer. No external DCC/CAD application
has been validated; the STL is the ordinary mesh interchange artifact. No STEP
support is claimed. See upstream [packaging notes](https://github.com/NVIDIA-Omniverse/usd-brep/blob/c9c5979f04cea8c38213004d4f04df0dcfb40d05/tools/pyproject/README.md).

## Remaining adoption work

- Repeated drawing-to-CAD trials across the benchmark corpus, including failed
  reconstructions and automatic projection/feature-position scoring.
- A richer executable construction-plan schema for arbitrary profiles, general
  sweeps, shelling, and dependency-aware constraints. The existing descriptive
  construction plan is not executable and is never fed directly to the kernel.
- Clickable faces/edges and robust geometric selection beyond all/axis-parallel
  edges, with parameter-to-feature highlights.
- A selected external USD application's schema/unit/axis compatibility test.
- Packaging for supported desktop platforms, warning resolution, and workload
  limits for multiple simultaneous worker processes.

**Decision:** retain this as an opt-in detail-editing prototype. Defer replacing
OpenSCAD and defer closing the full evaluation checklist until the broader trials
and external compatibility evidence exist.
