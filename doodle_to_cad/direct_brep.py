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

PROMPT_VERSION = 'drawing-brep-9'
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
box: origin (minimum corner),size (three positive lengths along X,Y,Z).
cylinder: origin (base centre),radius,height,axis (x/y/z).
union/difference: left,right (earlier operation IDs).
rotate: body,origin (pivot),axis (x/y/z),angle (degrees, 0<angle<=360). Right-hand rotation of a COPY about the world axis through the pivot.
fillet: body,radius,selector (all/parallel_x/parallel_y/parallel_z).
chamfer: body,radius (straight-line width ACROSS the bevel face, applied to all edges). For a 45-degree bevel with setback C along each adjoining face, radius = C * 1.4142135623730951. Expose C as a parameter and use a quoted expression for radius.
arc_pipe: origin (arc centre),bend_radius,radius,angle (0<angle<=270). Circular solid profile swept along an XY arc from +X anticlockwise. radius < bend_radius.
- Each evidence category contains entries with only id,text. Keep observed, inferred, assumptions and unresolved separate. Unresolved construction values prevent building.
- constraints contains ONLY intentionally overlapping volumetric material joints. Do not add these constraints to tangential pipe/leg joints with matching end faces; those have zero intersection volume even when their union is one connected solid. Full-face fused joints are checked through the final connected solid, not an invented positive overlap requirement. Each volumetric joint has the form: {"id":"joint1","kind":"connected","left":"feature1","right":"feature2","min_volume_mm3":0.01}. Both features must occur in final construction. Do not confuse containment with material connection.

GEOMETRY:
The whole drawing sheet depicts ONE object. X=width, Y=depth, Z=height. Front projection is XZ, top is XY, right is YZ. A circular feature seen in front has its cylinder axis along Y, not Z. Lowest Z must be zero, including rotated bodies.
Preserve measured proportions, feature counts, unequal sizes and the declared maximum dimension. Keep one connected final solid. Expose useful dimension parameters.
Box origin is its minimum corner and its endpoint equals origin + size. Compute joint endpoints explicitly. For a volumetric joint, extend joined material into both owners by a positive overlap. Full matching end faces can instead be fused by union into one solid; do not claim positive overlap volume for that face-to-face joint. Gaps and edge-only contact are invalid. Never subtract away required joint overlap. Cutters must cross the wall they cut.
Use rotation for diagonal features and radial patterns. Loft, arbitrary profiles and arbitrary sweeps are unsupported. Do not replace them silently with another construction.
For missing depth or dimensions, choose explicit conservative assumptions and expose parameters. Do not silently discard unresolved drawing details. Return unsupported if uncertainty prevents a supported construction.
Check placement and dimensions with numeric arithmetic before returning the recipe:
- A cylinder along X or Y extends one radius below its centre in Z. Put its centre at least that radius above Z=0.
- A connector endpoint is origin + length, not origin + a radius. Keep it inside the outer envelope while extending it into its owners.
- Stacked bodies that meet at one plane have zero overlap volume. Extend the internal member into each owner; retain the intended outer heights. The overlap must meet the declared min_volume_mm3, including after later cuts.
Use the visible shape, not just its object name. Preserve rounded transitions and flat bevels when the drawing shows them. Use a fillet only on the indicated edge family; rounding vertical corners must not round a sharp top or bottom rim.
For a curved circular-section path, use arc_pipe and any visible straight segments. Its centreline radius differs from its inner and outer radii. Preserve the section size and endpoint positions. Do not replace a curve by a box.
Expose the actual bend radius, section size and edge-treatment size as useful parameters. Reference these parameters in operation fields and dependent origins. An editable radius must also move connected endpoints and the section centre above the bed where required. Preserve dimensions that the edit is not meant to change.
Follow the planned axes, cross-sections and endpoint arithmetic in the construction_plan. The plan is an interpretation, not proof: report contradictions with the original image instead of silently changing its feature types.
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
    allowed = {'origin','size','radius','height','bend_radius'}
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


CORRECTION_PROMPT_VERSION = 'construction-numeric-fields-3'
CORRECTION_PROMPT = """Correct a measured BRep construction failure. Return the complete version 2 recipe as JSON only.
Preserve every feature ID, operation kind, dependency, cylinder axis, rotation angle, output and connection constraint exactly.
Keep recipe metadata, body declarations, frames and evidence text unchanged.
Change only operation origin, size, radius, height or bend_radius fields and existing parameter values within their ranges. Keep every other operation field unchanged.
A cylinder uses height, not size. A box uses size, not height. Use quoted arithmetic expressions for dimensions. Never use null placeholders.
For negative minimum Z, raise primitive Z coordinates AND rotation pivot Z coordinates consistently. A cylinder along X or Y extends one radius below its centre in Z. Changing a diameter alone does not put the part on Z=0.
For oversize connectors, compute endpoint = origin + length. Shorten the connector to stay inside its outer owner while retaining positive overlap. Do not shrink the whole design to hide protrusions.
For stacked zero-overlap joints, extend the internal member into BOTH owners while keeping the outer envelope unchanged. Lower its origin AND increase its height to overlap both ends. Meet the declared minimum volume; never weaken that requirement.
Return actual changes that resolve the diagnostic. Do not repeat the unchanged recipe. Preserve intended shape and feature count. This is a construction correction, not a drawing-fidelity judgment.
"""


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
                            pipeline, results_dir, jobs, prune, save_result):
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
        raw_plan = await pipeline._json_call(intent_messages,out,'construction-plan',temperature=0)
        try:
            plan = validate_plan(raw_plan)
        except ValueError as exc:
            raise BuildError('invalid_recipe', 'Construction plan rejected: '+str(exc)) from exc
        (out/'construction-plan.json').write_text(json.dumps(plan,indent=2))
        job['stage'] = 'planning BRep recipe'
        payload = {'evidence':evidence,'construction_plan':plan,'notes':notes,'maximum_dimension_mm':maximum,'controls':controls}
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
                validate_recipe(raw)
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
        result['files']['construction_plan'] = f'/results/{run_id}/construction-plan.json'
        result['files']['evidence'] = f'/results/{run_id}/feature-evidence.json'
        result['files']['generation'] = f'/results/{run_id}/generation.json'
        (out/'result.json').write_text(json.dumps(result,indent=2))
        return result

    job['task'] = asyncio.create_task(run_recipe_job(job,None,results_dir,publish,prepare=prepare,repair=repair))
    return {'job_id':run_id,'status':'running'}
