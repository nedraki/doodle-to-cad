from __future__ import annotations

import asyncio
import json
import re
import time
import uuid

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .config import ROOT, settings
from .model_client import CompatibleModelClient
from .openscad import available
from .params import extract_params, rewrite_params
from .pipeline import Pipeline

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
        if JOBS[key]["status"] != "running":
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
    scad = out / "model.scad"
    if not scad.exists():
        raise HTTPException(404, "Run has no model to edit")
    return out, scad


@app.get("/api/results/{run_id}/params")
def get_params(run_id: str):
    """Numeric top-level parameters the accepted model exposes for live editing."""
    out, scad = _run_dir(run_id)
    cached = out / "parameters.json"
    if cached.exists():
        return json.loads(cached.read_text())
    params = [p.to_dict() for p in extract_params(scad.read_text())]
    payload = {"run_id": run_id, "params": params}
    cached.write_text(json.dumps(payload, indent=2))
    return payload


@app.post("/api/results/{run_id}/parametrize")
def parametrize(run_id: str, updates: dict):
    """Rewrite top-level parameters, recompile, return a cache-busted STL URL.

    The accepted model.scad stays untouched; edits land in model-edited.scad
    so a reset is always one click away.
    """
    out, scad = _run_dir(run_id)
    base = scad.read_text()
    edited, applied = rewrite_params(base, {k: float(v) for k, v in updates.items() if isinstance(v, (int, float))})
    if not applied:
        raise HTTPException(422, {"message": "No known parameter matched the requested updates", "requested": sorted(updates)})
    from .openscad import compile_stl_only
    from .config import settings as _s
    stl_url, error = compile_stl_only(out, edited, f"edited-{len(applied)}-{'-'.join(sorted(applied))[:60]}", binary=_s.openscad_bin)
    if not stl_url:
        return {"ok": False, "applied": applied,
                "message": error or "Recompile produced no mesh — parameters reverted."}
    return {"ok": True, "applied": applied, "stl": stl_url}


@app.post("/api/generate")
async def generate(
    image: UploadFile = File(...), notes: str = Form(""), dimension: str = Form(""),
    object_type: str = Form(""), method: str = Form("3D print"), primary_view: str = Form("front"),
    projection_standard: str = Form("third-angle"),
    strict_watertight: bool = Form(True), view_directions: str = Form("[]"),
    refine_mode: str = Form("regularize"),
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
    payload["elapsed_seconds"] = round(time.monotonic() - job["created"], 1)
    return payload


@app.post("/api/generate/{job_id}/cancel")
async def job_cancel(job_id: str):
    job = JOBS.get(job_id)
    if not job: raise HTTPException(404, "Unknown job")
    if job["status"] == "running" and job["task"]:
        job["task"].cancel()
        await asyncio.sleep(0)  # let the cancellation settle into the job record
        return {"job_id": job_id, "status": job["status"]}
    return {"job_id": job_id, "status": job["status"]}
