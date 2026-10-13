# Task 03: Executable construction recipes

Issue: [#20](https://github.com/nedraki/doodle-to-cad/issues/20).
Branch: `codex/brep-03-construction-recipe`. PR base: `brep-integration`.
Task 02 was merged at `48a293585ed74d1f156cce7d654248f538f7bc60`.
Do not merge this work into `main`.

## Version 2 contract

Version 2 extends the existing JSON recipe. It keeps the same bounded arithmetic,
parameters, and operation subset. It does not execute generated Python.

- `version`: 2. `units`: `mm`.
- `frames`: one canonical `world` frame. Origin is `[0,0,0]`. X is width, Y is depth,
  and Z is height. Other frames and transforms are not supported in this task.
- `parameters`: named finite values, bounds, and existing editor metadata.
- `operations`: ordered features. Each has a stable `id`, native operation fields,
  `frame`, `depends_on`, and an `evidence` list.
- `depends_on`: must match the operation's body references. Dependencies must
  appear earlier. Unknown references, forward references, and cycles are rejected.
- `bodies`: one named body whose output matches the recipe's `output` feature.
  This remains a single-part backend. It does not build assemblies.
- `evidence`: separate `observed`, `inferred`, `assumptions`, and `unresolved` lists.
  Each entry has a unique `id` and bounded `text`. Features can refer to these IDs.
  Any unresolved entry blocks a build. Evidence is recorded; its truth is not proved.
- `constraints`: bounded `connected` checks. Each names two constructed features
  and a positive `min_volume_mm3` overlap threshold. Both must be used by the output.

The worker checks actual intersection volume between each pair. It then intersects
that overlap with the final solid. This detects a connection removed by a later cut.
The final mesh must still pass the existing single-component and watertight checks.
Touching faces alone do not satisfy a positive-volume connection.

The descriptive `design_plan.py` output is not an executable recipe. A later task
will produce this bounded recipe from interpreted intent. No automatic conversion
from an unrestricted descriptive plan is added here.

## Fixtures and results

`benchmarks/brep-v2/bookend.json` builds the four-hole bookend.
`benchmarks/brep-v2/wheel.json` builds a four-spoke wheel with explicit connections.
These are hand-authored fixtures. They are not drawing-generation results.

A spoke starts at `hub_radius - 2`. Its length is
`radius - rim - hub_radius + 4`. Thus its endpoint follows the rim when the radius
changes. The 2 mm overlap is an explicit assumption recorded in the recipe.

The wheel builds at radius 60 mm and at radius 80 mm. Its diameter changes from
120 to 160 mm. All eight hub/spoke and rim/spoke checks pass at both sizes.
A deliberately short spoke fails with `east_rim: required connection failed`,
even though the other spokes can keep the whole part connected.
A later cut that removes the connection is also rejected.

The browser check loads both fixtures in the existing viewer. It changes the wheel
radius with the existing parameter editor. Downloaded JSON retains the recipe
metadata and changes only the requested parameter. Original revisions stay intact.
The `invalid` fixture directory covers unknown operations, negative dimensions,
dependency cycles, unresolved values, executable expressions, invalid frames,
unknown evidence references, and incorrect body outputs. All return useful HTTP 422 errors.
See `report.json` and the screenshots in this directory.

## Existing recipes and migration

Version 1 remains supported. Loading and editing it does not rewrite it as version 2.
`migrate_v1()` returns a new version 2 document. It preserves all version 1 fields,
parameter metadata, and operations. It adds explicit dependencies and empty evidence
and constraint lists. It does not invent observed evidence or connection claims.

Example for a separate migrated file:

```python
import json
from pathlib import Path
from doodle_to_cad.construction_recipe import migrate_v1
source = json.loads(Path("saved.recipe.json").read_text())
Path("migrated.recipe.json").write_text(json.dumps(migrate_v1(source), indent=2))
```

The product test loads and edits a version 1 result, then builds its migrated recipe.
The parameter lists and solid volumes match. The original source remains unchanged.

The full regression suite passes: **88 tests**. The existing Starlette/httpx
deprecation warning remains. No browser script errors occurred.

## Reproduce

```sh
DOODLE_RESULTS_DIR=results/brep-recipe-product .venv/bin/python -m uvicorn doodle_to_cad.app:app --host 127.0.0.1 --port 8082
CHROMIUM_EXECUTABLE=/path/to/chrome .venv/bin/python scripts/check_recipe_product.py
DOODLE_BREP_PYTHON="$PWD/workers/brep/.venv/bin/python" .venv/bin/python -m pytest -q
```

## Limits and gate

This task does not fix the knob USD round-trip failure or the drawing-fidelity
errors observed in task 02. It does not add a sketch constraint solver, backend
selection, arbitrary coordinate transforms, or model-generated version 2 recipes.
Only explicitly declared connections are checked. A valid recipe can still encode
the wrong design. User review is pending. Do not merge or start task 04 yet.
Integration commit: pending.
