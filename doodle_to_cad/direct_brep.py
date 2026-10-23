"""Experimental drawing-to-recipe path. No generated code or backend fallback."""
import asyncio
import json
import math
import time
import uuid
from pathlib import Path

from fastapi import HTTPException

from .brep_recipe import validate_recipe
from .build_contract import BuildError
from .recipe_jobs import check_worker, run_recipe_job
from .construction_intent import PROMPT as INTENT_PROMPT, PROMPT_VERSION as INTENT_VERSION, validate_plan

PROMPT_VERSION = 'drawing-brep-19'
PROMPT = """Construct ONE editable BRep part directly from the drawing and measured evidence.
Return valid JSON only. Never return Python or OpenSCAD. If the part needs an unsupported operation, return {"unsupported":"specific reason"}.

First resolve the path plane and cross-section from the drawing labels. A path shown in TOP lies in XY; its thickness is along Z. A circular end section applies to straight segments as well as bends. A rectangular longitudinal silhouette does not make the section rectangular: use cylinders for circular-section straight segments. Moving a part above the bed is a translation through origins, not a rotation.

Complete minimal version 2 recipe example (all root fields are required):
{"version":2,"units":"mm","name":"plate","parameters":{"width":{"value":60,"min":30,"max":100}},"operations":[{"id":"plate","kind":"box","origin":[0,0,0],"size":["width",40,5],"frame":"world","depends_on":[],"evidence":["e1"]}],"output":"plate","frames":{"world":{"origin":[0,0,0],"x":"width","y":"depth","z":"height"}},"bodies":[{"id":"part","output":"plate"}],"evidence":{"observed":[],"inferred":[],"assumptions":[{"id":"e1","text":"Assumed plate thickness 5 mm."}],"unresolved":[]},"constraints":[]}

SCHEMA:
- Always include TOP-LEVEL output. It and bodies[0].output must name the final operation ID.
- IDs are unique identifiers: letters, digits, underscores, starting with a letter.
- Parameters: at most 64. Each needs numeric value,min,max. Optional label,unit,description,group.
- Dimensions are finite numbers or QUOTED arithmetic strings using parameter names and + - * / parentheses only. Example: [0,"-width/2",0]. Bare arithmetic is invalid JSON. No trig functions or references to operation fields.
- Every operation has id,kind,frame:"world",depends_on:[earlier input body IDs],evidence:[IDs from recipe.evidence]. At most 128 operations, in dependency order.
- Add exactly the fields listed for its kind:
shell: body (earlier solid),thickness (positive inward uniform wall AND floor thickness),opening (exactly "top"),preserve (exactly "outer"). Removes the single highest planar face and hollows inward, preserving outside bounds. Tested for boxes and boxes with rounded vertical corners. Keep outer width, depth, height and outside corner radius independent of thickness. For a rounded tray, make the outer box, fillet ONLY parallel_z edges to the drawn outside radius, then shell that rounded body. Flat top and floor faces remain flat. Expose thickness with label "Wall and floor thickness". If wall and floor need DIFFERENT dimensions, use an explicit difference with separate wall/floor parameters instead of pretending shell supports them. Reject missing or conflicting cavity details; never assume a missing wall/floor thickness.
loft: plane (only "xy"),correspondence (exactly "rectangle_corners_to_circle_diagonals"),profiles (exactly two ordered objects). First: {"shape":"rectangle","center":[x,y,z],"width":X_length,"height":Y_length}. Second: {"shape":"circle","center":[same_x,same_y,higher_z],"radius":R}. This is a SOLID rectangular-to-round transition with flat caps, not a hollow duct. Profiles are parallel XY planes with equal XY centres. The circle must be 0.01–256 mm above the rectangle. Profile dimensions must be 0.01–128 mm. The worker matches rectangle corners NE/NW/SW/SE to circle points at 45/135/225/315 degrees in CCW order and makes a degree-1 loft. No twist, rotated/offset profiles, intermediate profiles, splines or holes. Numeric fields allow quoted parameter expressions. Expose rectangle width as a parameter; changing it must keep the circle radius, centre and separation fixed. Use the two end profiles and labelled side-view separation, not a straight extrusion or cone approximation.
sweep: origin (world translation, normally [0,0,0]),plane (only "xy"),frame_rule (exactly "normal_to_path_z_up"),section_width (in-plane width),section_height (Z height),path (ordered open list containing one circular arc, optionally preceded/followed by one tangent line). This makes a solid RECTANGULAR section, with flat caps. Path points are local XY centreline coordinates. The section centre follows the path at local Z=section_height/2; its bottom stays at Z=0 before origin translation. Line: {"kind":"line","start":[x,y],"end":[x,y]}. Arc: {"kind":"arc","center":[x,y],"radius":R,"start_angle":degrees,"end_angle":degrees}. Angles are measured from +X. Positive sweep is CCW; negative sweep is clockwise. The absolute difference must be 1–180 degrees. Radius > section_width/2 + 0.01 mm. Lines must meet the arc endpoints exactly and follow its tangent. Line endpoint order is normalized to join the arc; coordinates are never moved. For CCW arcs, tangent directions at angles 0/90/180/270 degrees are +Y/-X/-Y/+X. The arc 0 to 180 passes above its centre; 180 to 360 passes below. Clockwise tangents are the opposite directions. Clockwise 180 to 0 passes above its centre. The worker reverses clockwise traversal to the equivalent CCW chain before kernel construction. Check endpoint coordinates AND tangent direction at both joins. Preserve the upright rectangular section through the bend. No spline, multiple bends, sharp joints or other planes. Numeric fields allow quoted parameter expressions. Expose section_height or section_width as a parameter; height edits must keep the XY path and width fixed. Use this for a rectangular-section bend with optional straight ends, not arc_pipe (which is circular).
extrude: origin (world XYZ translation),plane (only "xy"),direction (integer 1 or -1 along Z),depth (positive 0.01–256 mm),loops (outer loop first, followed by through-opening loops). Each loop is an ordered list of line/arc objects, joined end-to-start and closed. Line: {"kind":"line","start":[u,v],"end":[u,v]}. Arc: {"kind":"arc","center":[u,v],"radius":positive,"start_angle":degrees,"end_angle":degrees}; CCW from +X, 0 < end-start <=360. A circle is one 0-to-360 arc. Do not split a circle across multiple same-circle arcs. Local u,v are X,Y; origin translates the profile into the world. Numeric profile fields may use quoted parameter expressions. At most 128 edges and 16 loops. No crossing, touching, nested holes, open outlines or splines. Use the exact line/arc outline, not a bounding rectangle. Expose thickness via depth; changing depth must not change the profile. Other extrusion planes are unsupported because their USD round trip is not verified. Do not rotate an extruded profile to evade that restriction.
box: origin (minimum corner),size (three positive lengths along X,Y,Z).
cylinder: origin (base centre),radius,height,axis (x/y/z). Height is positive; the cylinder extends from origin in the POSITIVE axis direction. For a segment that runs from a joint toward negative Y, put its origin at joint_y - height so its positive-Y endpoint meets the joint. Apply the same rule on X and Z. Compute both endpoints; text claiming a negative direction does not change this geometry.
union/difference: left,right (earlier operation IDs).
rotate: body,origin (pivot),axis (x/y/z),angle (degrees, 0<angle<=360). Right-hand rotation of a COPY about the world axis through the pivot.
fillet: body,radius,selector (all/parallel_x/parallel_y/parallel_z).
chamfer: body,radius (straight-line width ACROSS the bevel face, applied to all edges). For a 45-degree bevel with setback C along each adjoining face, radius = C * 1.4142135623730951. Expose C as a parameter and use a quoted expression for radius.
arc_pipe: origin (arc centre),bend_radius,radius,angle (0<angle<=270). Circular solid profile swept along an XY arc from +X anticlockwise. radius < bend_radius.
revolve: origin (world XYZ translation),axis (exactly "z"),profile (one closed ordered list of 3–128 numeric [r,z] pairs; r = radius from the axis, z = height. The last pair joins back to the first; never repeat the first pair. r must be 0 or positive; the profile never crosses the axis. No crossing, touching, repeated or zero-area edges. Full 360 degrees about +Z; partial angles and spline profiles are unsupported. Numeric fields allow quoted parameter expressions.). This makes ONE axisymmetric solid from its radius-height silhouette: vase, bottle, cup, ring or stepped shaft. Prefer it over stacked cylinders for smooth stepped circular profiles. Keep each vertex an honest straight-line approximation of the drawn curve and disclose that in evidence. Build a HOLLOW vessel with ONE closed profile: base from the axis outward, outer wall up to the rim, rim inward by the wall thickness, inner wall down, inner floor across, back to the axis. Derive every inner radius and floor height from the declared wall and floor thickness values; never invent them. Keep the lowest z at 0 before origin translation. Expose overall height, maximum radius and, for vessels, wall and floor thickness as parameters; an edit to the maximum radius must move every dependent radius by the same amount.
sphere: origin (CENTER),radius (0.01–256). To sit on the Z=0 plate the origin z must equal the radius.
cone: origin (bottom-face centre),radius_base,radius_top (0–256, never above radius_base; 0 gives an apex),height,angle (1–360 revolution),axis (x/y/z). The solid extends from origin in the POSITIVE axis direction. A 1/4 cone is angle 90.
torus: origin (ring centre),bend_radius (ring centre to tube centre),radius (tube; radius < bend_radius),angle (1–360; 360 is a full ring),axis (torus normal). To sit on the plate the origin z must equal radius. A ring, washer rim or handle.
wedge: origin (base centre),radius,height,start_angle (0–359),end_angle (up to 360, at least 1 degree after start),axis. Absolute angular slice of a cylinder, degrees CCW from +X; height extends along the POSITIVE axis.
pyramid: origin (BASE-CENTRE of the bottom face),base (square side length),height. The apex sits above the base centre.
arc_block: origin (annulus centre at the bottom face),length (Z height),inside_radius (0 allowed),outside_radius,start_angle (0–359),end_angle. An annular sector CCW from +X, like a curved bracket segment.
helix: origin (bottom of the axis),height,radius_start,radius_end,turns (0.5–64),tube_radius (at least 2 mm — thinner tubes fail the build guards). A solid round tube wound right-handed about +Z climbing from origin. The capped end dips about tube_radius below origin: put origin z at least tube_radius. A spring or coil.
drafted_extrude: plane (only "xy"),direction (exactly 1),depth (0.01–256),draft_angle (0–45),loops (same closed line/arc loops as extrude, outer first). A positive draft_angle SHRINKS the section going up by depth*tan(angle) per side — mould draft. Check the top section does not collapse before using an angle.
- Each evidence category contains entries with only id,text. Keep observed, inferred, assumptions and unresolved separate. Unresolved construction values prevent building.
- constraints contains ONLY intentionally overlapping volumetric material joints. Do not add these constraints to tangential pipe/leg joints with matching end faces; those have zero intersection volume even when their union is one connected solid. Full-face fused joints are checked through the final connected solid, not an invented positive overlap requirement. Each volumetric joint has the form: {"id":"joint1","kind":"connected","left":"feature1","right":"feature2","min_volume_mm3":0.01}. Both features must occur in final construction. Do not confuse containment with material connection.

GEOMETRY:
The whole drawing sheet depicts ONE object. X=width, Y=depth, Z=height. Front projection is XZ, top is XY, right is YZ. A circular feature seen in front has its cylinder axis along Y, not Z. Lowest Z must be zero, including rotated bodies.
Preserve measured proportions, feature counts, unequal sizes and the declared maximum dimension. Keep one connected final solid. Expose useful dimension parameters.
OUTER SILHOUETTE IS A HARD CONSTRAINT: each view's outer_profile polygon is the truth of the body outline for that view. When feature_placements_mm is present, build the body by extruding or revolving the outer_silhouette polygon_mm VERBATIM — copy its coordinates; to keep editability, wrap them in quoted width/height expressions that evaluate to exactly those numbers. Never re-derive, simplify, mirror, rotate or "symmetrize" the outline from the image. Use the evidence curve_segments to regularize honestly: lines stay lines, arcs are rebuilt through their from/mid/to points, every shoulder and curved transition survives. A front-view outline stands upright: extrude() builds sections in local XY extruded along +Z, so extrude (u,v) = polygon_mm, then rotate angle 90 axis x origin [0,0,0] to map (u,v,t) -> (u,-t,v), then translate so the thickness spans the depth. Cut internal features after that rotation using world coordinates from center_mm: a slit = box origin [X-w/2,-0.1,Z-h/2] size [w,depth+0.2,h]; a hole = cylinder axis y origin [X,-0.1,Z] radius r height depth+0.2. Never replace the outline with a rounded rectangle, ellipse, box or circle, and never recover a lost silhouette with fillets or chamfers. Only when intent_refinements reports outer_profile_fit.accepted true may a primitive replace that outline.
Box origin is its minimum corner and its endpoint equals origin + size. Compute joint endpoints explicitly. For a volumetric joint, extend joined material into both owners by a positive overlap. Full matching end faces can instead be fused by union into one solid; do not claim positive overlap volume for that face-to-face joint. Gaps and edge-only contact are invalid. Never subtract away required joint overlap. Cutters must cross the wall they cut.
Use rotation for diagonal features and radial patterns. Closed XY line/arc profile extrusion, the drafted extrusion, the bounded rectangular sweep described above are supported. The rectangular-to-round loft described above is supported. The bounded revolve described above is supported for axisymmetric silhouettes. sphere, cone, torus, wedge, pyramid, arc_block and helix primitives are supported. Other lofts, spline profiles, extrusions in other planes and other sweeps are unsupported. Do not replace them silently with another construction.
STANDING-PLATE WORKED EXAMPLE: a front-view outline must stand in XZ with thickness along Y — it must never lie flat in the XY plane, which fails the front projection check. Emit exactly this pair (numbers taken from feature_placements_mm outer_silhouette polygon_mm), then cut internal features against the rotated body in world coordinates:
{"id":"body","kind":"extrude","frame":"world","depends_on":[],"evidence":["e1"],"origin":[0,0,0],"plane":"xy","direction":-1,"depth":"thickness","loops":[[{"kind":"line","start":[X1,Z1],"end":[X2,Z2]}]]}
{"id":"stand","kind":"rotate","frame":"world","depends_on":["body"],"evidence":["e1"],"body":"body","origin":[0,0,0],"axis":"x","angle":90}
The rotate maps (u,v,t) -> (u,-t,v): X = polygon X, Z = polygon Z (the flip is already in polygon_mm). With direction -1 the thickness occupies Y from 0 to +thickness, so the plate stands on the +Y side and internal cutters span y = -0.1 to y = thickness + 0.1. A body without this rotate is a lying slab and is always wrong for a front-view plate.
For missing depth or dimensions, choose explicit conservative assumptions and expose parameters. Do not silently discard unresolved drawing details. Return unsupported if uncertainty prevents a supported construction.
Check placement and dimensions with numeric arithmetic before returning the recipe:
- A cylinder along X or Y extends one radius below its centre in Z. Put its centre at least that radius above Z=0.
- A connector endpoint is origin + length, not origin + a radius. Keep it inside the outer envelope while extending it into its owners.
- Stacked bodies that meet at one plane have zero overlap volume. Extend the internal member into each owner; retain the intended outer heights. The overlap must meet the declared min_volume_mm3, including after later cuts.
Use the visible shape, not just its object name. Preserve rounded transitions and flat bevels when the drawing shows them. Use a fillet only on the indicated edge family; rounding vertical corners must not round a sharp top or bottom rim.
For a curved circular-section path, use arc_pipe and any visible straight segments. Its centreline radius differs from its inner and outer radii. Preserve the section size and endpoint positions. Do not replace a curve by a box.
Expose the actual bend radius, section size and edge-treatment size as useful parameters. Reference these parameters in operation fields and dependent origins. An editable radius must also move connected endpoints and the section centre above the bed where required. Preserve dimensions that the edit is not meant to change.
Follow the planned axes, cross-sections and endpoint arithmetic in the construction_plan. The plan is an interpretation, not proof: report contradictions with the original image instead of silently changing its feature types.
Clarification answers are authoritative for their named feature. A thickness_mm answer applies to its kind: wall_thickness, floor_thickness or uniform_thickness (both walls and floor). Preserve it exactly and keep other declared dimensions fixed. Never replace missing wall/floor thickness with an assumption. Clarification opening answers are authoritative for their named opening. Never replace a through-hole/recess answer or recess depth with an assumption. If opening extent remains unresolved without an answer or clear drawing evidence, return unsupported. Other plan uncertainties must be resolved into explicitly disclosed assumptions under the construction-plan default policy, or remain unresolved in recipe evidence and fail validation.
The interpretation can contain mistakes; check the original image. Evidence is not proof of drawing fidelity.
"""


