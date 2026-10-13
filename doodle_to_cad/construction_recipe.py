"""Version 2 executable recipes: explicit order, evidence and solid connections."""
from __future__ import annotations

import copy

FRAME = {"origin": [0, 0, 0], "x": "width", "y": "depth", "z": "height"}
EVIDENCE_KINDS = ("observed", "inferred", "assumptions", "unresolved")


def migrate_v1(recipe):
    """Return a new document. Keep every native version 1 field and parameter."""
    from .brep_recipe import validate_recipe
    validate_recipe(recipe)
    if recipe["version"] != 1:
        raise ValueError("Migration requires a version 1 recipe")
    result = copy.deepcopy(recipe)
    result.update(version=2, frames={"world": copy.deepcopy(FRAME)},
                  bodies=[{"id": "part", "output": recipe["output"]}],
                  evidence={key: [] for key in EVIDENCE_KINDS}, constraints=[])
    for op in result["operations"]:
        op.update(frame="world", depends_on=list(dict.fromkeys(op[k] for k in ("left", "right", "body") if k in op)), evidence=[])
    return result


def validate_v2(recipe, updates=None):
    from .brep_recipe import NAME, validate_recipe, number
    allowed = {"version", "units", "name", "parameters", "operations", "output", "frames", "bodies", "evidence", "constraints"}
    if set(recipe) - allowed:
        raise ValueError("Unknown version 2 recipe fields")
    if recipe.get("frames") != {"world": FRAME}:
        raise ValueError("Expected canonical world frame: X width, Y depth, Z height, origin [0,0,0]")
    evidence = recipe.get("evidence")
    if not isinstance(evidence, dict) or set(evidence) != set(EVIDENCE_KINDS):
        raise ValueError("Separate observed, inferred, assumptions and unresolved evidence")
    ids = set()
    for category, entries in evidence.items():
        if not isinstance(entries, list) or len(entries) > 128:
            raise ValueError(f"{category}: expected at most 128 evidence entries")
        for entry in entries:
            if not isinstance(entry, dict) or set(entry) != {"id", "text"}:
                raise ValueError(f"{category}: evidence needs id and text")
            eid = entry['id']
            if not isinstance(eid, str) or not NAME.fullmatch(eid) or eid in ids:
                raise ValueError("Evidence IDs must be unique valid names")
            if not isinstance(entry['text'], str) or not 1 <= len(entry['text']) <= 1000:
                raise ValueError(f"{eid}: evidence text must contain 1–1000 characters")
            ids.add(eid)
    if evidence['unresolved']:
        raise ValueError("Resolve build values before construction: " + ', '.join(e['id'] for e in evidence['unresolved']))
    operations = recipe.get('operations')
    if not isinstance(operations, list) or not 1 <= len(operations) <= 128:
        raise ValueError("Expected 1–128 operations")
    native = {k: copy.deepcopy(v) for k,v in recipe.items() if k in {'units','name','parameters','output'}}
    native.update(version=1, operations=[])
    seen = set()
    ancestry = {}
    for op in operations:
        if not isinstance(op, dict):
            raise ValueError("Expected an operation object")
        oid = op.get('id')
        if not isinstance(oid, str) or not NAME.fullmatch(oid) or oid in seen:
            raise ValueError("Feature IDs must be unique valid names")
        deps = op.get('depends_on')
        if not isinstance(deps, list) or any(not isinstance(d,str) for d in deps) or len(set(deps)) != len(deps):
            raise ValueError(f"{oid}: expected unique dependency IDs")
        if any(d not in seen for d in deps):
            raise ValueError(f"{oid}: dependency cycle, unknown dependency, or incorrect operation order")
        refs = [op[k] for k in ('left','right','body') if k in op]
        if any(not isinstance(d,str) for d in refs) or set(deps) != set(refs):
            raise ValueError(f"{oid}: dependencies must match body references")
        if op.get('frame') != 'world':
            raise ValueError(f"{oid}: only the world frame is supported")
        sources = op.get('evidence')
        if not isinstance(sources,list) or any(not isinstance(e,str) or e not in ids for e in sources):
            raise ValueError(f"{oid}: unknown evidence reference")
        ancestry[oid] = {oid}.union(*(ancestry[d] for d in deps))
        native['operations'].append({k:v for k,v in op.items() if k not in {'frame','depends_on','evidence'}})
        seen.add(oid)
    edited_native, resolved = validate_recipe(native, updates)
    bodies = recipe.get('bodies')
    if not isinstance(bodies,list) or len(bodies) != 1 or not isinstance(bodies[0],dict) or set(bodies[0]) != {'id','output'}:
        raise ValueError("This backend requires one declared output body")
    body = bodies[0]
    if not isinstance(body['id'],str) or not NAME.fullmatch(body['id']) or body['output'] != recipe['output']:
        raise ValueError("Declared body must name the recipe output")
    constraints = recipe.get('constraints')
    if not isinstance(constraints,list) or len(constraints) > 128:
        raise ValueError("Expected at most 128 connection constraints")
    constraint_ids = set()
    for c in constraints:
        if not isinstance(c,dict) or set(c) != {'id','kind','left','right','min_volume_mm3'} or c.get('kind') != 'connected':
            raise ValueError("Supported constraint: connected with left, right and min_volume_mm3")
        cid = c['id']
        if not isinstance(cid,str) or not NAME.fullmatch(cid) or cid in constraint_ids:
            raise ValueError("Connection IDs must be unique valid names")
        constraint_ids.add(cid)
        for key in ('left','right'):
            if not isinstance(c[key],str) or c[key] not in ancestry[recipe['output']]:
                raise ValueError(f"{cid}: connection must reference a feature used in the final body")
        if c['left'] == c['right'] or number(c['min_volume_mm3']) <= 0:
            raise ValueError(f"{cid}: require distinct features and positive overlap volume")
    edited = copy.deepcopy(recipe)
    edited['parameters'] = edited_native['parameters']
    return edited, resolved
