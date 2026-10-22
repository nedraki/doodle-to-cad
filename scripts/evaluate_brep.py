"""Backend comparison harness for the BRep product-default decision (issue #34).

Two modes:
  (1) Deterministic recipe-vs-reference comparison; no model required.
      DOODLE_BREP_PYTHON=/path/to/worker/python .venv/bin/python scripts/evaluate_brep.py
  (2) Live product-API trials (issue #34 / docs/brep/task-17-comparison).
      DOODLE_BREP_PYTHON=/path/to/worker/python PYTHONPATH=. .venv/bin/python \
        scripts/evaluate_brep.py trials --plan docs/brep/task-17-comparison/TRIAL-PLAN.json

Trials mode drives the real app (in-process uvicorn, port 8130-8139) through
POST /api/generate and the edit endpoints. It never fabricates outcomes: every
run keeps its result.json copy, job payload and measurement row under the
evidence folder, failures included.
"""
import json
import os
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

REFERENCES = {
    "bracket": '''difference(){union(){cube([60,40,5]);cube([60,5,80]);}
for(x=[10,35])for(z=[20,50])translate([x,-1,z])cube([10,7,15]);}''',
    "enclosure": '''$fn=96;difference(){hull(){for(x=[2,58])for(y=[2,38])
translate([x,y,0])cylinder(r=2,h=25);}translate([3,3,3])cube([54,34,25]);}''',
    "curved_pipe": '''$fn=128;translate([0,0,3])rotate_extrude(angle=90)
translate([20,0])circle(r=3);''',
}
EDITS = {"bracket": {"hole1_width": 12, "hole1_x": 12},
         "enclosure": {"wall": 4, "fillet": 3},
         "curved_pipe": {"bend_radius": 25, "tube_radius": 4}}


def main():
    from doodle_to_cad.brep import build_recipe
    from doodle_to_cad.config import settings
    from doodle_to_cad.openscad import compile_stl_only, mesh_health
    rows = []
    output = ROOT / "results" / "brep-evaluation"
    output.mkdir(parents=True, exist_ok=True)
    for name, scad in REFERENCES.items():
        recipe = json.loads((ROOT / "benchmarks" / "brep" / f"{name}.json").read_text())
        out = output / name
        out.mkdir(exist_ok=True)
        start = time.monotonic()
        built = build_recipe(out, recipe)
        baseline_elapsed = time.monotonic()-start
        start = time.monotonic()
        edited = build_recipe(out, recipe, EDITS[name])
        edit_elapsed = time.monotonic()-start
        start = time.monotonic()
        url, error = compile_stl_only(out, scad, 'reference', settings.openscad_bin)
        scad_elapsed = time.monotonic()-start
        row = {"case": name, "brep": built['diagnostics'], "edit": edited['diagnostics'],
               "updates": EDITS[name], "brep_wall_seconds": round(baseline_elapsed,3),
               "edit_wall_seconds": round(edit_elapsed,3), "openscad_wall_seconds": round(scad_elapsed,3),
               "openscad": mesh_health(out / 'reference.stl') if url else {"error": error}}
        rows.append(row)
        print(name, row['brep_wall_seconds'], row['edit_wall_seconds'], row['openscad'])
    (ROOT / "docs" / "brep" / "evaluation.json").write_text(json.dumps(rows,indent=2)+'\n')


# ---------------------------------------------------------------------------
# trials mode (issue #34)
# ---------------------------------------------------------------------------

def _iso_now():
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat()


# ---- environment fingerprint (issue #85) -----------------------------------
# The frozen plan's evidence_layout declared 'environment.json ... written at
# trial end' but the harness never wrote it. Declared evidence that is never
# written is worse than absent evidence, so this is now a single choke point:
# EVERY row.json write goes through _finish_row, which always writes the
# environment file alongside (collection errors land in _collect_error,
# never a silently missing file).
_SERVER_MODEL = None  # set once by _drive from /api/health, like the log line
_ENV_STATIC = None


