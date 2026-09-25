from __future__ import annotations

import json
import io
import re
import shutil
import time
import uuid
import asyncio
from pathlib import Path
from typing import Any
from PIL import Image

from .config import Settings
from .geometry import analyze_image, label_view_geometry
from .evaluation import assign_view_groups, evaluate_candidate
from .design_plan import normalize_design_plan
from .preflight import preflight_scad
from .model_client import CompatibleModelClient, extract_json
from .openscad import compile_and_render, mesh_health
from .refine import refine_evidence
from .sizes import derive_physical_sizes, normalize_dimensions, uniform_scale_scad


SPEC_PROMPT = """You are the perception planner in a multi-view doodle-to-CAD system.

NON-NEGOTIABLE VIEW CONTRACT:
- The entire drawing sheet describes exactly ONE physical object.
- Spatially separated drawings are front/top/bottom/left/right projections or an isometric view of that SAME object. They are not separate parts to place beside each other.
- Reconcile the views into one consistent 3D part graph. A feature seen in multiple views is one feature with shared coordinates.
- Use the declared first-angle or third-angle projection standard to interpret view placement.
- User notes and object-type hints are authoritative. Never replace an explicit object identity with a visually fanciful guess.

GEOMETRY CONTRACT:
- Interpret imperfect strokes by design intent, regularizing near-lines, near-circles, symmetry, alignment, repetition and equal sizes.
- Closed profiles inside a containing outline are candidate holes/cutouts. For sheet metal, laser-cut, plate, bracket, grille and bookend designs, default such profiles to subtractive through-cutouts unless evidence explicitly says emboss/protrusion.
- Separate ink contours may describe attached faces of one bent or assembled object.
- OpenCV hierarchy is evidence, not absolute truth; resolve it with semantics and all views.
- OpenCV view_geometry is the quantitative geometry contract. Preserve each view's pixel aspect ratio, outer profile, and every internal profile's view-local center, size and polygon.
- Use each view's cad_mapping to convert local (u,v) coordinates into the canonical X/Y/Z frame. Never compare or transfer raw sheet coordinates between views.
- Regularize stroke noise, but do not center, align, resize, or make repeated features equal unless the measured view-local geometry supports that relation.

Return JSON only with: object, object_count (must be 1), dimensionality (flat|3d|ambiguous), projection_standard, views (each with direction, sheet region and what it constrains), manufacturing_strategy, parts, features, relations, symmetry, repetitions, dimensions, uncertainties, interpretation_conflicts, generation_notes, and construction_plan.
construction_plan must contain family (extrude|revolve|multi_face_union|loft|sweep|shell|assembled|freeform|ambiguous), operations in dependency order, and unresolved_constraints. Each operation contains id, operation, owner, profile_plane, direction_axis, parameters, and source_views. Choose a construction family only when supported by the views; otherwise use ambiguous. Respect user dimensions over visual estimates. Infer occluded details only when justified and label uncertainty."""

