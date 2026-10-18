"""Targeted post-generation repair for OpenSCAD results ("this part is close").

The user describes ONE correction; the model edits the currently displayed
source in place instead of redesigning. Every attempt produces either a
separate candidate revision (never the displayed version) or an explained
failure that leaves the last valid result untouched.

Trust model:
- The candidate is built from the DISPLAYED version: the caller supplies the
  source URL the browser is showing (an ``edited-*.scad`` produced by a
  successfully applied parameter edit, or the revision's own source). The URL
  must resolve inside the run directory, so an original generation or a
  foreign path can never be smuggled in.
- The original generation score is never carried over: a repair candidate is
  explicitly ``evaluation.status = "unverified"`` until the generation
  evaluation has actually been rerun.
- Publishing re-checks the selection counter after the model/build work, so a
  stale repair cannot overwrite a newer keep.

Measured checks (deterministic, trimesh-backed) vs visual review:
compilation, watertightness, connected component count, per-axis extents and
editable parameter values are measured; whether the requested correction is
semantically achieved stays ``unverified`` and the model's interpretation is
displayed for review next to the screenshots.
"""
from __future__ import annotations

import asyncio
import json
import time
import uuid
from pathlib import Path
from typing import Any

from fastapi import HTTPException

from .build_contract import BuildInput, build
from .params import extract_params

PROMPT_VERSION = 1

# Documented preservation tolerances (see also benchmarks/brep-baseline/wheel
# /manifest.json generated_dimension_relative = 0.02). An extent is preserved
# when it agrees within the relative tolerance OR the absolute allowance.
PRESERVATION_TOLERANCES = {
    "extent_relative": 0.02,
    "extent_abs_mm": 0.5,
    "editable_parameter_values": "exact; any change is listed for review",
    "volume_relative_informational": 0.25,
}

REPAIR_PROMPT = """You make ONE targeted correction to an existing OpenSCAD model. The user says what to change; everything else must survive byte-for-byte in spirit.
Hard rules:
- Implement exactly the stated correction and nothing else. Do not redesign, restyle, simplify, optimise or "improve" anything the correction does not mention.
- Keep every top-level parameter name, value and unit the correction does not require you to touch, keep all modules and comments, and keep the /* doodle-meta */ JSON comment (update only the metadata entries the correction legitimately changes).
- Do not rename parameters, do not add new top-level parameters unless the correction demands it, and do not change the construction family.
- Bridging disconnected material needs real overlap: extend geometry INTO the mating part (by >= 1 mm) before union(); a plain union of gapped solids does not connect anything.
- Preserve unmentioned bounding extents and feature counts within a few percent.
- Use only real OpenSCAD built-ins; cube(), not box(); rotate_extrude(), not revolve().
- Output the complete corrected program as OpenSCAD code only: no markdown fences, no commentary, no questions."""

INTERPRET_PROMPT = """You plan one targeted repair of a CAD model from the user's correction sentence. Distinguish the requested change from the properties the user expects to remain unchanged. Only list properties the user stated or the supplied diagnostics make explicit; never invent requirements.
Return JSON only: {"requested_change": "<one sentence>", "preserve": ["<property to keep>", ...], "expected_evidence": ["<measurable outcome proving the change>", ...]}"""


def _url_for(out: Path, path: Path) -> str:
    return f"/results/{out.name}/{path.relative_to(out).as_posix()}"


def _resolve_displayed(out: Path, url: str | None, suffixes: tuple[str, ...], field: str) -> Path | None:
    """Map a displayed-file URL to a real path strictly inside the run dir."""
    if not url:
        return None
    path_part = url.split("?", 1)[0]
    prefix = f"/results/{out.name}/"
    if not path_part.startswith(prefix):
        raise HTTPException(422, {"message": f"displayed.{field} must be a file of this run", "code": "invalid_input"})
    target = (out / path_part[len(prefix):]).resolve()
    if out.resolve() not in target.parents:
        raise HTTPException(422, {"message": f"displayed.{field} escapes the run directory", "code": "invalid_input"})
    if not target.is_file() or target.suffix not in suffixes:
        raise HTTPException(422, {"message": f"displayed.{field} does not match an existing file of this run", "code": "invalid_input"})
    return target