def _environment_static():
    """Build once per harness run; per-trial calls only stamp dates."""
    global _ENV_STATIC
    if _ENV_STATIC is not None:
        return _ENV_STATIC
    import platform
    import subprocess
    from urllib.parse import urlsplit
    from doodle_to_cad.config import settings
    record = {"collected_by": "evaluate_brep.py (issue #85)",
              "tested_commit": None, "python": sys.version,
              "platform": platform.platform(),
              "model_base_url": getattr(settings, "base_url", None),
              "model_host": urlsplit(getattr(settings, "base_url", "") or "").hostname,
              "server_model": _SERVER_MODEL,
              "doodle_brep_python": os.environ.get("DOODLE_BREP_PYTHON"),
              "results_dir": os.environ.get("DOODLE_RESULTS_DIR")}
    try:
        record["tested_commit"] = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=str(ROOT), text=True).strip()
    except Exception as exc:
        record.setdefault("_collect_error", [])\
            .append(f"git rev: {exc}")
    worker = os.environ.get("DOODLE_BREP_PYTHON")
    if worker:
        try:
            record["worker_packages"] = json.loads(subprocess.check_output(
                ["uv", "pip", "list", "--python", worker, "--format", "json"],
                text=True))
        except Exception as exc:
            record.setdefault("_collect_error", []).append(f"worker pkgs: {exc}")
    try:
        from importlib.metadata import version
        record["application_packages"] = {
            name: version(name) for name in
            ("fastapi", "httpx", "numpy", "trimesh", "networkx", "pillow")}
    except Exception as exc:
        record.setdefault("_collect_error", []).append(f"app pkgs: {exc}")
    image = os.environ.get("DOODLE_OPENSCAD_DOCKER")
    if image:
        record["openscad_docker_image"] = image
        try:
            record["openscad_docker_image_id"] = subprocess.check_output(
                ["docker", "image", "inspect", image, "--format", "{{.Id}}"],
                text=True).strip()
        except Exception as exc:
            record.setdefault("_collect_error", []).append(f"docker image: {exc}")
    _ENV_STATIC = record
    return record


def _finish_row(cell, row):
    """The ONLY sanctioned way to persist a trial row: environment.json first
    (declared evidence must exist), then row.json, atomically enough that a
    crash mid-write never leaves a row without its environment record."""
    try:
        env = dict(_environment_static())
        env["trial"] = f'{row.get("drawing")}/{row.get("backend")}/t{row.get("trial")}'
        env["trial_submitted_at"] = row.get("submitted_at")
        env["trial_finished_at"] = row.get("finished_at") or _iso_now()
        env["written_at"] = _iso_now()
        (cell / "environment.json").write_text(json.dumps(env, indent=2) + "\n")
    except Exception as exc:  # the file is still attempted; failure is recorded in row
        row["environment_write_error"] = str(exc)
    (cell / "row.json").write_text(json.dumps(row, indent=2))


def _measure_stl(path):
    """Independent trimesh re-measurement of a run STL."""
    import trimesh
    loaded = trimesh.load_mesh(path, process=True)
    if isinstance(loaded, trimesh.Scene):
        import trimesh as _t
        loaded = _t.util.concatenate(tuple(loaded.geometry.values()))
    components = loaded.split(only_watertight=False)
    watertight = bool(components) and all(c.is_watertight for c in components)
    genus = None
    if len(components) == 1 and watertight:
        e = int(components[0].euler_number)
        genus = (2 - e) // 2 if (2 - e) % 2 == 0 else None
    return {"watertight": watertight, "components": len(components), "genus": genus,
            "extents_mm": [round(float(v), 3) for v in loaded.extents],
            "volume_mm3": round(float(sum(abs(c.volume) for c in components)), 1)}


def _stl_url_to_path(run_dir, url):
    return run_dir / Path(url).relative_to(f"/results/{run_dir.name}")


def _pick_param(params):
    import re
    numeric = [p for p in params if isinstance(p, dict)
               and isinstance(p.get("value"), (int, float)) and not isinstance(p.get("value"), bool)
               and p.get("value", 0) > 0]
    preferred = [p for p in numeric if re.search(r"thick|width|radius|depth|height|diameter", str(p.get("name", "")), re.I)]
    return (preferred or numeric or [None])[0]


