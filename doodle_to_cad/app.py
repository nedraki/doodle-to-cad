from __future__ import annotations

import asyncio
import json
import re
import shutil
import time
import uuid

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .config import ROOT, settings
from .model_client import CompatibleModelClient
from .openscad import available
from .params import extract_params, rewrite_params, validate_updates
from .pipeline import Pipeline
from .brep import build_recipe, worker_python, RECIPE_PROMPT
from .brep_recipe import recipe_params, validate_recipe
from .build_contract import CAPABILITIES
from .recipe_jobs import check_worker, run_recipe_job

RUN_ID_RE = re.compile(r"^[0-9a-f]{6,32}$")
app = FastAPI(title="Doodle to CAD", version="0.1.0")
client = CompatibleModelClient(settings)
pipeline = Pipeline(settings, client)
settings.results_dir.mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=ROOT / "web"), name="static")
app.mount("/results", StaticFiles(directory=settings.results_dir), name="results")

# In-memory job registry. Generations run as background tasks so the browser
# submits once and polls; a dropped connection no longer loses the result,
# which still lands on disk under results/<run-id>/ regardless.
JOBS: dict[str, dict] = {}
MAX_TRACKED_JOBS = 25
JOB_ID_RE = re.compile(r"^[0-9a-f]{12}$")


def _prune_jobs() -> None:
    stale = sorted(JOBS, key=lambda key: JOBS[key]["created"])[:-MAX_TRACKED_JOBS]
    for key in stale:
        if JOBS[key]["status"] not in {"running", "cancelling", "waiting_for_answer"}:
            del JOBS[key]


@app.get("/")
def index(): return FileResponse(ROOT / "web" / "index.html")


@app.get("/api/health")
async def health(refresh: bool = False):
    model = await client.discover(refresh)
    return {"status":"ok" if model.selected and available(settings.openscad_bin) else "degraded","agentic":{"backend":"bounded-cad-supervisor","max_attempts":settings.agent_max_attempts,"accept_score":settings.agent_accept_score,"base_url":settings.base_url,"requested_model":settings.requested_model or None,"selected_model":model.selected,"model_source":model.source,"thinking_enabled":settings.enable_thinking,"thinking_budget":settings.thinking_budget,"structured_thinking_enabled":settings.structured_enable_thinking,"code_thinking_enabled":settings.code_enable_thinking,"available_models":model.available,"model_error":model.error},"openscad":{"binary":settings.openscad_bin,"available":available(settings.openscad_bin)}}


@app.get("/api/results/latest")
def latest_result():
    completed = sorted(settings.results_dir.glob("*/result.json"), key=lambda path: path.stat().st_mtime, reverse=True)
    if not completed:
        raise HTTPException(404, "No completed generation exists")
    return json.loads(completed[0].read_text())


def _run_dir(run_id: str):
    if not RUN_ID_RE.fullmatch(run_id):
        raise HTTPException(404, "Unknown run")
    out = settings.results_dir / run_id
    scad = out / "model.recipe.json" if (out / "model.recipe.json").exists() else out / "model.scad"
    if not scad.exists():
        raise HTTPException(404, "Run has no model to edit")
    return out, scad


@app.get("/api/results/{run_id}")
def get_result(run_id: str):
    out, _ = _run_dir(run_id)
    if not (out / "result.json").exists():
        raise HTTPException(404, "Run has no completed result")
    return json.loads((out / "result.json").read_text())


@app.get("/api/results/{run_id}/params")
def get_params(run_id: str):
    """Numeric top-level parameters the accepted model exposes for live editing."""
    out, scad = _run_dir(run_id)
    cached = out / "parameters.json"
    params = recipe_params(json.loads(scad.read_text())) if scad.suffix == ".json" else [p.to_dict() for p in extract_params(scad.read_text())]
    payload = {"run_id": run_id, "params": params}
    cached.write_text(json.dumps(payload, indent=2))
    return payload


@app.post("/api/results/{run_id}/parametrize")
def parametrize(run_id: str, updates: dict):
    """Rewrite top-level parameters, recompile, return a cache-busted STL URL.

    The accepted model.scad stays untouched; edits receive unique SCAD/STL filenames
    so a reset is always one click away.
    """
    out, scad = _run_dir(run_id)
    if scad.suffix == ".json":
        try:
            return build_recipe(out, json.loads(scad.read_text()), updates)
        except ValueError as exc:
            raise HTTPException(422, {"message": str(exc), "code": getattr(exc, "code", "invalid_input")}) from exc
    base = scad.read_text()
    try:
        validate_updates(base, updates)
    except ValueError as exc:
        raise HTTPException(422, {"message": str(exc), "code": getattr(exc, "code", "invalid_input")}) from exc
    edited, applied = rewrite_params(base, updates)
    if not applied:
        raise HTTPException(422, {"message": "No known parameter matched the requested updates", "requested": sorted(updates)})
    from .openscad import compile_stl_only
    from .config import settings as _s
    tag = f"edited-{uuid.uuid4().hex}"
    stl_url, error = compile_stl_only(out, edited, tag, binary=_s.openscad_bin)
    if not stl_url:
        return {"ok": False, "applied": applied,
                "message": error or "Recompile produced no mesh — last successful geometry retained."}
    return {"ok": True, "applied": applied, "stl": stl_url, "scad": f"/results/{run_id}/{tag}.scad", "params": [p.to_dict() for p in extract_params(edited)]}


