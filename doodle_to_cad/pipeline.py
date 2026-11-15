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


SPEC_PROMPT = """You are a principal mechanical engineer and industrial designer in a doodle-to-CAD system for FDM 3D printing.

CORE PRODUCT PHILOSOPHY (THE DOODLE IS A 3D DESIGN SEED, NOT A 2D COOKIE-CUTTER):
- Unless multiple explicit orthographic drafting views of a flat sheet-metal plate are drawn, treat the user's doodle as a creative seed for a TRUE 3D VOLUMETRIC, MECHANICALLY FUNCTIONAL, FDM 3D-PRINTABLE ASSEMBLY made of 3 distinct printable parts (dimensionality = "3d").
- NEVER interpret a 3D physical object as a flat 2D/2.5D extruded plaque or relief token.
- Infer the real-world 3D depth, round/tubular/domed cross-sections, and inherent mechanical movements or modular assembly joints that make the object an appealing, functional 3D-printed product:
  1. Decompose the object into 3 distinct, functional 3D-printable parts (which may include paired sub-elements such as a symmetric rotating pair, giving 3 to 5 watertight solids in the STL).
  2. Engineer real mechanical joints or couplings between the 3 parts (e.g., rotating axles in bores, pivoting shafts in sleeves, ball-and-socket or pin-and-socket joints, detachable multi-stage collars/tenons, or a weighted freestanding support base + 3D structural frame/column + posable/removable 3D head/module).
  3. Specify an explicit FDM clearance gap (`clearance_mm`: 0.5 to 0.6 mm) at every joint so the parts assemble/move smoothly and remain separate watertight solids in the compiled mesh.
  4. Design for FDM printability: ensure stable bed contact at Z=0 (add a 3D support base/stand or stable contact elements touching Z=0 if the object would otherwise tip over), self-supporting angles, and sturdy cross-sections (>= 4 mm diameter for shafts/axles/columns).

Return JSON only with:
- object: concise description of the 3D functional assembly
- object_count: 1
- dimensionality: "3d" (use "flat" ONLY if the drawing is explicitly a multi-view flat mounting plate/bracket)
- projection_standard: "third-angle" or "first-angle"
- views: list of views (each with direction, sheet region and what it constrains)
- manufacturing_strategy: concrete FDM 3D printing & multi-part assembly strategy (how the 3 parts are built in 3D volume, how they join/move with clearance, and how the assembly stands stably on Z=0)
- fdm_assembly: {
    "printable_part_count": 3,
    "min_solid_count": 3,
    "max_solid_count": 5,
    "clearance_mm": 0.5,
    "kinematics_and_joints": [
      {"joint_id": "...", "type": "rotary_axle|steering_pivot|snap_socket|stage_tenon|ball_socket", "part_a": "...", "part_b": "...", "axis": "X|Y|Z", "clearance_mm": 0.5, "function": "..."}
    ],
    "fdm_print_notes": "..."
  }
- parts: list of the 3 distinct printable parts (each with id, name, role, primitive_3d_strategy, cross_section_shape, dimensions_mm, and joint_interfaces)
- features: list of key 3D volumetric and functional features (do NOT list enclosed 2D pen-stroke spaces as through-holes unless they are true windows/wheel-spokes/bores)
- relations: spatial and mechanical joint relations between the 3 parts
- symmetry, repetitions, dimensions (must include max_width, max_depth, max_height in mm with max_depth >= 25% of max dimension so it is truly 3D), uncertainties, interpretation_conflicts, generation_notes, and construction_plan."""