def _param_new_value(p):
    v = float(p["value"])
    lo = p.get("min") if isinstance(p.get("min"), (int, float)) else None
    hi = p.get("max") if isinstance(p.get("max"), (int, float)) else None
    target = round(v * 1.2, 2)
    if hi is not None:
        target = min(target, float(hi))
    if lo is not None:
        target = max(target, float(lo))
    if abs(target - v) < 1e-6:  # the 1.2x step collapsed against a bound
        alt = round(v * 0.8, 2)
        if hi is not None:
            alt = min(alt, float(hi))
        if lo is not None:
            alt = max(alt, float(lo))
        if abs(alt - v) < 1e-6:
            return None
        target = alt
    return target


def _rule_number(rule, recipe):
    """Best numeric anchor for a targeted-edit value probe."""
    import re
    for key in ("depth", "radius", "thickness", "size", "value"):
        v = (rule or {}).get(key)
        if isinstance(v, (int, float)) and not isinstance(v, bool) and v > 0:
            return float(v)
    text = json.dumps({"rule": rule, "params": recipe.get("parameters", {})})
    for match in re.finditer(r":\s*([0-9]+(?:\.[0-9]+)?)", text):
        value = float(match.group(1))
        if 0 < value <= 256:
            return value
    return 10.0


def reference_checks(measurement, reference, supplied_dimension=None, tolerance_mm=1.0):
    """Pure comparison shared by _run_trial and the #81 fixture gate.

    One source of truth for build/extents/genus/volume verdicts so a fixture
    exercises exactly the check the live harness applies. Returns
    (checks, not_applicable).

    #102 supplied-dimension contract: a dimension the case actually gave the
    model (plan corpus 'dimension', the requested maximum) must survive to
    the mesh within tolerance_mm (plan tolerances.supplied_dimension_mm).
    Reference-only expectations (ground-truth extents nobody supplied) stay
    on the 2% extents check - the two tracks never gate each other. The
    result is reported alongside, never inside, overall_pass."""
    ground_truth = reference.get("kind") != "no_ground_truth" and "genus" in reference
    build_success = bool(measurement and measurement.get("watertight")
                         and measurement.get("components") == 1)
    checks: dict = {"build_success": build_success}
    na: list = []
    if not ground_truth:
        na += ["extents", "genus", "volume"]
        checks.update({"extents_pass": None, "genus_pass": None, "volume_pass": None})
    else:
        extents_pass = bool(measurement) and all(
            abs(a - b) <= 0.02 * max(b, 1e-9) for a, b in
            zip(sorted(measurement["extents_mm"]), sorted(reference["extents_mm"])))
        genus_pass = bool(measurement) and measurement.get("genus") == reference["genus"]
        volume_pass = bool(measurement) and abs(measurement["volume_mm3"] - reference["volume_mm3"]) <= 0.02 * reference["volume_mm3"]
        checks.update({"extents_pass": extents_pass, "genus_pass": genus_pass, "volume_pass": volume_pass})
    if supplied_dimension is None:
        na.append("supplied_dimension")  # key absent, same as no-ground-truth na style
    else:
        checks["supplied_dimension_pass"] = (
            bool(measurement) and "extents_mm" in measurement
            and abs(max(measurement["extents_mm"]) - supplied_dimension) <= tolerance_mm)
    return checks, na