@app.get("/api/backends")
def backend_capabilities():
    return {"version": 1, "backends": CAPABILITIES}


@app.get("/api/brep")
def brep_status():
    try:
        worker_python()
        return {"configured": True}
    except ValueError:
        return {"configured": False}


@app.post("/api/brep/jobs")
async def submit_recipe_job(recipe: dict):
    """Developer saved-recipe input; uses the existing status/cancel endpoints."""
    try:
        validate_recipe(recipe)
    except ValueError as exc:
        raise HTTPException(422, {"message": str(exc), "code": "invalid_input"}) from exc
    try:
        await check_worker()
    except (ValueError, OSError, asyncio.TimeoutError) as exc:
        raise HTTPException(422, {"message": str(exc) or "Worker check timed out", "code": getattr(exc, "code", "backend_unavailable")}) from exc
    run_id = uuid.uuid4().hex[:12]
    job = {"job_id": run_id, "kind": "recipe", "status": "running", "stage": "queued",
           "created": time.monotonic(), "result": None, "error": None, "task": None}
    JOBS[run_id] = job
    _prune_jobs()
    job["task"] = asyncio.create_task(run_recipe_job(job, recipe, settings.results_dir, _save_brep_result))
    return {"job_id": run_id, "status": "running"}


@app.post("/api/brep/build")
def brep_build(recipe: dict):
    """Build an explicit recipe without a model call (evaluation/import entrypoint)."""
    try:
        validate_recipe(recipe)
        worker_python()
        run_id = uuid.uuid4().hex[:12]
        out = settings.results_dir / run_id
        built = build_recipe(out, recipe)
        return _save_brep_result(out, recipe, built)
    except ValueError as exc:
        raise HTTPException(422, {"message": str(exc), "code": getattr(exc, "code", "invalid_input")}) from exc


def _save_brep_result(out, recipe, built, original=None, controls=None):
    (out / "model.recipe.json").write_text(json.dumps(recipe, indent=2))
    result = {"id": out.name, "backend": "usd-brep", "success": False,
              "spec": {"object": recipe.get("name", "BRep part")},
              "model": "experimental BRep recipe", "duration_seconds": built["diagnostics"]["build_seconds"],
              "evaluation": {"accepted": False, "failures": ["Drawing fidelity has not been evaluated."]},
              "diagnostics": built["diagnostics"], "controls": controls or {"primary_view": "front"},
              "files": {"source": built["source"], "stl": built["stl"], "usd": built["usd"], "views": built.get("views", {})},
              "build": built.get("build"),
              "original_run_id": original}
    temporary = out / "result.pending.json"
    temporary.write_text(json.dumps(result, indent=2))
    temporary.replace(out / "result.json")
    return result


@app.post("/api/results/{run_id}/brep")
async def brep_from_result(run_id: str):
    """Create a separate candidate; translating code is not an exact conversion."""
    out, source = _run_dir(run_id)
    if source.suffix == ".json":
        raise HTTPException(422, "This result already uses a BRep recipe")
    try:
        worker_python()
        original = json.loads((out / "result.json").read_text())
        candidate = settings.results_dir / uuid.uuid4().hex[:12]
        candidate.mkdir(parents=True)
        recipe = await pipeline._json_call([
            {"role": "system", "content": RECIPE_PROMPT},
            {"role": "user", "content": json.dumps({"spec": original.get("spec"), "scad": source.read_text()})},
        ], candidate, "brep-recipe")
        if "unsupported" in recipe:
            raise ValueError(str(recipe["unsupported"]))
        validate_recipe(recipe)
        built = await asyncio.to_thread(build_recipe, candidate, recipe)
        if (out / "input.png").exists():
            shutil.copyfile(out / "input.png", candidate / "input.png")
        return _save_brep_result(candidate, recipe, built, run_id, original.get("controls"))
    except ValueError as exc:
        raise HTTPException(422, {"message": str(exc), "code": getattr(exc, "code", "invalid_input")}) from exc


@app.post("/api/dev/interpret")
async def interpret_drawing(image: UploadFile = File(...), primary_view: str = Form("front"),
                            projection_standard: str = Form("third-angle")):
    if image.content_type not in {"image/png", "image/jpeg", "image/webp"}:
        raise HTTPException(415, "Upload PNG, JPEG, or WebP")
    data = await image.read()
    if len(data) > 15_000_000:
        raise HTTPException(413, "Image exceeds 15 MB")
    if primary_view not in {"front", "top", "right", "left", "rear"} or projection_standard not in {"first-angle", "third-angle"}:
        raise HTTPException(422, "Invalid view controls")
    try:
        return await pipeline.interpret_features(data, image.content_type,
            {"primary_view": primary_view, "projection_standard": projection_standard})
    except ValueError as exc:
        raise HTTPException(422, {"message": str(exc)}) from exc