SCAD_PROMPT = """You are a principal mechanical engineer and OpenSCAD master generating a TRUE 3D VOLUMETRIC, MULTI-PART FDM 3D-PRINTABLE ASSEMBLY from a user's doodle seed and structured specification. Output OpenSCAD code only.

NON-NEGOTIABLE 3D VOLUMETRIC & FDM MULTI-PART RULES:
1. NO 2.5D PLAQUES OR SILHOUETTE EXTRUSIONS:
   - When specification.dimensionality == "3d" (or fdm_assembly is present), NEVER extrude the 2D outer silhouette of the drawing with linear_extrude() and NEVER build a flat backing plate with engraved grooves.
   - Every part must be a true 3D volumetric solid built from 3D primitives:
     * Bodies of revolution (axisymmetric vessels, cylindrical/conical bodies, nozzles, rollers, domes, hubs): use `rotate_extrude()` or coaxial `cylinder(r1=..., r2=...)` + `sphere()` domes + `difference()` cavities.
     * Curved 3D columns, shafts, frames, pipes, and limbs: build true round-cross-section 3D tubes by chaining pairwise `hull() { translate(p_i) sphere(d=d_i); translate(p_next) sphere(d=d_next); }` along 3D `[x, y, z]` waypoints — never a flat 2D strip.
     * 3D organic or aerodynamic lobes, cantilevers, blades, and grips: build in 3D using `hull()` of scaled 3D `sphere()` / `cylinder()` primitives pitched and rotated in 3D space (`rotate([rx, ry, rz]) scale([sx, sy, sz]) sphere(r=...)`), arranged radially or spatially in 3D around the core so the object has rich 3D depth along Y as well as X and Z.
2. MULTI-PART MECHANICAL ASSEMBLY WITH REAL CLEARANCE (`components >= 3`):
   - Render the 3 printable parts in their natural ASSEMBLED 3D pose, plus an `explode_gap = 0;` top-level parameter (in mm) that shifts the parts apart along their assembly axes when increased.
   - CRITICAL MESH SEPARATION RULE: In OpenSCAD, if two parts touch at even a single point or shared plane, OpenSCAD merges them into 1 connected component! To guarantee that `model.stl` contains 3 to 5 independent watertight printable solids (`components >= 3`) when `explode_gap = 0`:
     * Declare `clearance = 0.6;` (mm) as a top-level user-editable parameter.
     * Every mating joint (rotary axle in bore, pivot shaft in sleeve, tenon in mortise/socket, ball/pin in socket, or stepped stage collar) MUST maintain a full `clearance` air gap on BOTH radius (`bore_r = shaft_r + clearance`) AND axial shoulders/floors (`gap >= clearance` along the axis so no faces touch). Remember that a `sphere(d=D)` at the tip of a `hull()` extends `D/2` beyond its center coordinate along the axis, so make any blind socket bore at least `D/2 + 2*clearance` deeper than the sphere center!
     * When subtracting a socket/bore clearance cutter from a receiving part, extend the clearance cutter envelope along the ENTIRE length of the mating shaft that passes near any overhanging lobes or projections so no overhanging feature grazes the mating part outside the socket.
     * Never union() separate printable parts together; instantiate each printable part in its own module (`part_1_...()`, `part_2_...()`, `part_3_...()`) at the top level.
   - Within each individual printable part, all sub-features MUST overlap cleanly by >= 1.5 mm inside one `union()` so there are zero tiny floating splinters.
3. CANONICAL AXES, ORIENTATION & FDM PRINTABILITY:
   - Canonical axes: X = width (left-right), Y = front-to-back depth, Z = height (up).
   - Cameras are fixed: front looks down Y (shows XZ plane), top looks down Z (shows XY plane), right looks down X (shows YZ plane).
   - Orient the assembly so its primary side/profile matches the drawing in the FRONT view (XZ plane), while having full 3D thickness/radius along Y (depth >= 25% of overall size).
   - The lowest point of the assembly MUST rest stably at Z = 0 (within 0..0.5 mm) and all extents must fit inside a 256 x 256 x 256 mm FDM build cube.
4. PARAMETRIC METADATA (`/* doodle-meta JSON */`):
   - Before the parameter declarations, include a `/* doodle-meta JSON */` comment with version 1, `parameters`, and `features` objects. Example:
     `/* doodle-meta {"version":1,"parameters":{"width":{"label":"Overall width","description":"Overall X width of the assembly","unit":"mm","min":60,"max":180,"step":1},"explode_gap":{"label":"Explode gap","description":"Separates the printable parts along assembly axes","unit":"mm","min":0,"max":50,"step":1}},"features":{"overall_width":{"kind":"dimension","axis":"x","label":"Overall width"}}} */`
   - Expose meaningful top-level numeric parameters at column 0 before any module/function, including overall dimensions (`width`, `depth`, `height`), key part dimensions, `clearance`, and `explode_gap`.
   - Give every entry in `parameters` a `label`, `description`, `unit` (`"mm" | "°" | "count" | "unitless"`), `min`, `max`, and `step`.
   - Use only real OpenSCAD built-ins (`cube`, `cylinder`, `sphere`, `rotate_extrude`, `linear_extrude`, `hull`, `union`, `difference`, `intersection`, `scale`, `rotate`, `translate`). Never use `box()` or `revolve()`. Never assign geometry to variables."""

COMPILER_REPAIR_PROMPT = """You repair OpenSCAD compiler and empty-object failures without redesigning the part.
Return complete OpenSCAD code only. Make the smallest source change that compiles to a non-empty STL.
Preserve all dimensions, profiles, holes, slots, symmetry, modules and the intended construction family.
Preserve and update the doodle-meta JSON comment to match any changed geometry and parameter declarations.
Use only real OpenSCAD syntax and built-ins. Use cube(), not box(); use rotate_extrude(), not revolve().
Never assign geometry or module invocations to variables. The final program must instantiate one connected design."""