def _copy_evidence(run_dir: Path, cell: Path) -> None:
    """Copy the whitelisted per-run files into the frozen trial cell.

    Gate for the #95 follow-up: a construction plan rejected by the gate never
    produces construction-plan.json (direct_brep writes that only after
    validate_plan passes), so the model's raw transcript is the only surviving
    witness of WHY the gate fired. _json_call already writes it next to the
    run; without copying it here the evidence is produced and then discarded,
    the same 'produced-but-never-persisted' family as issue #85.
    """
    import shutil
    for name in ("model.scad", "model.recipe.json", "geometry.json", "generation.json",
                 "attempts.json", "clarifications.json", "construction-plan.json",
                 "error.json", "drawing-checks.json", "geometry-overlay.png", "sketch-spec.json",
                 "input.png"):
        if (run_dir / name).exists():
            shutil.copyfile(run_dir / name, cell / name)
    for raw in sorted(run_dir.glob("construction-plan*.raw.txt")):
        if (cell / raw.name).exists():
            raise RuntimeError(f"refusing to overwrite existing evidence {cell / raw.name}")
        shutil.copyfile(raw, cell / raw.name)
    # #89: kernel-crash forensics. Each build attempt leaves its triggering
    # recipe, kernel failure payload, the stage (op id) captured at the crash,
    # and the runner log in construction-attempts/N/. Only the LAST attempt's
    # error.json survives at top level, so a crash on attempt 1 of 3 was
    # frozen as a recipe without the message that killed it (ATTRIBUTION
    # 'wheel usd t1'). Carry all four, append-only, next to the attempts.
    for attempt_dir in sorted(run_dir.glob("construction-attempts/*")):
        for name in ("recipe.json", "failure.json", "stage.txt", "runner.log"):
            src = attempt_dir / name
            if not src.exists():
                continue
            dest = cell / "failed" / f"{attempt_dir.name}.{name}"
            dest.parent.mkdir(exist_ok=True)
            if dest.exists():
                raise RuntimeError(f"refusing to overwrite existing evidence {dest}")
            shutil.copyfile(src, dest)