@app.post("/api/generate")
async def generate(
    image: UploadFile = File(...), notes: str = Form(""), dimension: str = Form(""),
    object_type: str = Form(""), method: str = Form("3D print"), primary_view: str = Form("front"),
    projection_standard: str = Form("third-angle"),
    strict_watertight: bool = Form(True), view_directions: str = Form("[]"),
    refine_mode: str = Form("regularize"), backend: str = Form("openscad"),
    additional_views: list[UploadFile] = File(default=[]),
):
    if image.content_type not in {"image/png","image/jpeg","image/webp"}: raise HTTPException(415,"Upload PNG, JPEG, or WebP")
    data=await image.read()
    if len(data)>15_000_000: raise HTTPException(413,"Image exceeds 15 MB")
    try:
        directions = json.loads(view_directions)
        extra = []
        for index, upload in enumerate(additional_views):
            extra.append((directions[index] if index < len(directions) else "additional", await upload.read(), upload.content_type or "image/png"))
        controls = {"object_type_hint": object_type, "method": method, "primary_view": primary_view, "projection_standard": projection_standard, "strict_watertight": strict_watertight, "refine_mode": "as_drawn" if refine_mode == "as_drawn" else "regularize"}
    except json.JSONDecodeError as exc:
        raise HTTPException(422, {"message": f"view_directions is not valid JSON: {exc}", "error_type": type(exc).__name__, "stage": "request"}) from exc

    if backend not in {"openscad", "usd-brep"}:
        raise HTTPException(422, "Unknown generation backend")
    if backend == "usd-brep":
        from .direct_brep import submit_direct_job
        return await submit_direct_job(data, image.content_type, notes, dimension, extra, controls,
                                       pipeline, settings.results_dir, JOBS, _prune_jobs, _save_brep_result)

    run_id = uuid.uuid4().hex[:12]
    job = {"job_id": run_id, "status": "running", "stage": "queued", "created": time.monotonic(),
           "result": None, "error": None, "task": None}
    JOBS[run_id] = job
    _prune_jobs()

    async def run_job():
        try:
            result = await pipeline.generate(
                data, image.content_type, notes, dimension, extra, controls,
                run_id=run_id, on_stage=lambda name: job.update(stage=name),
            )
            job["result"] = result
            job["status"] = "done"
            job["stage"] = "done"
        except asyncio.CancelledError:
            job["status"] = "cancelled"
            job["stage"] = "cancelled"
            job["error"] = {"message": "Generation cancelled.", "error_type": "Cancelled", "stage": job.get("stage")}
            raise
        except Exception as exc:
            job["status"] = "error"
            job["stage"] = "failed"
            job["error"] = {"message": str(exc), "error_type": type(exc).__name__, "stage": "generation"}

    job["task"] = asyncio.create_task(run_job())
    return {"job_id": run_id, "status": "running"}


@app.get("/api/generate/{job_id}")
def job_status(job_id: str):
    job = JOBS.get(job_id)
    if not job:
        # Registry is in-memory; survive restarts by falling back to the on-disk result.
        if JOB_ID_RE.match(job_id) and (settings.results_dir / job_id / "result.json").exists():
            return {"job_id": job_id, "status": "done", "stage": "done",
                    "result": json.loads((settings.results_dir / job_id / "result.json").read_text())}
        raise HTTPException(404, "Unknown job")
    payload = {key: job[key] for key in ("job_id", "status", "stage", "result", "error")}
    if job.get("question"): payload["question"] = job["question"]
    payload["elapsed_seconds"] = round(time.monotonic() - job["created"], 1)
    return payload


@app.post("/api/generate/{job_id}/cancel")
async def job_cancel(job_id: str):
    job = JOBS.get(job_id)
    if not job: raise HTTPException(404, "Unknown job")
    if job["status"] in {"running", "waiting_for_answer"} and job["task"]:
        job["task"].cancel()
        if job.get("kind") == "recipe":
            try:
                await job["task"]
            except asyncio.CancelledError:
                pass
            job.update(status="cancelled", stage="cancelled")
        else:
            await asyncio.sleep(0)  # let the cancellation settle into the job record
        return {"job_id": job_id, "status": job["status"]}
    return {"job_id": job_id, "status": job["status"]}


@app.post("/api/generate/{job_id}/answer")
async def answer_question(job_id: str, payload: dict):
    from .clarification import accept_answer
    job=JOBS.get(job_id)
    if not job:raise HTTPException(404, "Unknown job")
    return accept_answer(job,payload)