SCAD_PROMPT = """You are an expert mechanical designer generating ONE CAD design from multiple orthographic/isometric depictions of the same object. Create complete parametric OpenSCAD from the structured specification. Output OpenSCAD code only.

Hard requirements:
- Canonical axes are X=width, Y=front-to-back depth, Z=height.
- Plane contract: front geometry lies in XZ and front through-features cut along Y; top geometry lies in XY and cuts along Z; right geometry lies in YZ and cuts along X.
- Cameras are fixed: front looks down Y, top looks down Z, right looks down X. Never redefine these directions in comments or code.
- Never create one solid per drawing view and never lay projections out as geometry.
- Fuse views into one coherent object at a shared origin.
- Use millimetres, named parameters and modules; preserve functional parts, bends, attachments, symmetry and repetition.
- Implement every feature marked hole, slot or through_cutout subtractively with difference(); cutters must fully traverse the owning wall/plate with a small epsilon margin.
- A cutter's axis must be PERPENDICULAR to the wall it pierces: front-view openings cut along Y -> rotate([90,0,0]) before cylinder(), or use a cube whose Y side spans -eps..thickness+eps. A plain cylinder() has its axis along Z and will drill a vertical tunnel (breaking top/bottom edges) instead of a front hole. Right-view openings cut along X -> rotate([0,90,0]). Rounded slot ends need the same rotation as their slot's through-axis.
- For a through-cutter, the primitive's own axis must cross the material: use `cylinder(..., center=true)` at the hole centre, or a cube spanning from one epsilon outside the far face to the other (e.g. y from -eps to thickness+eps). A cylinder started at the near face with center=false cuts nothing.
- Connected parts must overlap enough to form the requested manifold. Do not leave floating decorations or components.
- Preserve the authoritative maximum dimension and stated manufacturing method.
- derived_sizes (when non-null) lists measured physical sizes in millimetres per axis from measured ink spans: set the top-level size parameters to exactly those values for non-null axes — they override your own pixel estimates; choose sensible proportions only for null axes.
- The part must fit a 256 x 256 x 256 mm FDM build cube (BambuLab-class). Keep all extents within it.
- The part must sit on the build plate: lowest geometry at Z=0 (do not float the solid around Z origin).
- Do not flatten a perspective object into a traced slab.
- Use only real OpenSCAD primitives. For rotational solids use rotate_extrude(), never revolve(). Use cube(), never box().
- OpenSCAD geometry/CSG/module invocations cannot be assigned to variables. Put reusable geometry in module definitions.
- measured_view_geometry is the measured truth of feature placement: for each internal profile place its opening centre at center_view_normalized (u right, v down within its view). Convert with the view's cad_mapping (front: X = u*width from the left edge, Z = (1-v)*height from the bottom; top: Y = (1-v)*depth, so v=0 at the top of the view is the BACK (+Y) of the part and increasing v moves toward the FRONT; right: Y = u*depth, so u=0 at the left of the view is the FRONT (-Y) and increasing v/up stays height). Never distribute holes evenly, centre them "for symmetry", or invent margins when measured coordinates exist.
- intent_refinements (when present) is the user's DESIGN INTENT distilled from the hand-drawn strokes and takes precedence over raw polygon tracing: model ideal_shape forms exactly — circle -> cylinder(d=...), rectangle -> cube, slot -> stadium (rounded-ends) cutter; use snapped centres and uniform sizes; build grids/patterns with nested for-loops over the reported pitch. Do not reproduce stroke wobble with polyhedron() or polygon(). Only fall back to raw measured_view_geometry polygons for profiles labelled polygon with low confidence.
- Chirality is evidence, not semantics: each view's outer_profile polygon is the silhouette truth for that axis. In the right view u=0 is the FRONT (Y=0) and u=1 the back — if the tall/thick mass sits on the left of the right view, that material belongs near Y=0, even if naming the part "back panel" feels natural. Never mirror the solid to satisfy a semantic expectation when the measured outer polygon says otherwise.
- Model exactly what the registered views show: no curvature, bevels, fillets or decoration that no view depicts (a rectangular top-view outer profile means flat faces, not a curved front). Simplicity that matches every silhouette beats invented realism.
- Prefer one explicit top-level CSG tree: a complete positive body first, followed by subtractive cutters.
- The final top-level expression must instantiate exactly one design. Never use external files or unsupported libraries."""

COMPILER_REPAIR_PROMPT = """You repair OpenSCAD compiler and empty-object failures without redesigning the part.
Return complete OpenSCAD code only. Make the smallest source change that compiles to a non-empty STL.
Preserve all dimensions, profiles, holes, slots, symmetry, modules and the intended construction family.
Use only real OpenSCAD syntax and built-ins. Use cube(), not box(); use rotate_extrude(), not revolve().
Never assign geometry or module invocations to variables. The final program must instantiate one connected design."""

SUPERVISOR_PROMPT = """You supervise a CAD synthesis loop. Diagnose the candidate against the specification, supplied drawings, rendered projections, compile log, and deterministic evaluation. Choose exactly one action:
- accept: only if geometry and required features appear faithful and the mesh is valid;
- repair_scad: preserve the interpretation but fix implementation, topology, scale, or missing features;
- reinterpret: revise the structured design when the chosen design path contradicts the drawings.
Return JSON only: {"action":"accept|repair_scad|reinterpret","problems":[...],"preserve":[...],"instructions":"concrete next-step instructions","confidence":0.0}. Never accept merely because a mesh is watertight.
Discipline: "problems" and "preserve" are short bullet strings (under 120 chars each). "instructions" is a direct command (under 120 words) stating WHAT to fix, never WHY step by step; no OpenSCAD snippets and no reasoning narration inside any string value."""