async def _run_trial(client, plan, item, backend, trial, out_dir, semaphore):
    import asyncio
    import hashlib
    import shutil
    from doodle_to_cad.config import settings

    cell = out_dir / item["id"] / backend / f"trial-{trial:02d}"
    if (cell / "row.json").exists():
        return json.loads((cell / "row.json").read_text())
    cell.mkdir(parents=True, exist_ok=True)
    row = {"drawing": item["id"], "backend": backend, "trial": trial,
           "submitted_at": None, "finished_at": None}
    plan_infra = plan["infrastructure"]
    image = (ROOT / item["drawing"]).read_bytes()
    (cell / "input.png").write_bytes(image)
    form = {"backend": backend, "notes": item["notes"], "object_type": "", "method": "3D print",
            "primary_view": item["primary_view"], "projection_standard": "third-angle",
            "strict_watertight": "true", "view_directions": "[]", "refine_mode": "regularize",
            "dimension": item["dimension"],
            "ask_missing_dimensions": "true" if item.get("ask_dimensions") else "false"}
    (cell / "request.json").write_text(json.dumps(
        {"form": form, "image_sha256": hashlib.sha256(image).hexdigest(),
         "source": item["drawing"], "reference_geometry_sent": False}, indent=2))
    questions = []
    async with semaphore:
        started = time.monotonic()
        row["submitted_at"] = _iso_now()
        try:
            response = await client.post("/api/generate", files={"image": ("drawing.png", image, "image/png")}, data=form)
            response.raise_for_status()
            job = response.json()["job_id"]
        except Exception as exc:
            row.update(job_status="submit_failed", error={"message": str(exc)})
            _finish_row(cell, row)
            return row
        row["run_id"] = job
        deadline = started + plan_infra["poll_timeout_seconds"]
        status = {}
        while time.monotonic() < deadline:
            try:
                status = (await client.get(f"/api/generate/{job}")).json()
            except Exception as exc:
                row.setdefault("poll_errors", []).append(str(exc))
                await asyncio.sleep(2)
                continue
            if status["status"] == "waiting_for_answer":
                question = status.get("question") or {}
                kind = question.get("kind", "opening_extent")
                answer_policy = plan["clarification_policy"]["answers"]
                payload = {"question_id": question.get("id")}
                if kind == "body_dimension" and kind not in answer_policy:
                    # Unattended harness cannot invent a user dimension
                    # (issue #68); let the ask time out instead of guessing.
                    await asyncio.sleep(min(130, plan_infra["poll_timeout_seconds"] - (time.monotonic() - started)))
                    questions.append({"kind": kind, "feature_id": question.get("feature_id"),
                                      "text": question.get("text"), "answer": None, "note": "left to timeout"})
                    continue
                payload.update(answer_policy.get(kind, {"choice": "through"}))
                try:
                    result = await client.post(f"/api/generate/{job}/answer", json=payload)
                    questions.append({"kind": kind, "feature_id": question.get("feature_id"),
                                      "text": question.get("text"), "answer": payload,
                                      "http": result.status_code})
                except Exception as exc:
                    questions.append({"kind": kind, "error": str(exc)})
                if len(questions) > plan["clarification_policy"]["max_answered_questions"]:
                    await client.post(f"/api/generate/{job}/cancel")
                    status = {"status": "error", "error": {"code": "clarification_stalled",
                              "message": "still waiting after the frozen answer budget"}}
                    break
                await asyncio.sleep(1)
                continue
            if status["status"] not in ("running", "cancelling"):
                break
            await asyncio.sleep(2)
        else:
            try:
                await client.post(f"/api/generate/{job}/cancel")
            except Exception:
                pass
            status = {"status": "timeout", "error": {"code": "poll_timeout",
                      "message": f"exceeded {plan_infra['poll_timeout_seconds']} s"}}
    row["finished_at"] = _iso_now()
    row["wall_seconds"] = round(time.monotonic() - started, 1)
    row["job_status"] = status.get("status")
    row["error"] = status.get("error")
    (cell / "job.json").write_text(json.dumps(
        {k: status.get(k) for k in ("job_id", "status", "stage", "error")}, indent=2))
    (cell / "questions.json").write_text(json.dumps(questions, indent=2))
    row["questions_asked"] = len(questions)
    row["question_kinds"] = sorted({q.get("kind") for q in questions if q.get("kind")})

    run_dir = settings.results_dir / job
    result = None
    if (run_dir / "result.json").exists():
        result = json.loads((run_dir / "result.json").read_text())
        shutil.copyfile(run_dir / "result.json", cell / "result.json")
    _copy_evidence(run_dir, cell)
    for failed in sorted(run_dir.glob("attempt-*/*.failed.scad")):
        (cell / "failed").mkdir(exist_ok=True)
        shutil.copyfile(failed, cell / "failed" / f"{failed.parent.name}-{failed.name}")
    if result is None:
        row["build"] = None
        row["checks"] = {"build_success": False, "overall_pass": False}
        _finish_row(cell, row)
        _append_index(out_dir, row)
        return row

    # ---- independent geometry measurement ---------------------------------
    stl = None
    stl_url = (result.get("files") or {}).get("stl")
    if stl_url:
        candidate = _stl_url_to_path(run_dir, stl_url)
        if candidate.exists():
            stl = candidate
    measurement = None
    if stl is not None:
        try:
            measurement = await asyncio.to_thread(_measure_stl, stl)
            measurement["sha256"] = hashlib.sha256(stl.read_bytes()).hexdigest()
            measurement["bytes"] = stl.stat().st_size
            if measurement["bytes"] < 1_500_000 or not measurement["watertight"] or measurement["components"] != 1:
                (cell / "stl").mkdir(exist_ok=True)
                shutil.copyfile(stl, cell / "stl" / "model.stl")
        except Exception as exc:
            measurement = {"measure_error": str(exc)}
    row["build"] = measurement

    refs = json.loads((Path(plan["_plan_dir"]) / "references" / "reference-measurements.json").read_text())
    ref_key = {"profiles_empty_notes": "profiles", "missing_thickness": "missing_thickness"}.get(item["id"], item["id"])
    reference = refs.get(ref_key) or {}
    ground_truth = reference.get("kind") != "no_ground_truth" and "genus" in reference

    # #102: fail-loud on a malformed certified dimension - a frozen plan
    # must be exact, silent fallback here would hide a plan typo.
    _dim = str(item.get("dimension") or "").strip()
    supplied_dimension = float(item["dimension"]) if _dim else None
    checks, na = reference_checks(
        measurement, reference, supplied_dimension=supplied_dimension,
        tolerance_mm=float(plan.get("tolerances", {}).get("supplied_dimension_mm", 1.0)))

    # ---- harness-independent drawing fidelity (separate from build) --------
    fidelity = {"scores": None, "pass": None, "reason": None}
    try:
        from doodle_to_cad.evaluation import projection_scores
        from doodle_to_cad.feature_evidence import view_assignment_evidence
        evidence = result.get("geometry")
        if backend == "usd-brep":
            evidence = view_assignment_evidence(json.loads((run_dir / "geometry.json").read_text()))
        views = {}
        (cell / "views").mkdir(exist_ok=True)
        for name, url in ((result.get("files") or {}).get("views") or {}).items():
            path = _stl_url_to_path(run_dir, url)
            if path.exists():
                views[name] = path
                shutil.copyfile(path, cell / "views" / f"{name}.png")
        if evidence and views:
            scores, topology = await asyncio.to_thread(
                projection_scores, image, evidence, views, item["primary_view"], "third-angle")
            fidelity["scores"] = {k: round(float(v), 3) for k, v in scores.items()}
            fidelity["topology"] = {k: {"expected": t.get("crop_internal_profiles"),
                                        "actual": t.get("rendered_internal_profiles"),
                                        "position_fidelity": t.get("feature_position_fidelity")}
                                    for k, t in topology.items()}
            if scores:
                fidelity["pass"] = all(v >= plan["tolerances"]["projection_similarity_min"] for v in scores.values())
            else:
                fidelity["reason"] = "no registered view pairs"
        elif not views:
            fidelity["reason"] = "no rendered views on disk"
        else:
            fidelity["reason"] = "no geometry evidence"
    except Exception as exc:
        fidelity["reason"] = f"harness error: {exc}"
    checks["fidelity_pass"] = fidelity["pass"]
    if fidelity["pass"] is None:
        na.append("fidelity")
    # #102: the supplied-dimension contract is a separate track (like
    # build_success was made separate from fidelity); it never changes the
    # meaning of already-frozen overall_pass values.
    applicable = [v for k, v in checks.items() if v is not None and k != "supplied_dimension_pass"]
    checks["overall_pass"] = bool(applicable) and all(applicable) and checks["build_success"]
    checks["not_applicable"] = na
    row["checks"] = checks
    row["fidelity"] = fidelity

    # ---- product's own verdicts (recorded, never the harness pass) --------
    evaluation = result.get("evaluation") or {}
    row["product"] = {
        "success": result.get("success"),
        "accepted": evaluation.get("accepted"),
        "status": evaluation.get("status"),
        "score": evaluation.get("score"),
        "projection_status": evaluation.get("projection_status"),
        "geometry_status": evaluation.get("geometry_status"),
        "failures": evaluation.get("failures"),
    }

    # ---- recovery / attempts ------------------------------------------------
    attempts_info = {"count": None, "recovered": False, "corrections": None}
    if backend == "openscad":
        attempts = result.get("attempts") or []
        attempts_info["count"] = len(attempts)
        attempts_info["selected"] = result.get("selected_attempt")
        attempts_info["recovered"] = bool(result.get("success") and len(attempts) > 1)
    else:
        generation = result.get("generation") or {}
        schema_attempts = generation.get("attempts") or []
        corrections = generation.get("construction_attempts") or []
        attempts_info["count"] = len(schema_attempts)
        attempts_info["corrections"] = len(corrections)
        attempts_info["recovered"] = bool(checks["build_success"] and (len(schema_attempts) > 1 or len(corrections) > 1))
    row["attempts"] = attempts_info

    # ---- unsupported-operation outcome -------------------------------------
    code = (row.get("error") or {}).get("code")
    row["unsupported"] = {"flag": code in {"unsupported_construction", "unresolved_design", "clarification_stalled"},
                          "code": code}

    # ---- BRep-only capabilities (own table; never an OpenSCAD failure) -----
    if backend == "usd-brep" and (cell / "model.recipe.json").exists():
        try:
            recipe = json.loads((cell / "model.recipe.json").read_text())
            kinds = sorted({op["kind"] for op in recipe.get("operations", [])})
            row["brep_only"] = {"operations": kinds,
                                "loft": "loft" in kinds, "shell": "shell" in kinds,
                                "arc_pipe": "arc_pipe" in kinds, "sweep": "sweep" in kinds,
                                "extrude": "extrude" in kinds,
                                "parameter_names": sorted((recipe.get("parameters") or {}).keys())}
        except Exception as exc:
            row["brep_only"] = {"error": str(exc)}

    # ---- edit timings through the product API -------------------------------
    edit = {"available": None, "ok": False, "seconds": None, "param": None, "old": None,
            "new": None, "message": None}
    try:
        params_response = await client.get(f"/api/results/{job}/params")
        params = (params_response.json() or {}).get("params") or []
        p = _pick_param(params)
        if p is None:
            edit.update(available=False, message="no numeric parameter exposed")
        else:
            new = _param_new_value(p)
            if new is None:
                edit.update(available=False, message="parameter cannot move within bounds")
            else:
                edit.update(available=True, param=p.get("name"), old=p.get("value"), new=new)
                began = time.monotonic()
                response = await client.post(f"/api/results/{job}/parametrize", json={p["name"]: new})
                edit["seconds"] = round(time.monotonic() - began, 2)
                body = {}
                try:
                    body = response.json()
                except Exception:
                    pass
                edit["ok"] = bool(response.status_code == 200 and body.get("ok") and body.get("applied"))
                edit["message"] = body.get("message") or (None if edit["ok"] else f"http {response.status_code}")
    except Exception as exc:
        edit["message"] = f"harness error: {exc}"
    row["edit"] = edit

    targeted = {"available": False, "ok": False, "seconds": None, "operation": None,
                "value": None, "message": None}
    if backend != "usd-brep":
        targeted["message"] = "not_applicable: the product requires a BRep result for targeted edits"
    else:
        targets = ((result.get("diagnostics") or {}).get("selection_catalog") or {}).get("targets") or []
        if not targets:
            targeted["message"] = "not_applicable: no selectable targeted geometry in this build"
        else:
            try:
                from doodle_to_cad import targeted_edits
                target = targets[0]
                store_path = run_dir / "revisions.json"
                store = json.loads(store_path.read_text()) if store_path.exists() else {}
                began = time.monotonic()
                selection = await client.post(f"/api/results/{job}/selection", json={
                    "revision_id": "original", "target_id": target["id"],
                    "target_version": store.get("target_version", 0),
                    "selection_version": store.get("selection_version", 0)})
                if selection.status_code != 200:
                    raise RuntimeError(f"selection http {selection.status_code}: {selection.text[:200]}")
                store = json.loads(store_path.read_text())
                recipe = json.loads((cell / "model.recipe.json").read_text())
                bounds = (result.get("diagnostics") or {}).get("extents_mm")
                anchor = _rule_number(target.get("rule"), recipe)
                edit_plan = None
                for value in (round(anchor * 1.2, 2), anchor + 2, round(anchor * 0.8, 2), anchor - 1):
                    if value <= 0:
                        continue
                    try:
                        _, edit_plan = targeted_edits.plan(recipe, target["rule"], value, bounds=bounds)
                        targeted["value"] = value
                        break
                    except ValueError:
                        continue
                if edit_plan is None:
                    raise RuntimeError("no probe value produced a valid targeted plan")
                targeted["operation"] = edit_plan["operation"]
                response = await client.post(f"/api/results/{job}/revisions/targeted", json={
                    "parent_id": "original", "selection_version": store["selection_version"],
                    "operation": edit_plan["operation"], "value": targeted["value"]})
                targeted["seconds"] = round(time.monotonic() - began, 2)
                targeted["ok"] = response.status_code == 200
                if not targeted["ok"]:
                    targeted["message"] = f"http {response.status_code}: {response.text[:300]}"
            except Exception as exc:
                targeted["message"] = str(exc)[:400]
    row["targeted"] = targeted

    _finish_row(cell, row)
    _append_index(out_dir, row)
    return row