def mesh_diagnostics(stl: Path | None) -> dict[str, Any] | None:
    """Measured mesh state; None when no STL exists to measure."""
    if stl is None or not Path(stl).is_file():
        return None
    from .openscad import mesh_health
    try:
        return mesh_health(Path(stl))
    except Exception:
        return None


def build_candidate(out: Path, scad_text: str, candidate_dir: Path, binary: str):
    """Compile one repair candidate. Seam for tests; keeps the failed source."""
    candidate_dir.mkdir(parents=True, exist_ok=True)
    source = candidate_dir / "model.scad"
    source.write_text(scad_text)
    return build(BuildInput("openscad", source, candidate_dir), binary)


def _param_values(text: str) -> dict[str, float]:
    return {p.name: p.value for p in extract_params(text)}


def _params_list(text: str) -> list[dict[str, Any]]:
    return [p.to_dict() for p in extract_params(text)]


def preservation_checks(before: dict | None, after: dict | None,
                        before_params: dict[str, float], after_params: dict[str, float]) -> list[dict[str, Any]]:
    """Deterministic before/after checks with documented tolerances."""
    checks: list[dict[str, Any]] = []
    if after is None:
        return checks
    checks.append({"name": "watertight", "status": "passed" if after.get("watertight") else "failed",
                   "before": None if before is None else before.get("watertight"), "after": after.get("watertight")})
    components_after = after.get("components")
    components_before = None if before is None else before.get("components")
    if components_after == 1:
        status = "passed"
    elif components_before is not None and components_after is not None and components_after < components_before:
        status = "improved"
    elif components_before is not None and components_after is not None and components_after > components_before:
        status = "regressed"
    else:
        status = "unchanged"
    checks.append({"name": "connected_components", "status": status,
                   "before": components_before, "after": components_after,
                   "note": "passed means one connected component; separate from watertightness"})
    tol = PRESERVATION_TOLERANCES
    if before is not None and before.get("extents_mm") and after.get("extents_mm"):
        drift = []
        for axis, (a, b) in enumerate(zip(before["extents_mm"], after["extents_mm"])):
            ok = abs(a - b) <= max(tol["extent_abs_mm"], tol["extent_relative"] * max(abs(a), abs(b)))
            if not ok:
                drift.append({"axis": "xyz"[axis], "before": a, "after": b})
        checks.append({"name": "extents_preserved", "status": "passed" if not drift else "failed",
                       "before": before["extents_mm"], "after": after["extents_mm"], "drift": drift,
                       "tolerances": {"extent_relative": tol["extent_relative"], "extent_abs_mm": tol["extent_abs_mm"]}})
    else:
        checks.append({"name": "extents_preserved", "status": "unverified", "after": after.get("extents_mm"),
                       "note": "No measured mesh for the displayed version to compare against."})
    changed = sorted(name for name in set(before_params) | set(after_params)
                     if before_params.get(name) != after_params.get(name))
    checks.append({"name": "editable_parameters_preserved", "status": "passed" if not changed else "reported",
                   "changed": changed, "before": before_params, "after": after_params,
                   "note": "changed parameters are allowed only when the correction requires them"})
    if before is not None and before.get("volume_mm3") and after.get("volume_mm3"):
        ratio = after["volume_mm3"] / before["volume_mm3"]
        checks.append({"name": "volume_change", "status": "measured", "before": before["volume_mm3"],
                       "after": after["volume_mm3"], "ratio": round(ratio, 4)})
    checks.append({"name": "requested_correction", "status": "unverified",
                   "note": "Needs visual inspection of the preview plus the model interpretation below."})
    return checks


def _read_instruction(payload: dict) -> str:
    instruction = payload.get("instruction")
    if type(instruction) is not str or not instruction.strip():
        raise HTTPException(422, {"message": "Repair requires a non-empty correction instruction.", "code": "invalid_input"})
    if len(instruction) > 2000:
        raise HTTPException(422, {"message": "Correction instruction exceeds 2000 characters.", "code": "invalid_input"})
    return instruction.strip()