SUPERVISOR_PROMPT = """You supervise a 3D-printable CAD synthesis loop. Diagnose the candidate against the specification, supplied doodle, rendered 3D projections (isometric, front, top, right), compile log, and deterministic evaluation.
Check specifically:
1. Is the model a TRUE 3D VOLUMETRIC assembly (round/tubular/revolved/3D-hulled bodies with real depth along Y) rather than a flat 2.5D extruded plaque?
2. Does `mesh_health.components` equal the expected 3 to 5 independent watertight printable solids (`watertight == true`, separated by `clearance` at every mechanical joint so parts do not boolean-merge into 1 lump, and with zero tiny floating debris splinters)?
3. Do the 3 parts capture the doodle's visual character and inherent mechanical movement/assembly while standing stably at Z=0?
Choose exactly one action:
- accept: only if all mandatory gates pass, the parts are true 3D volumetric solids, and the multi-part FDM assembly is valid;
- repair_scad: preserve the interpretation but fix joint clearance/separation, 3D volume, topology, scale, or missing features;
- reinterpret: revise the structured design when the chosen design path contradicts the doodle.
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
        single_view_seed = evidence.get("view_group_count", 1) <= 1 and not additional_views
        if single_view_seed:
            vg = (evidence.get("view_geometry") or [{}])[0]
            prompt_evidence = {
                "image_size_px": evidence.get("image_size_px"),
                "view_group_count": evidence.get("view_group_count", 1),
                "primary_view_bbox_normalized": vg.get("sheet_bbox_normalized"),
                "pixel_aspect_ratio_width_over_height": vg.get("pixel_aspect_ratio_width_over_height"),
                "note": "Single-view doodle seed: infer full 3D volumetric geometry, 3 FDM-printable parts, and mechanical joints/clearances rather than tracing 2D contours.",
            }
        else:
            prompt_evidence = evidence
        user_text = f"User description: {notes or '(none)'}\nAuthoritative maximum dimension: {dimension or '(none supplied)'}\nControls: {json.dumps(controls)}\nDrawing evidence: {json.dumps(prompt_evidence)}"
        visual_content: list[dict[str, Any]] = [
            {"type":"text","text":user_text},
            {"type":"text","text":"FULL DRAWING SHEET (use as a 3D industrial design & mechanical seed):"},
            {"type":"image_url","image_url":{"url":self.client.image_url(image,mime)}},
        ]
        registered = self._registered_view_crops(image,evidence,controls,out)
        for direction, crop in registered.items():
            visual_content.extend([
                {"type":"text","text":(
                    f"REGISTERED {direction.upper()} VIEW CROP."
                )},
                {"type":"image_url","image_url":{"url":self.client.image_url(crop,"image/png")}},
            ])
        for direction, view_data, view_mime in additional_views:
            visual_content.extend([{"type":"text","text":f"ADDITIONAL ORTHOGRAPHIC VIEW ({direction}):"},{"type":"image_url","image_url":{"url":self.client.image_url(view_data,view_mime)}}])
        messages = [{"role":"system","content":SPEC_PROMPT},{"role":"user","content":visual_content}]
        stage("interpreting")
        spec = await self._json_call(messages,out,"interpretation")
        spec["object_count"] = 1
        if single_view_seed and str(spec.get("dimensionality", "")).lower() != "flat":
            spec["dimensionality"] = "3d"
            fdm = spec.get("fdm_assembly") if isinstance(spec.get("fdm_assembly"), dict) else {}
            fdm.setdefault("printable_part_count", 3)
            fdm.setdefault("min_solid_count", 3)
            fdm.setdefault("max_solid_count", 5)
            fdm.setdefault("clearance_mm", 0.6)
            spec["fdm_assembly"] = fdm
        spec["user_intent"] = {"description": notes, "object_type_hint": controls.get("object_type_hint", ""), "authoritative_max_dimension_mm": dimension}
        spec["source_view_group_count"] = evidence.get("view_group_count", 1)
        spec["multi_view_contract"] = "All source views constrain one shared physical assembly; never instantiate views as separate geometry."
        spec["cutout_policy"] = "Closed internal profiles are subtractive through-cutouts only when explicitly classified as holes/cutouts."
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
        is_fdm_3d = bool(spec.get("fdm_assembly") or str(spec.get("dimensionality", "")).lower() == "3d")
        generation_input = {
            "design_contract": {
                "object_count": 1,
                "mode": "fdm_3d_multipart_assembly" if is_fdm_3d else "orthographic_part",
                "views_are_constraints_not_parts": True,
                "projection_standard": controls.get("projection_standard"),
                "strict_watertight": controls.get("strict_watertight"),
                "method": controls.get("method"),
            },
            "specification": spec,
            "measured_view_geometry": (
                {"aspect_ratio_width_over_height": (evidence.get("view_geometry") or [{}])[0].get("pixel_aspect_ratio_width_over_height")}
                if is_fdm_3d
                else {"coordinate_contract": evidence.get("coordinate_contract"), "views": evidence.get("view_geometry", [])}
            ),
            "intent_refinements": None if is_fdm_3d else refine_evidence(evidence, controls.get("refine_mode", "regularize")),
            "derived_sizes": derived_sizes,
        }
        strict = bool(controls.get("strict_watertight", True))
        stage("generating")
        gen_user_content: Any = (
            [
                {"type": "text", "text": json.dumps(generation_input, indent=2)},
                {"type": "text", "text": "ORIGINAL DOODLE SEED (build a true 3D volumetric, 3-part FDM printable assembly with >= 0.6 mm clearance between mating parts):"},
                {"type": "image_url", "image_url": {"url": self.client.image_url(image, mime)}},
            ]
            if (is_fdm_3d and image)
            else json.dumps(generation_input, indent=2)
        )
        scad = await self._scad_call(
            [{"role":"system","content":SCAD_PROMPT},{"role":"user","content":gen_user_content}],
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
                regen_content: Any = (
                    [{"type":"text","text":json.dumps(fresh_input,indent=2)},
                     {"type":"text","text":"ORIGINAL DOODLE SEED:"},
                     {"type":"image_url","image_url":{"url":self.client.image_url(image,mime)}}]
                    if (is_fdm_3d and image)
                    else json.dumps(fresh_input,indent=2)
                )
                scad=await self._scad_call(
                    [{"role":"system","content":SCAD_PROMPT},{"role":"user","content":regen_content}],
                    attempt_dir, "regeneration", temperature=.15,
                )
                continue
            if next_action == "reinterpret":
                revised_content = visual_content + [{"type":"text","text":f"Revise the previous specification using this supervisor diagnosis.\nPREVIOUS SPEC:\n{json.dumps(spec)}\nDIAGNOSIS:\n{json.dumps(diagnosis)}"}]
                spec = await self._json_call([{"role":"system","content":SPEC_PROMPT},{"role":"user","content":revised_content}],attempt_dir,"reinterpretation",temperature=0)
                spec["object_count"] = 1
                if single_view_seed and str(spec.get("dimensionality", "")).lower() != "flat":
                    spec["dimensionality"] = "3d"
                    fdm = spec.get("fdm_assembly") if isinstance(spec.get("fdm_assembly"), dict) else {}
                    fdm.setdefault("printable_part_count", 3)
                    fdm.setdefault("min_solid_count", 3)
                    fdm.setdefault("max_solid_count", 5)
                    fdm.setdefault("clearance_mm", 0.6)
                    spec["fdm_assembly"] = fdm
                generation_input["specification"] = spec
                reinterp_content: Any = (
                    [{"type":"text","text":json.dumps(generation_input,indent=2)},
                     {"type":"text","text":"ORIGINAL DOODLE SEED:"},
                     {"type":"image_url","image_url":{"url":self.client.image_url(image,mime)}}]
                    if (is_fdm_3d and image)
                    else json.dumps(generation_input,indent=2)
                )
                scad = await self._scad_call(
                    [{"role":"system","content":SCAD_PROMPT},{"role":"user","content":reinterp_content}],
                    attempt_dir, "reinterpretation-generation", temperature=.05,
                )
            else:
                passing=[name for name,passed in evaluation.get("mandatory_gates",{}).items() if passed]
                repair_content: list[dict[str,Any]] = [{"type":"text","text":f"Repair this candidate according to the diagnosis and evaluation. Preserve every required feature.\nPRESERVATION CONTRACT: These gates already pass and must not regress: {json.dumps(passing)}. Ensure mating printable parts maintain a full clearance air gap (both radial and axial >= clearance) so mesh_health.components stays within 3..5 independent watertight printable solids, while sub-features within each individual part overlap cleanly.\nDIAGNOSIS: {json.dumps(diagnosis)}\nEVALUATION: {json.dumps(evaluation)}\nMESH_HEALTH: {json.dumps(health)}\nSPEC: {json.dumps(spec)}\nCODE:\n{scad}"}]
                if image:
                    repair_content.extend([{"type":"text","text":"ORIGINAL DOODLE SEED:"},{"type":"image_url","image_url":{"url":self.client.image_url(image,mime)}}])
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