def _append_index(out_dir, row):
    with (out_dir / "index.jsonl").open("a") as handle:
        handle.write(json.dumps(row) + "\n")


async def _drive(plan, cells, out_dir, port, parallel):
    import asyncio
    import httpx
    import uvicorn
    from doodle_to_cad.app import app

    config = uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning")
    server = uvicorn.Server(config)
    task = asyncio.create_task(server.serve())
    for _ in range(100):
        if server.started:
            break
        await asyncio.sleep(0.1)
    rows = []
    try:
        async with httpx.AsyncClient(base_url=f"http://127.0.0.1:{port}", timeout=120) as client:
            health = (await client.get("/api/health")).json()
            global _SERVER_MODEL
            _SERVER_MODEL = health["agentic"]["selected_model"]
            print("server model:", _SERVER_MODEL, flush=True)
            semaphore = asyncio.Semaphore(parallel)
            jobs = []
            for item, backend, trial in cells:
                async def safe(item=item, backend=backend, trial=trial):
                    try:
                        return await _run_trial(client, plan, item, backend, trial, out_dir, semaphore)
                    except Exception as exc:  # a broken trial is evidence, not a vanished trial
                        cell = out_dir / item["id"] / backend / f"trial-{trial:02d}"
                        cell.mkdir(parents=True, exist_ok=True)
                        row = {"drawing": item["id"], "backend": backend, "trial": trial,
                               "job_status": "harness_error", "harness_error": str(exc),
                               "checks": {"overall_pass": False}}
                        _finish_row(cell, row)
                        _append_index(out_dir, row)
                        return row
                jobs.append(safe())
            rows = await asyncio.gather(*jobs)
    finally:
        server.should_exit = True
        await task
    return rows