CORRECTABLE = {"placement_failed", "dimension_exceeded", "connection_failed"}


def validate_correction(before, after):
    """A construction correction cannot remove features or weaken required joints."""
    validate_recipe(after)
    if after.get('version') != 2 or after['output'] != before['output']:
        raise ValueError('Keep version 2 and the same output operation')
    features = lambda r: {op['id']: op['kind'] for op in r['operations']}
    if features(before) != features(after):
        raise ValueError('Construction correction must preserve all feature IDs and operation kinds')
    links = lambda r: {op['id']: {k: op[k] for k in ('left', 'right', 'body') if k in op} for op in r['operations']}
    if links(before) != links(after):
        raise ValueError('Construction correction must preserve feature dependencies')
    if before['constraints'] != after['constraints']:
        raise ValueError('Do not remove, change or weaken required connection constraints')
    if not set(before['parameters']).issubset(after['parameters']):
        raise ValueError('Keep existing editable parameter names')
    allowed = {'origin','size','radius','height','bend_radius','radius_base','radius_top','base','length',
               'inside_radius','outside_radius','tube_radius','start_angle','end_angle','draft_angle','depth'}
    original_ops = {op['id']:op for op in before['operations']}
    for op in after['operations']:
        original = original_ops[op['id']]
        if {k:v for k,v in op.items() if k not in allowed} != {k:v for k,v in original.items() if k not in allowed}:
            raise ValueError('Only numeric geometry fields may change; preserve axes and feature evidence')
    if before['parameters'].keys() != after['parameters'].keys():
        raise ValueError('Keep the same parameter names')
    for name, parameter in before['parameters'].items():
        if {k:v for k,v in parameter.items() if k != 'value'} != {k:v for k,v in after['parameters'][name].items() if k != 'value'}:
            raise ValueError('Keep parameter ranges and metadata unchanged')
    mutable = {'operations', 'parameters'}
    if {k:v for k,v in before.items() if k not in mutable} != {k:v for k,v in after.items() if k not in mutable}:
        raise ValueError('Keep recipe metadata, body identity and evidence unchanged')
    if before == after:
        raise ValueError('Construction correction made no change')


