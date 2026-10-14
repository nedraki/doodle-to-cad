"""Optional backend boundary: recipe in, checked mesh + USD + diagnostics out."""
from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import tempfile
import uuid

from .brep_recipe import recipe_params, validate_recipe
from .build_contract import BuildInput, BuildResult, BuildError, Diagnostic
from .openscad import render_views, mesh_health

WORKER = Path(__file__).resolve().parents[1] / "workers" / "brep" / "build.py"


def worker_python():
    configured = os.getenv("DOODLE_BREP_PYTHON", str(WORKER.parent / ".venv" / "bin" / "python"))
    if not configured or not Path(configured).is_file():
        raise BuildError("backend_unavailable", "Set DOODLE_BREP_PYTHON to an isolated Python 3.12 worker; see docs/brep/README.md")
    return configured


def build_brep(request: BuildInput, binary: str = "openscad", on_stage=lambda _: None) -> BuildResult:
    """Publish one immutable revision after the isolated worker passes its checks."""
    result = BuildResult("usd-brep", request.source)
    try:
        edited, _ = validate_recipe(json.loads(request.source.read_text()))
    except (ValueError, OSError) as exc:
        result.diagnostics.append(Diagnostic("invalid_input", str(exc)))
        return result
    try:
        python = worker_python()
    except ValueError as exc:
        result.diagnostics.append(Diagnostic("backend_unavailable", str(exc)))
        return result
    out = request.output_dir
    out.mkdir(parents=True, exist_ok=True)
    published = out / f"brep-{uuid.uuid4().hex}"
    with tempfile.TemporaryDirectory(prefix=".brep-", dir=out) as tmp:
        staging = Path(tmp)
        source = staging / "model.recipe.json"
        source.write_text(json.dumps(edited, indent=2))
        on_stage("building solid")
        try:
            process = subprocess.run([python, str(WORKER), str(source), str(staging)],
                                     capture_output=True, text=True, timeout=120,
                                     env={k: v for k, v in os.environ.items() if k not in {"PYTHONPATH", "PYTHONHOME"}})
        except OSError:
            result.diagnostics.append(Diagnostic("backend_unavailable", "Could not launch the configured BRep worker"))
            return result
        except subprocess.TimeoutExpired:
            result.diagnostics.append(Diagnostic("timeout", "BRep build timed out; last successful geometry retained"))
            return result
        result.log = process.stdout + process.stderr
        if process.returncode:
            failure_path = staging / "construction-error.json"
            failure = json.loads(failure_path.read_text()) if failure_path.exists() else {}
            result.diagnostics.append(Diagnostic(failure.get("code", "build_failed"),
                                                 failure.get("message", (result.log or "BRep worker crashed")[-2500:])))
            return result
        try:
            result.backend_details = json.loads((staging / "diagnostics.json").read_text())
            for name in ("model.stl", "model.usda"):
                if not (staging / name).stat().st_size:
                    raise ValueError(f"Empty worker output: {name}")
        except (OSError, ValueError) as exc:
            result.diagnostics.append(Diagnostic("invalid_output", str(exc)))
            return result
        on_stage("checking mesh")
        try:
            result.measurements = mesh_health(staging / "model.stl")
            if not result.measurements["watertight"] or result.measurements["components"] != 1:
                raise ValueError("BRep STL must contain one watertight component")
        except Exception as exc:
            result.diagnostics.append(Diagnostic("invalid_output", str(exc)))
            return result
        if request.render:
            on_stage("rendering views")
            # OpenSCAD renders the finished mesh; it does not build the BRep solid.
            preview = staging / "preview.scad"
            preview.write_text('import("model.stl");\n')
            views, log = render_views(preview, staging, binary)
            result.views = {name: published / path.name for name, path in views.items()}
            if log:
                result.diagnostics.append(Diagnostic("render_failed", log, "warning"))
                result.log += "\n" + log
        (staging / "worker.log").write_text(result.log)
        staging.rename(published)
    result.source = published / "model.recipe.json"
    result.stl = published / "model.stl"
    result.exports = {"usd": published / "model.usda"}
    return result


def build_recipe(out: Path, recipe: dict, updates: dict | None = None, *, on_stage=lambda _: None):
    """Compatibility API for the existing recipe and parameter endpoints."""
    from .config import settings
    edited, _ = validate_recipe(recipe, updates)
    out.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".input-", dir=out) as tmp:
        source = Path(tmp) / "model.recipe.json"
        source.write_text(json.dumps(edited))
        result = build_brep(BuildInput("usd-brep", source, out), settings.openscad_bin, on_stage)
    if not result.ok:
        error = next(d for d in result.diagnostics if d.severity == "error")
        raise BuildError(error.code, error.message)
    def url(path):
        return f"/results/{out.name}/{path.relative_to(out).as_posix()}"
    return {"ok": True, "backend": "usd-brep", "applied": updates or {},
            "stl": url(result.stl), "source": url(result.source),
            "usd": url(result.exports["usd"]), "diagnostics": result.backend_details,
            "views": {name: url(path) for name, path in result.views.items()},
            "build": result.metadata(), "params": recipe_params(edited)}


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
