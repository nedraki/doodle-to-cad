"""Optional backend boundary: recipe in, checked mesh + USD + diagnostics out."""
from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import tempfile
import uuid

from .brep_recipe import recipe_params, validate_recipe

WORKER = Path(__file__).resolve().parents[1] / "workers" / "brep" / "build.py"


def worker_python():
    configured = os.getenv("DOODLE_BREP_PYTHON", str(WORKER.parent / ".venv" / "bin" / "python"))
    if not configured or not Path(configured).is_file():
        raise ValueError("Set DOODLE_BREP_PYTHON to an isolated Python 3.12 worker; see docs/brep/README.md")
    return configured


def build_recipe(out: Path, recipe: dict, updates: dict | None = None):
    """Publish a unique immutable revision only after all worker checks pass."""
    edited, _ = validate_recipe(recipe, updates)
    python = worker_python()
    out.mkdir(parents=True, exist_ok=True)
    tag = f"brep-{uuid.uuid4().hex}"
    with tempfile.TemporaryDirectory(prefix=".brep-", dir=out) as tmp:
        staging = Path(tmp)
        source = staging / "model.recipe.json"
        source.write_text(json.dumps(edited, indent=2))
        try:
            process = subprocess.run([python, str(WORKER), str(source), str(staging)],
                                     capture_output=True, text=True, timeout=120,
                                     env={k: v for k, v in os.environ.items() if k not in {"PYTHONPATH", "PYTHONHOME"}})
        except OSError as exc:
            raise ValueError("Could not launch the configured BRep worker") from exc
        except subprocess.TimeoutExpired as exc:
            raise ValueError("BRep build timed out; last successful geometry retained") from exc
        if process.returncode:
            raise ValueError((process.stderr or process.stdout or "BRep worker crashed")[-2500:])
        diagnostics = json.loads((staging / "diagnostics.json").read_text())
        (staging / "worker.log").write_text(process.stdout + process.stderr)
        # Rename within one filesystem; no published files are ever overwritten.
        staging.rename(out / tag)
    prefix = f"/results/{out.name}/{tag}"
    return {"ok": True, "backend": "usd-brep", "applied": updates or {},
            "stl": f"{prefix}/model.stl", "source": f"{prefix}/model.recipe.json",
            "usd": f"{prefix}/model.usda", "diagnostics": diagnostics,
            "params": recipe_params(edited)}


RECIPE_PROMPT = """Translate the supplied design and OpenSCAD into ONE editable BRep recipe.
Return JSON only, never Python. Preserve positions, holes, dimensions and canonical
X=width, Y=depth, Z=height in mm, with lowest Z=0. Do not invent details.
This is an experimental translation: if unsupported, return {"unsupported":"reason"}.
Schema: {"version":1,"units":"mm","name":"part","parameters":{
"width":{"value":60,"min":30,"max":100,"label":"Width","unit":"mm","group":"Body"}},
"operations":[{"id":"body","kind":"box","origin":[0,0,0],"size":["width",40,5]}],"output":"body"}.
Dimensions are finite numbers or short arithmetic strings using parameter names,
+ - * / and parentheses only. Each parameter needs numeric value, min, max;
optional label, unit, description, group. Expose individual hole widths, heights,
positions, wall thicknesses and existing fillet radii with useful bounded ranges.
Operations in dependency order, exactly these fields:
box: id,kind,origin (3 coordinates),size (3 positive dimensions).
cylinder: id,kind,origin (base centre),radius,height,axis (x/y/z).
union/difference: id,kind,left,right (earlier operation IDs).
fillet: id,kind,body,radius,selector (all/parallel_x/parallel_y/parallel_z).
chamfer: id,kind,body,radius (all edges; radius is width across chamfer).
arc_pipe: id,kind,origin (arc centre),bend_radius,radius,angle (0<angle<=270).
arc_pipe is a solid circular profile swept along an XY arc from +X anticlockwise.
Use booleans for pockets/enclosures. Cutters must cross the owning wall.
Fillet selectors are geometric and are recomputed on each rebuild. No edge indices.
Maximum 64 parameters, 128 operations; output names the final operation.
No descriptive, unresolved or additional fields. Unsupported geometry must be reported.
"""