CORRECTION_PROMPT_VERSION = 'construction-numeric-fields-4'
CORRECTION_PROMPT = """Correct a measured BRep construction failure. Return the complete version 2 recipe as JSON only.
Preserve every feature ID, operation kind, dependency, cylinder axis, rotation angle, output and connection constraint exactly.
Keep recipe metadata, body declarations, frames and evidence text unchanged.
Change only operation origin, size, radius, height, bend_radius, radius_base, radius_top, base, length, inside_radius, outside_radius, tube_radius, start_angle, end_angle, draft_angle or depth fields and existing parameter values within their ranges. Keep every other operation field unchanged.
A cylinder uses height, not size. A box uses size, not height. Use quoted arithmetic expressions for dimensions. Never use null placeholders.
For negative minimum Z, raise primitive Z coordinates AND rotation pivot Z coordinates consistently. A cylinder along X or Y extends one radius below its centre in Z. Changing a diameter alone does not put the part on Z=0.
For a positive minimum Z (floating part), lower the same Z coordinates. For an extruded plate standing upright through a rotate operation, its height above the plate is controlled by the extrude origin Z and the rotate pivot origin Z — change those; NEVER edit loops, path or profile fields, which carry the protected silhouette.
For oversize connectors, compute endpoint = origin + length. Shorten the connector to stay inside its outer owner while retaining positive overlap. Do not shrink the whole design to hide protrusions.
For stacked zero-overlap joints, extend the internal member into BOTH owners while keeping the outer envelope unchanged. Lower its origin AND increase its height to overlap both ends. Meet the declared minimum volume; never weaken that requirement.
Return actual changes that resolve the diagnostic. Do not repeat the unchanged recipe. Preserve intended shape and feature count. This is a construction correction, not a drawing-fidelity judgment.
"""