async def repair_preview(pipeline: Any, settings: Any, out: Path, payload: dict) -> dict[str, Any]:
    """Build a separate repair candidate revision from the displayed version.

    Never mutates the selection: the candidate only becomes current through
    the existing keep endpoint (selection counter re-checked after the build).
    """
    allowed = {"parent_id", "selection_version", "instruction", "displayed"}
    if not set(payload) <= allowed or set(payload) < {"parent_id", "selection_version", "instruction"}:
        raise HTTPException(422, {"message": "Repair requires parent_id, selection_version and instruction.", "code": "invalid_input"})
    from . import revisions
    instruction = _read_instruction(payload)
    displayed = payload.get("displayed") or {}
    if not isinstance(displayed, dict) or not set(displayed) <= {"source", "stl"}:
        raise HTTPException(422, {"message": "displayed must be an object with source/stl URLs.", "code": "invalid_input"})
    with revisions.locked(out):
        store = revisions.read_store(out)
        revisions.selection_matches(store, payload["selection_version"])
        parent = {k: v for k, v in revisions.record(store, payload["parent_id"]).items()}
    if parent["result"].get("backend") != "openscad":
        raise HTTPException(422, {"message": "Targeted repair currently requires an OpenSCAD result.", "code": "invalid_input"})

    source_path = _resolve_displayed(out, displayed.get("source"), (".scad",), "source")
    started_from = "displayed-parameter-edit" if source_path and source_path.name != "model.scad" else "parent-revision"
    source_text = source_path.read_text() if source_path else parent["source_text"]
    if not source_text or not source_text.strip():
        raise HTTPException(422, {"message": "The displayed version has no source to repair.", "code": "invalid_input"})
    stl_path = _resolve_displayed(out, displayed.get("stl"), (".stl",), "stl")
    if stl_path is None:
        stl_url = (parent["result"].get("files") or {}).get("stl")
        stl_path = _resolve_displayed(out, stl_url, (".stl",), "stl")

    before_mesh = await asyncio.to_thread(mesh_diagnostics, stl_path)
    before_params = _param_values(source_text)
    candidate_dir = out / f"repair-{uuid.uuid4().hex[:8]}"
    candidate_dir.mkdir(parents=True, exist_ok=True)  # model-call raw artifacts land here from the first call
    drawing = None
    for name in ("input.png", "input.jpg"):
        if (out / name).is_file():
            drawing = (out / name).read_bytes()
            break

    started = time.monotonic()
    interpretation: dict[str, Any] | None = None
    interpretation_failure: dict[str, str] | None = None
    try:
        content: list[dict[str, Any]] = [{"type": "text", "text": json.dumps(
            {"correction": instruction, "object": parent["result"].get("spec", {}).get("object"),
             "editable_parameters": before_params,
             "current_mesh_diagnostics": before_mesh}, indent=2)}]
        if drawing:
            content.append({"type": "text", "text": "ORIGINAL DRAWING:"})
            content.append({"type": "image_url", "image_url": {"url": pipeline.client.image_url(drawing, "image/png")}})
        interpretation = await pipeline._json_call(
            [{"role": "system", "content": INTERPRET_PROMPT}, {"role": "user", "content": content}],
            candidate_dir, "repair-interpretation", temperature=0)
        if not isinstance(interpretation, dict) or set(interpretation) < {"requested_change", "preserve"}:
            raise ValueError("interpretation missing requested_change/preserve")
    except Exception as exc:  # interpretation is advisory; the repair may continue
        interpretation_failure = {"error_type": type(exc).__name__, "error": str(exc)[:500]}
        interpretation = None

    repair_content: list[dict[str, Any]] = [{"type": "text", "text": json.dumps({
        "correction_contract": {"requested_change": instruction,
                                "model_interpretation": interpretation,
                                "rule": "change only what the correction describes"},
        "original_specification": parent["result"].get("spec"),
        "editable_parameters": before_params,
        "current_mesh_diagnostics": before_mesh,
        "tolerances": PRESERVATION_TOLERANCES}, indent=2)},
        {"type": "text", "text": f"CURRENT CODE (from the displayed version):\n{source_text}"}]
    if drawing:
        repair_content.append({"type": "text", "text": "ORIGINAL DRAWING:"})
        repair_content.append({"type": "image_url", "image_url": {"url": pipeline.client.image_url(drawing, "image/png")}})
    try:
        candidate_scad = await pipeline._scad_call(
            [{"role": "system", "content": REPAIR_PROMPT}, {"role": "user", "content": repair_content}],
            candidate_dir, "repair", temperature=0)
    except Exception as exc:
        failure = {"stage": "model", "error_type": type(exc).__name__, "error": str(exc)[:1000]}
        candidate_dir.mkdir(parents=True, exist_ok=True)
        (candidate_dir / "repair.json").write_text(json.dumps(
            {"failed": failure, "started_from": started_from, "instruction": instruction}, indent=2))
        raise HTTPException(422, {"message": f"The repair model call failed. The displayed version is unchanged. {failure['error_type']}: {failure['error']}",
                                  "code": "model_failure", "candidate_dir": _url_for(out, candidate_dir)}) from exc

    built = await asyncio.to_thread(build_candidate, out, candidate_scad, candidate_dir, settings.openscad_bin)
    after_mesh = await asyncio.to_thread(mesh_diagnostics, candidate_dir / "model.stl") if built.stl else None
    after_params = _param_values(candidate_scad)
    checks = [{"name": "compiles", "status": "passed" if built.stl else "failed",
               "compile_seconds": round(time.monotonic() - started, 2)}]
    if not built.stl:
        failure = {"stage": "compile", "error": (built.log or "OpenSCAD produced no STL")[-2000:]}
        checks[0]["detail"] = failure["error"]
        (candidate_dir / "repair.json").write_text(json.dumps({
            "failed": failure, "started_from": started_from, "instruction": instruction,
            "interpretation": interpretation, "checks": checks, "prompt_version": PROMPT_VERSION}, indent=2))
        raise HTTPException(422, {"message": "The repair candidate did not compile. The displayed version is unchanged — revise the instruction.",
                                  "code": "build_failed", "compile_log": failure["error"],
                                  "failed_scad": _url_for(out, candidate_dir / "model.scad")})
    checks += preservation_checks(before_mesh, after_mesh, before_params, after_params)
    repair_record = {
        "instruction": instruction, "parent_id": parent["id"], "started_from": started_from,
        "interpretation": interpretation, "interpretation_failure": interpretation_failure,
        "checks": checks, "diagnostics": {"before": before_mesh, "after": after_mesh},
        "tolerances": PRESERVATION_TOLERANCES, "prompt_version": PROMPT_VERSION,
        "model": pipeline.settings.requested_model or None,
        "score_carried_from_generation": False,
    }
    (candidate_dir / "repair.json").write_text(json.dumps(repair_record, indent=2))

    result = json.loads(json.dumps(parent["result"]))
    result.update(
        success=False,
        files={"scad": _url_for(out, candidate_dir / "model.scad"),
               "source": _url_for(out, candidate_dir / "model.scad"),
               "stl": _url_for(out, candidate_dir / "model.stl"),
               "views": {k: _url_for(out, v) for k, v in built.views.items()},
               "repair": _url_for(out, candidate_dir / "repair.json")},
        build=built.metadata(),
        evaluation={"status": "unverified", "accepted": False, "score": None,
                    "failures": ["The original generation acceptance score was not rerun for this repair candidate."]},
        repair=repair_record)
    revision_id = uuid.uuid4().hex
    item = {"id": revision_id, "parent_id": parent["id"], "kind": "repair", "result": result,
            "source_text": candidate_scad, "parameters": _params_list(candidate_scad),
            "instruction": instruction}
    with revisions.locked(out):
        store = revisions.read_store(out)
        revisions.selection_matches(store, payload["selection_version"])
        store["revisions"][revision_id] = item
        revisions.write_store(out, store)
        return revisions.result_for(store, revision_id)