def run_trials(argv=None):
    import argparse
    import asyncio
    import shutil
    parser = argparse.ArgumentParser(description="issue #34 backend comparison trials")
    parser.add_argument("--plan", default="docs/brep/task-17-comparison/TRIAL-PLAN.json")
    parser.add_argument("--out", default="docs/brep/task-17-comparison/runs")
    parser.add_argument("--port", type=int, default=8132)
    parser.add_argument("--parallel", type=int, default=None)
    parser.add_argument("--trials", type=int, default=None, help="override trials_per_cell")
    parser.add_argument("--cell", action="append", default=[],
                        help="restrict to drawing or drawing/backend (repeatable)")
    parser.add_argument("--fresh", action="store_true", help="discard existing rows and rerun")
    args = parser.parse_args(argv)

    assert 8130 <= args.port <= 8139, "task port range is 8130-8139"
    os.environ.setdefault("DOODLE_RESULTS_DIR", "results/task-17-comparison")

    plan_path = (ROOT / args.plan).resolve()
    plan = json.loads(plan_path.read_text())
    plan["_plan_dir"] = str(plan_path.parent)
    out_dir = ROOT / args.out
    out_dir.mkdir(parents=True, exist_ok=True)
    trials = args.trials or plan_infra(plan)["trials_per_cell"]
    parallel = args.parallel or plan_infra(plan)["concurrency"]
    wanted = set()
    for value in args.cell:
        wanted.add(value)
    cells = []
    for item in plan["corpus"]:
        for backend in ("openscad", "usd-brep"):
            if wanted and not (item["id"] in wanted or f"{item['id']}/{backend}" in wanted):
                continue
            for trial in range(1, trials + 1):
                cells.append((item, backend, trial))
    if args.fresh and wanted:
        for item in plan["corpus"]:
            if item["id"] in wanted or any(w.startswith(item["id"] + "/") for w in wanted):
                shutil.rmtree(out_dir / item["id"], ignore_errors=True)
    index = out_dir / "index.jsonl"
    if args.fresh and not wanted and index.exists():
        index.unlink()
    print(f"{len(cells)} trials planned, parallel={parallel}, port={args.port}", flush=True)
    rows = asyncio.run(_drive(plan, cells, out_dir, args.port, parallel))
    # Rebuild the index from per-trial rows so reruns leave no duplicate lines.
    with index.open("w") as handle:
        for row_path in sorted(out_dir.glob("*/*/trial-*/row.json")):
            handle.write(json.dumps(json.loads(row_path.read_text())) + "\n")
    passed = sum(1 for r in rows if (r.get("checks") or {}).get("overall_pass"))
    print(f"done: {len(rows)} rows, {passed} overall passes -> {index}", flush=True)


def plan_infra(plan):
    return plan["infrastructure"]


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "trials":
        run_trials(sys.argv[2:])
    else:
        main()