def _check_standing_body(raw, placements):
    """Front-view drawings whose outline is tall cannot be built by a flat
    extrusion: catch the lying-slab failure in validation, where the retry
    loop can tell the model exactly what to add."""
    if not placements:
        return
    front = next((v for v in placements.get('views') or [] if v['view'] == 'front'), None)
    outer = next((p for p in (front or {}).get('profiles', []) if p.get('role') == 'outer_silhouette'), None)
    if not outer or not outer.get('polygon_mm'):
        return
    points = outer['polygon_mm']
    spread_z = max(p[1] for p in points) - min(p[1] for p in points)
    spread_x = max(p[0] for p in points) - min(p[0] for p in points)
    if spread_x <= 0 or spread_z < 0.4 * spread_x:
        return
    kinds = {op.get('kind') for op in raw.get('operations') or []}
    if 'extrude' in kinds and 'rotate' not in kinds:
        raise ValueError(
            f'The front view outline is {round(spread_z)} mm tall on {round(spread_x)} mm wide, so the body must stand in XZ. '
            'An extrude() builds its section flat in XY: add the STANDING-PLATE WORKED EXAMPLE pair — the same extrude plus '
            'a rotate operation (angle 90, axis x, origin [0,0,0]) depending on it — before cutting internal features.')


def _plan_or_demote(validate_plan, raw_plan):
    # An answered round sometimes invents a clarification kind outside the
    # four supported ones. Failing the whole job wastes the user's answer:
    # demote an unsupported clarification to unresolved and keep planning.
    try:
        return validate_plan(raw_plan)
    except ValueError as exc:
        if not isinstance(raw_plan, dict) or not isinstance(raw_plan.get('clarification'), dict):
            raise
        question = raw_plan['clarification']
        stripped = {k: v for k, v in raw_plan.items() if k != 'clarification'}
        label = question.get('feature_label') or question.get('feature_id') or 'a feature'
        reason = question.get('reason') or 'a construction detail is missing'
        if isinstance(stripped.get('unresolved'), list):
            stripped['unresolved'] = stripped['unresolved'] + [f'Clarification left unresolved: {label}: {reason}']
        try:
            return validate_plan(stripped)
        except ValueError:
            raise exc