JSON_REPAIR_PROMPT = """Repair the supplied malformed JSON into one valid JSON object. Preserve its meaning and fields. Do not add analysis, markdown, comments, or code fences. Output JSON only."""


class Pipeline:
    def __init__(self, settings: Settings, client: CompatibleModelClient):
        self.settings, self.client = settings, client
        self._structured_thinking_healthy = True

    async def generate(self, image: bytes, mime: str, notes: str, dimension: str,
                       additional_views: list[tuple[str, bytes, str]] | None = None,
                       controls: dict[str, Any] | None = None,
                       run_id: str | None = None,
                       on_stage=None) -> dict[str, Any]:
        def stage(name: str) -> None:
            if on_stage:
                try: on_stage(name)
                except Exception: pass
        started = time.monotonic(); run_id = run_id or uuid.uuid4().hex[:12]
        out = self.settings.results_dir / run_id; out.mkdir(parents=True, exist_ok=False)
        suffix = ".png" if "png" in mime else ".jpg"
        (out / f"input{suffix}").write_bytes(image)
        stage("analyzing")
        evidence, overlay = await asyncio.to_thread(analyze_image, image); (out / "geometry-overlay.png").write_bytes(overlay)
        additional_views, controls = additional_views or [], controls or {}
        assigned_views=assign_view_groups(evidence,controls.get("primary_view","front"),controls.get("projection_standard","third-angle"))
        evidence=label_view_geometry(evidence,assigned_views)
        derived_sizes = derive_physical_sizes(evidence, dimension)
        if derived_sizes: (out / "derived-sizes.json").write_text(json.dumps(derived_sizes, indent=2))
        user_text = f"User description: {notes or '(none)'}\nAuthoritative maximum dimension: {dimension or '(none supplied)'}\nControls: {json.dumps(controls)}\nOpenCV evidence: {json.dumps(evidence)}"
        visual_content: list[dict[str, Any]] = [
            {"type":"text","text":user_text},
            {"type":"text","text":"FULL DRAWING SHEET (spatial layout identifies projection views; it is not physical geometry):"},
            {"type":"image_url","image_url":{"url":self.client.image_url(image,mime)}},
        ]
        registered = self._registered_view_crops(image,evidence,controls,out)
        for direction, crop in registered.items():
            visual_content.extend([
                {"type":"text","text":(
                    f"REGISTERED {direction.upper()} ORTHOGRAPHIC VIEW CROP. This is a projection of the same object. "
                    "Its position on the sheet is not a physical offset, attachment, or separate part."
                )},
                {"type":"image_url","image_url":{"url":self.client.image_url(crop,"image/png")}},
            ])
        for direction, view_data, view_mime in additional_views:
            visual_content.extend([{"type":"text","text":f"ADDITIONAL ORTHOGRAPHIC VIEW ({direction}):"},{"type":"image_url","image_url":{"url":self.client.image_url(view_data,view_mime)}}])
        messages = [{"role":"system","content":SPEC_PROMPT},{"role":"user","content":visual_content}]
        stage("interpreting")
        spec = await self._json_call(messages,out,"interpretation")
        spec["object_count"] = 1
        spec["user_intent"] = {"description": notes, "object_type_hint": controls.get("object_type_hint", ""), "authoritative_max_dimension_mm": dimension}
        spec["source_view_group_count"] = evidence.get("view_group_count", 1)
        spec["multi_view_contract"] = "All source views constrain one shared physical object; never instantiate views as separate geometry."
        spec["cutout_policy"] = "Closed internal profiles are subtractive through-cutouts unless explicitly classified otherwise."
        spec["construction_plan"] = normalize_design_plan(spec)
        spec["dimensions"] = normalize_dimensions(spec.get("dimensions"))
        if derived_sizes:
            # Measured-ink sizes are ground truth for the axes the views
            # constrain; the LLM's pixel-peeped estimates stay only for axes no
            # view pins down (e.g. depth from a single front sketch). The
            # evaluator's shape gate reads exactly these keys.
            dims = dict(spec["dimensions"])
            for key, value in (("max_width", derived_sizes["width_mm"]),
                               ("max_depth", derived_sizes["depth_mm"]),
                               ("max_height", derived_sizes["height_mm"])):
                if value is not None:
                    dims[key] = value
            dims["size_provenance"] = "measured ink spans x authoritative max dimension"
            spec["dimensions"] = dims
        (out / "sketch-spec.json").write_text(json.dumps(spec,indent=2))
        generation_input = {"design_contract": {"object_count": 1, "views_are_constraints_not_parts": True, "projection_standard": controls.get("projection_standard"), "strict_watertight": controls.get("strict_watertight"), "method": controls.get("method")}, "specification": spec,
                            "measured_view_geometry": {"coordinate_contract": evidence.get("coordinate_contract"), "views": evidence.get("view_geometry", [])},
                            "intent_refinements": refine_evidence(evidence, controls.get("refine_mode", "regularize")),
                            "derived_sizes": derived_sizes}
        strict = bool(controls.get("strict_watertight", True))
        stage("generating")
        scad = await self._scad_call(
            [{"role":"system","content":SCAD_PROMPT},{"role":"user","content":json.dumps(generation_input,indent=2)}],
            out, "generation", temperature=.1,
        )
        attempts = []; best = None; next_action = "generate"
        for number in range(1, self.settings.agent_max_attempts + 1):
            attempt_dir = out / f"attempt-{number:02d}"; attempt_dir.mkdir()
            compiler_repairs=[]
            while True:
                scad_path = attempt_dir / "model.scad"; scad_path.write_text(scad)
                stage(f"compiling (attempt {number})")
                preflight=preflight_scad(scad,spec)
                if preflight["passed"]:
                    stl,views,log=await asyncio.to_thread(compile_and_render,scad_path,attempt_dir,self.settings.openscad_bin)
                else: stl,views,log=None,{},"PREFLIGHT: "+"; ".join(preflight["errors"])
                if stl or len(compiler_repairs) >= self.settings.code_validation_repairs:
                    break
                repair_number=len(compiler_repairs)+1
                failed_name=f"compiler-repair-{repair_number:02d}.failed.scad"
                (attempt_dir/failed_name).write_text(scad)
                failure={"repair":repair_number,"preflight":preflight,"compile_log":log,"failed_scad":failed_name}
                compiler_repairs.append(failure)
                compiler_input=(
                    "Repair this candidate using the exact validation failure below. Do not redesign it.\n"
                    f"PREFLIGHT: {json.dumps(preflight)}\nCOMPILER: {log[-3000:]}\n"
                    f"SPECIFICATION: {json.dumps(spec)}\nCODE:\n{scad}"
                )
                scad=await self._scad_call(
                    [{"role":"system","content":COMPILER_REPAIR_PROMPT},{"role":"user","content":compiler_input}],
                    attempt_dir,f"compiler-repair-{repair_number:02d}",temperature=0,
                )
            health = await asyncio.to_thread(mesh_health, stl) if stl else None
            # Deterministic size clamp: when the compiled max extent misses the
            # authoritative target by >5%, uniformly scale the named size
            # parameters and recompile (no LLM). Verified empirically — keep
            # the scaled variant only if it measurably improves the miss, so
            # partially-parameterised models can never be made worse.
            scale_applied = None
            try: target_mm = float(dimension)
            except (TypeError, ValueError): target_mm = None
            if stl and health and target_mm and target_mm > 0:
                actual_max = max(health["extents_mm"])
                miss = abs(actual_max - target_mm) / target_mm
                if actual_max > 0 and miss > 0.05:
                    scaled_scad, applied = uniform_scale_scad(scad, target_mm / actual_max)
                    if applied:
                        scaled_dir = attempt_dir / "uniform-scaled"; scaled_dir.mkdir(exist_ok=True)
                        scaled_path = scaled_dir / "model.scad"; scaled_path.write_text(scaled_scad)
                        s_stl, s_views, s_log = await asyncio.to_thread(compile_and_render, scaled_path, scaled_dir, self.settings.openscad_bin)
                        s_health = await asyncio.to_thread(mesh_health, s_stl) if s_stl else None
                        if s_stl and s_health and s_health["extents_mm"]:
                            s_miss = abs(max(s_health["extents_mm"]) - target_mm) / target_mm
                            if s_miss < miss:
                                scad, stl, views, health, log = scaled_scad, s_stl, s_views, s_health, s_log
                                scale_applied = {"factor": round(target_mm / actual_max, 4), "before_max_mm": actual_max,
                                                 "after_max_mm": max(s_health["extents_mm"]), "params": applied}
            evaluation = await asyncio.to_thread(
                evaluate_candidate, stl=stl, health=health, scad=scad, views=views, source=image,
                evidence=evidence, spec=spec, target_dimension=dimension, strict=strict,
                primary_view=controls.get("primary_view","front"),
                projection_standard=controls.get("projection_standard","third-angle"))
            evaluation["accepted"] = bool(evaluation["accepted"] and evaluation["score"] >= self.settings.agent_accept_score)
            def _rel(path: Path | None) -> str | None:
                return path.relative_to(out).as_posix() if path else None
            record = {"attempt":number,"action":next_action,"preflight":preflight,"compiler_repairs":compiler_repairs,"uniform_scale":scale_applied,"evaluation":evaluation,"mesh_health":health,
                      "compile_log":log,"files":{"scad":_rel(attempt_dir/"model.scad"),"stl":_rel(stl),
                      "views":{k:_rel(v) for k,v in views.items()}}}
            candidate_rank=(sum(evaluation.get("mandatory_gates",{}).values()),evaluation["score"])
            best_rank=(-1,-1) if best is None else (sum(best["record"]["evaluation"].get("mandatory_gates",{}).values()),best["record"]["evaluation"]["score"])
            attempts.append(record); (attempt_dir/"evaluation.json").write_text(json.dumps(record,indent=2))
            if best is None or candidate_rank > best_rank:
                best = {"record":record,"dir":attempt_dir,"stl":stl,"views":views,"scad":scad,"health":health,"log":log}
            if evaluation["accepted"]: break
            if number >= self.settings.agent_max_attempts: break
            stage(f"supervising (attempt {number})")
            diagnosis_content: list[dict[str,Any]] = [{"type":"text","text":json.dumps({"specification":spec,"preflight":preflight,"evaluation":evaluation,"mesh_health":health,"compile_log":log[-2500:],"scad":scad},indent=2)},
                {"type":"text","text":"ORIGINAL DRAWING:"},{"type":"image_url","image_url":{"url":self.client.image_url(image,mime)}}]
            for name,path in views.items(): diagnosis_content.extend([{"type":"text","text":f"CANDIDATE {name.upper()}:"},{"type":"image_url","image_url":{"url":self.client.image_url(path.read_bytes(),'image/png')}}])
            try:
                diagnosis = await asyncio.wait_for(
                    self._json_call([{"role":"system","content":SUPERVISOR_PROMPT},{"role":"user","content":diagnosis_content}],attempt_dir,"supervisor",temperature=0),
                    timeout=self.settings.supervisor_timeout,
                )
            except Exception as exc:
                # A dead supervisor must not end the repair loop: the deterministic
                # gate failures already say what is wrong, so fall back to a
                # repair_scad directive built from them.
                failure={"stage":"supervisor","error_type":type(exc).__name__,"error":str(exc),"recovery":"deterministic_repair_directive"}
                record["supervisor_failure"]=failure
                (attempt_dir/"supervisor.failure.json").write_text(json.dumps(failure,indent=2))
                diagnosis={"action":"repair_scad","problems":evaluation["failures"],
                           "preserve":[g for g,p in evaluation["mandatory_gates"].items() if p],
                           "instructions":"Fix exactly these failing gates without regressing passing ones: "+"; ".join(evaluation["failures"]),
                           "confidence":0.0,"fallback":True}
                (attempt_dir/"evaluation.json").write_text(json.dumps(record,indent=2))
            record["supervisor"] = diagnosis; (attempt_dir/"evaluation.json").write_text(json.dumps(record,indent=2))
            next_action = diagnosis.get("action", "repair_scad")
            if next_action == "accept" and evaluation["accepted"]: break
            stagnant = len(attempts) > 1 and evaluation["failures"] == attempts[-2]["evaluation"]["failures"] and abs(evaluation["score"]-attempts[-2]["evaluation"]["score"]) < .5
            if stagnant:
                next_action = "regenerate_scad"
                record["supervisor"]["action"] = next_action
                record["supervisor"]["instructions"] = "Previous repair made no measurable progress. Regenerate cleanly from the specification and mandatory gate failures using a different construction strategy."
                fresh_input={**generation_input,"previous_candidate_failures":evaluation["failures"],"require_different_construction":True}
                scad=await self._scad_call(
                    [{"role":"system","content":SCAD_PROMPT},{"role":"user","content":json.dumps(fresh_input,indent=2)}],
                    attempt_dir, "regeneration", temperature=.15,
                )
                continue
            if next_action == "reinterpret":
                revised_content = visual_content + [{"type":"text","text":f"Revise the previous specification using this supervisor diagnosis.\nPREVIOUS SPEC:\n{json.dumps(spec)}\nDIAGNOSIS:\n{json.dumps(diagnosis)}"}]
                spec = await self._json_call([{"role":"system","content":SPEC_PROMPT},{"role":"user","content":revised_content}],attempt_dir,"reinterpretation",temperature=0)
                spec["object_count"] = 1; generation_input["specification"] = spec
                scad = await self._scad_call(
                    [{"role":"system","content":SCAD_PROMPT},{"role":"user","content":json.dumps(generation_input,indent=2)}],
                    attempt_dir, "reinterpretation-generation", temperature=.05,
                )
            else:
                passing=[name for name,passed in evaluation.get("mandatory_gates",{}).items() if passed]
                repair_content = [{"type":"text","text":f"Repair this candidate according to the diagnosis and evaluation. Preserve every required feature.\nPRESERVATION CONTRACT: These gates already pass and must not regress: {json.dumps(passing)}. Preserve the current bounding box and valid mesh unless a failing dimension explicitly requires changing it. Do not replace a working base solid while repairing cutters or projections.\nDIAGNOSIS: {json.dumps(diagnosis)}\nEVALUATION: {json.dumps(evaluation)}\nSPEC: {json.dumps(spec)}\nCODE:\n{scad}"}]
                for name,path in views.items(): repair_content.extend([{"type":"text","text":f"CURRENT {name.upper()}:"},{"type":"image_url","image_url":{"url":self.client.image_url(path.read_bytes(),'image/png')}}])
                scad = await self._scad_call(
                    [{"role":"system","content":SCAD_PROMPT},{"role":"user","content":repair_content}],
                    attempt_dir, "repair", temperature=0,
                )
        assert best is not None
        stage("finalizing")
        selected = best["record"]; scad = best["scad"]; health = best["health"]; log = best["log"]
        (out/"model.scad").write_text(scad)
        if best["stl"]: shutil.copy2(best["stl"],out/"model.stl")
        views = {}
        for name,path in best["views"].items():
            target=out/path.name; shutil.copy2(path,target); views[name]=target
        stl = out/"model.stl" if (out/"model.stl").exists() else None
        (out/"attempts.json").write_text(json.dumps(attempts,indent=2))
        repaired = len(attempts) > 1
        model = await self.client.discover()
        passed_mesh_gate = bool(selected["evaluation"]["accepted"])
        result = {"id":run_id,"success":passed_mesh_gate,"model":model.selected,"model_source":model.source,"base_url":self.settings.base_url,"spec":spec,"geometry":evidence,"mesh_health":health,"evaluation":selected["evaluation"],"selected_attempt":selected["attempt"],"attempts":attempts,"controls":controls,"additional_view_count":len(additional_views),"repaired":repaired,"compile_log":log,"duration_seconds":round(time.monotonic()-started,2),"files":{"scad":f"/results/{run_id}/model.scad","stl":f"/results/{run_id}/model.stl" if stl else None,"attempts":f"/results/{run_id}/attempts.json","overlay":f"/results/{run_id}/geometry-overlay.png","views":{k:f"/results/{run_id}/{v.name}" for k,v in views.items()}}}
        (out/"result.json").write_text(json.dumps(result,indent=2)); return result

    @staticmethod
    def _clean_scad(text: str) -> str:
        text=text.strip(); text=re.sub(r"^```(?:openscad|scad)?\s*", "", text, flags=re.I); text=re.sub(r"\s*```$", "", text)
        if not text or "module" not in text and not any(x in text for x in ("cube(","cylinder(","sphere(","polyhedron(","linear_extrude(","rotate_extrude(")):
            raise ValueError("Model did not return recognizable OpenSCAD")
        return text.strip()+"\n"

    @staticmethod
    def _registered_view_crops(image:bytes,evidence:dict[str,Any],controls:dict[str,Any],output_dir:Path)->dict[str,bytes]:
        assigned=assign_view_groups(
            evidence,
            controls.get("primary_view","front"),
            controls.get("projection_standard","third-angle"),
        )
        if not assigned:
            return {}
        source=Image.open(io.BytesIO(image)).convert("RGB"); width,height=source.size
        crops={}
        for direction,group in assigned.items():
            x,y,w,h=group.get("bbox_normalized",[0,0,1,1]); pad=.015
            box=(max(0,int((x-pad)*width)),max(0,int((y-pad)*height)),
                 min(width,int((x+w+pad)*width)),min(height,int((y+h+pad)*height)))
            cropped=source.crop(box); buffer=io.BytesIO(); cropped.save(buffer,format="PNG")
            data=buffer.getvalue(); crops[direction]=data
            (output_dir/f"registered-{direction}.png").write_bytes(data)
        return crops

    async def _json_call(self,messages:list[dict[str,Any]],output_dir:Path,label:str,temperature:float=.15)->dict[str,Any]:
        try:
            raw=await self.client.chat(
                messages,
                temperature=temperature,
                enable_thinking=(
                    True if self.settings.structured_enable_thinking and self._structured_thinking_healthy
                    else False
                ),
            )
            (output_dir/f"{label}.raw.txt").write_text(raw)
        except Exception as exc:
            self._structured_thinking_healthy = False
            first_failure={"stage":label,"error_type":type(exc).__name__,"error":str(exc),"recovery":"retry_without_thinking"}
            (output_dir/f"{label}.thinking-failure.json").write_text(json.dumps(first_failure,indent=2))
            raw=None; last_exc=None
            for try_no in range(1, max(1, self.settings.transport_retries + 1) + 1):
                try:
                    raw=await self.client.chat(
                        messages,temperature=temperature,enable_thinking=False,
                        max_tokens=self.settings.max_tokens,
                    )
                    (output_dir/f"{label}.fallback.raw.txt").write_text(raw)
                    break
                except Exception as fallback_exc:
                    last_exc=fallback_exc
                    transport=type(fallback_exc).__name__ in {"ReadTimeout","ConnectError","ConnectTimeout","PoolTimeout","RemoteProtocolError"}
                    if not transport or try_no > self.settings.transport_retries:
                        raise RuntimeError(
                            f"{label} failed with thinking ({type(exc).__name__}: {exc}) and direct-output retry "
                            f"also failed ({type(fallback_exc).__name__}: {fallback_exc})"
                        ) from fallback_exc
                    await asyncio.sleep(3 * try_no)
        try:
            return extract_json(raw)
        except (ValueError,json.JSONDecodeError) as exc:
            (output_dir/f"{label}.parse-error.txt").write_text(str(exc)+"\n")
            repair_messages=[{"role":"system","content":JSON_REPAIR_PROMPT},{"role":"user","content":raw}]
            repaired=await self.client.chat(repair_messages,temperature=0,enable_thinking=False,max_tokens=min(self.settings.max_tokens,4096))
            (output_dir/f"{label}.repaired.txt").write_text(repaired)
            try:
                return extract_json(repaired)
            except (ValueError,json.JSONDecodeError) as repair_exc:
                raise ValueError(f"{label} returned malformed JSON and repair failed: {repair_exc}") from repair_exc

    async def _scad_call(self,messages:list[dict[str,Any]],output_dir:Path,label:str,temperature:float=.1)->str:
        """Generate SCAD with a distinct reasoning policy and durable diagnostics."""
        attempts = max(1, self.settings.transport_retries + 1)
        last_exc: Exception | None = None
        for try_no in range(1, attempts + 1):
            try:
                raw = await self.client.chat(
                    messages,
                    temperature=temperature,
                    enable_thinking=self.settings.code_enable_thinking,
                    max_tokens=self.settings.code_max_tokens,
                )
                (output_dir/f"{label}.raw.scad.txt").write_text(raw)
                return self._clean_scad(raw)
            except Exception as exc:
                last_exc = exc
                transport = type(exc).__name__ in {"ReadTimeout","ConnectError","ConnectTimeout","PoolTimeout","RemoteProtocolError"}
                (output_dir/f"{label}.failure-{try_no:02d}.json").write_text(json.dumps({
                    "stage": label, "attempt": try_no, "error_type": type(exc).__name__, "error": str(exc),
                    "transport": transport,
                    "code_thinking_enabled": self.settings.code_enable_thinking,
                    "code_max_tokens": self.settings.code_max_tokens}, indent=2))
                if not transport or try_no >= attempts:
                    break
                await asyncio.sleep(3 * try_no)
        raise RuntimeError(
            f"CAD code generation failed at '{label}' ({type(last_exc).__name__}): {last_exc}"
        ) from last_exc