def _normalize_recipe_boilerplate(raw):
    """The canonical world frame and the single output body are pipeline
    contract, not model choices: fill them instead of grading the model's
    handwriting on fields with zero degrees of freedom. Live run
    a4b87426de3f died over "x":"length" wording while its geometry was
    sound."""
    from .construction_recipe import FRAME
    if not isinstance(raw, dict):
        raise ValueError('Direct recipe must be an object')
    raw['frames'] = {'world': FRAME}
    output = raw.get('output')
    bodies = raw.get('bodies')
    valid = (isinstance(bodies, list) and len(bodies) == 1 and isinstance(bodies[0], dict)
             and set(bodies[0]) == {'id', 'output'} and bodies[0].get('output') == output)
    if isinstance(output, str) and not valid:
        raw['bodies'] = [{'id': 'part', 'output': output}]
    for op in raw.get('operations') or []:
        if isinstance(op, dict):
            refs = [op[k] for k in ('left', 'right', 'body') if k in op]
            if all(isinstance(ref, str) for ref in refs):
                op['depends_on'] = refs
    return raw


async def correct_construction(pipeline, out, recipe, failure, attempt, maximum):
    if failure['code'] not in CORRECTABLE:
        raise BuildError(failure['code'], failure['message'])
    request = {'failed_recipe':recipe,'diagnostic':failure,'maximum_dimension_mm':maximum}
    (out/'construction-correction-prompt.txt').write_text(CORRECTION_PROMPT)
    (out/f'construction-correction-{attempt}.request.json').write_text(json.dumps(request,indent=2))
    messages = [{'role':'system','content':CORRECTION_PROMPT}, {'role':'user','content':json.dumps(request)}]
    corrected = await pipeline._json_call(messages,out,f'construction-correction-{attempt}',temperature=0)
    try:
        validate_correction(recipe, corrected)
    except ValueError as exc:
        raise BuildError('invalid_recipe', f'Construction correction rejected: {exc}') from exc
    (out/f'construction-correction-{attempt}.recipe.json').write_text(json.dumps(corrected,indent=2))
    return corrected


async def submit_direct_job(image, mime, notes, dimension, extra, controls,
                            pipeline, results_dir, jobs, prune, save_result, routing=None):
    if extra:
        raise HTTPException(422, {'code':'unsupported_input', 'message':'Direct BRep currently accepts one drawing sheet. Put all projections on that sheet.'})
    if controls['primary_view'] not in {'front','top','right','left','rear'} or controls['projection_standard'] not in {'first-angle','third-angle'}:
        raise HTTPException(422, 'Invalid view controls')
    if controls['refine_mode'] == 'as_drawn':
        raise HTTPException(422, {'code':'unsupported_input','message':'Direct BRep supports regularized geometry only. Trace as drawn is not supported.'})
    try:
        maximum = float(dimension or 120)
        if not math.isfinite(maximum) or not 1 <= maximum <= 256:
            raise ValueError('Direct BRep maximum dimension must be between 1 and 256 mm')
        await check_worker()
    except (ValueError, OSError, asyncio.TimeoutError) as exc:
        raise HTTPException(422, {'code':getattr(exc,'code','invalid_input'),'message':str(exc)}) from exc
    run_id = uuid.uuid4().hex[:12]
    job = {'job_id':run_id,'kind':'recipe','status':'running','stage':'queued',
           'created':time.monotonic(),'result':None,'error':None,'task':None}
    if routing is not None:
        job['routing'] = routing
    jobs[run_id] = job
    prune()
    provenance = {'path':'drawing-to-brep','backend':'usd-brep','prompt_version':PROMPT_VERSION,
                  'correction_prompt_version':CORRECTION_PROMPT_VERSION,'max_construction_corrections':2,
                  'construction_plan_version':INTENT_VERSION,'model':None,'notes':notes,'maximum_dimension_mm':maximum,'controls':controls,
                  'generated_scad':False,'drawing_fidelity_verified':False,'attempts':[]}

    async def prepare(out):
        suffix = {'image/png':'png','image/jpeg':'jpg','image/webp':'webp'}[mime]
        (out/f'input.{suffix}').write_bytes(image)
        (out/'generation.json').write_text(json.dumps(provenance,indent=2))
        (out/'recipe-prompt.txt').write_text(PROMPT)
        provenance['model'] = (await pipeline.client.discover()).selected
        (out/'generation.json').write_text(json.dumps(provenance,indent=2))
        evidence = await pipeline.interpret_features(image, mime, controls, out=out)
        job['stage'] = 'planning BRep geometry'
        intent_request = {'controls':controls,'maximum_dimension_mm':maximum,'notes':notes}
        (out/'construction-plan-prompt.txt').write_text(INTENT_PROMPT)
        (out/'construction-plan-request.json').write_text(json.dumps(intent_request,indent=2))
        intent_messages = [{'role':'system','content':INTENT_PROMPT},{'role':'user','content':[
            {'type':'text','text':json.dumps(intent_request)},
            {'type':'image_url','image_url':{'url':pipeline.client.image_url(image,mime)}}]}]
        from .clarification import ask_clarification
        answers=[];history=[]
        for round_number in range(4):
            label='construction-plan' if not round_number else f'construction-plan-answer-{round_number}'
            raw_plan = await pipeline._json_call(intent_messages,out,label,temperature=0)
            try:
                plan = _plan_or_demote(validate_plan, raw_plan)
            except ValueError as exc:
                raise BuildError('invalid_recipe', 'Construction plan rejected: '+str(exc)) from exc
            (out/(label+'.json')).write_text(json.dumps(plan,indent=2))
            question=plan.get('clarification')
            if not question:
                break
            if round_number==3 or any(a['feature_id']==question['feature_id'] and a.get('kind','opening_extent')==question['kind'] for a in answers):
                raise BuildError('unresolved_design','The drawing still leaves a required design detail unclear after clarification. No part was built.')
            answer=await ask_clarification(job,out,question,maximum,history)
            answers.append(answer)
            intent_request['clarification_answers']=answers
            (out/f'construction-plan-answer-{round_number+1}-request.json').write_text(json.dumps(intent_request,indent=2))
            intent_messages[1]['content'][0]['text']=json.dumps(intent_request)
        (out/'construction-plan.json').write_text(json.dumps(plan,indent=2))
        job['stage'] = 'planning BRep recipe'
        payload = {'clarification_answers':answers,'evidence':evidence,'construction_plan':plan,'notes':notes,'maximum_dimension_mm':maximum,'controls':controls}
        from .sizes import derive_physical_sizes
        from .refine import refine_evidence
        labeled = json.loads((out/'geometry.json').read_text())
        payload['feature_placements_mm'] = pipeline.feature_placements_mm(labeled, derive_physical_sizes(labeled, maximum))
        payload['intent_refinements'] = refine_evidence(labeled, controls.get('refine_mode', 'regularize'))
        (out/'recipe-request.json').write_text(json.dumps(payload,indent=2))
        messages = [{'role':'system','content':PROMPT},{'role':'user','content':[
            {'type':'text','text':json.dumps(payload)},
            {'type':'image_url','image_url':{'url':pipeline.client.image_url(image,mime)}}]}]
        for attempt in range(2):
            raw = await pipeline._json_call(messages,out,f'direct-recipe-{attempt+1}',temperature=0)
            if 'unsupported' in raw:
                raise BuildError('unsupported_construction',str(raw['unsupported']))
            try:
                if raw.get('version') != 2:
                    raise ValueError('Direct generation requires recipe version 2')
                _normalize_recipe_boilerplate(raw)
                validate_recipe(raw)
                _check_standing_body(raw, payload.get('feature_placements_mm'))
                provenance['attempts'].append({'attempt':attempt+1,'schema_valid':True})
                (out/'generation.json').write_text(json.dumps(provenance,indent=2))
                return raw
            except ValueError as exc:
                provenance['attempts'].append({'attempt':attempt+1,'schema_valid':False,'error':str(exc)})
                (out/'generation.json').write_text(json.dumps(provenance,indent=2))
                if attempt:
                    raise BuildError('invalid_recipe',str(exc)) from exc
                messages += [{'role':'assistant','content':json.dumps(raw)},
                             {'role':'user','content':'Correct only the recipe schema: '+str(exc)}]

    async def repair(out, recipe, failure, attempt):
        return await correct_construction(pipeline, out, recipe, failure, attempt, maximum)

    def publish(out, recipe, built):
        extents = built['build']['measurements']['extents_mm']
        if max(extents) > maximum + .5:
            raise BuildError('dimension_exceeded',f'BRep extents_mm={extents} exceed requested maximum {maximum} mm')
        provenance['construction_attempts'] = json.loads((out/'build-history.json').read_text())
        (out/'generation.json').write_text(json.dumps(provenance,indent=2))
        result = save_result(out,recipe,built,controls=controls)
        from .brep_checks import evaluate_drawing
        from .feature_evidence import view_assignment_evidence
        geometry_path = out/'geometry.json'
        geometry = json.loads(geometry_path.read_text()) if geometry_path.exists() else {}
        views = {name:out/Path(url).relative_to('/results/'+run_id) for name,url in built.get('views',{}).items()}
        evaluation = evaluate_drawing(image, view_assignment_evidence(geometry), views,
                                      built['build']['measurements'], controls, maximum)
        result['evaluation'] = evaluation
        (out/'drawing-checks.json').write_text(json.dumps(evaluation,indent=2))
        result['files']['drawing_checks'] = f'/results/{run_id}/drawing-checks.json'
        result.update(model=provenance['model'],generation=provenance,
                      duration_seconds=round(time.monotonic()-job['created'],2))
        if (out/'clarifications.json').exists():
            result['files']['clarifications'] = f'/results/{run_id}/clarifications.json'
        result['files']['construction_plan'] = f'/results/{run_id}/construction-plan.json'
        result['files']['evidence'] = f'/results/{run_id}/feature-evidence.json'
        result['files']['generation'] = f'/results/{run_id}/generation.json'
        (out/'result.json').write_text(json.dumps(result,indent=2))
        return result

    job['task'] = asyncio.create_task(run_recipe_job(job,None,results_dir,publish,prepare=prepare,repair=repair))
    return {'job_id':run_id,'status':'running'}
