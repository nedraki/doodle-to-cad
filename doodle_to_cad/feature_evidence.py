"""Opt-in drawing interpretation. References are checked; claims remain hypotheses."""
import copy
import re

PROMPT = """Interpret the supplied doodle and measured regions, without CAD instructions.
Return a JSON object with exactly: version (1), object_hypothesis (string), features
(list), relationships (list), assumptions (list of strings), unresolved (list of
strings), conflicts (list of strings).
Each feature has exactly id, type, description, status, evidence, reason.
Each relationship has exactly id, type, features (list of feature IDs), description,
status, evidence, reason. IDs are short unique names. Status is observed, inferred,
or unresolved. Evidence is a list of {view_id, region_id} from the supplied catalog.
Use only supplied IDs; never invent measured regions. An entire view can support a
feature whose boundary OpenCV did not isolate. Explain that limit in reason.
Feature types: body, profile, hub, rim, spoke, opening, wall, cavity, step, flange,
neck, other. Relationship types: connected, repeated, shared_dimension, hollow,
position, symmetry, other.
Separate visible 2D facts from inferred 3D relationships. A visible join suggests a
connection but does not prove hidden depth continuity. Record every spoke-to-hub and
spoke-to-rim connection, individually or as a repeated group. Record cutout positions
using measured profile references; do not center, equalize or resize them by habit.
Compare shared dimensions between views. For stepped silhouettes, preserve unequal
flange widths and step heights unless evidence supports equality. Do not turn equal
projections into proof of roundness; classify axisymmetry as inferred when appropriate.
Do not infer a shell, cavity, wall thickness, hidden opening or open side from an
outer outline alone. Keep hidden geometry unresolved. An inner contour may be a hole,
pocket, rim or separate feature; preserve alternatives unless another view resolves
it. Top-view inner contours do not by themselves prove a bottom opening. Preserve
contradictory views in conflicts. View assignments are a spatial heuristic, not fact.
Reference the drawing, not a presumed object name. No executable recipe, kernel
selection, OpenSCAD, Python, or invented physical dimensions. Keep text concise.
"""


def region_catalog(evidence):
    """Expose measured regions without replacing OpenCV IDs or coordinates."""
    catalog=[]
    for view in evidence.get('view_geometry', []):
        vid=str(view['view_id'])
        base={'view_id':vid,'direction':view.get('direction','unassigned'),
              'sheet_bbox_normalized':view['sheet_bbox_normalized'],
              'cad_mapping':view.get('cad_mapping',{}),
              'view_assignment':'spatial heuristic'}
        catalog.append({**base,'region_id':'view','kind':'view',
                        'bbox_view_normalized':[0,0,1,1],
                        'measured_span_pixels':view['measured_span_pixels']})
        profiles=[('outer',view.get('outer_profile'))]+[('internal',p) for p in view.get('internal_profiles',[])]
        for kind,profile in profiles:
            if profile:
                catalog.append({**base,'region_id':'profile_'+str(profile['profile_id']),
                                'kind':kind,**copy.deepcopy(profile)})
    return catalog


def validate_interpretation(raw, catalog):
    fields={'version','object_hypothesis','features','relationships','assumptions','unresolved','conflicts'}
    if not isinstance(raw,dict) or set(raw)!=fields or type(raw.get('version')) is not int or raw['version']!=1:
        raise ValueError('Expected feature-evidence version 1 and its declared fields')
    def text(value):
        if not isinstance(value,str) or not 1<=len(value)<=2000:
            raise ValueError('Expected text with 1–2000 characters')
    text(raw['object_hypothesis'])
    for key in ('assumptions','unresolved','conflicts'):
        if not isinstance(raw[key],list) or len(raw[key])>128:
            raise ValueError(f'{key}: expected at most 128 entries')
        for value in raw[key]:text(value)
    regions={(r['view_id'],r['region_id']):r for r in catalog}
    seen=set();feature_ids=set();result=copy.deepcopy(raw);warnings=[];unresolved_warnings=[]
    for category in ('features','relationships'):
        entries=result[category]
        if not isinstance(entries,list) or len(entries)>128:
            raise ValueError(f'{category}: expected at most 128 entries')
        for entry in entries:
            expected={'id','type','description','status','evidence','reason'} | ({'features'} if category=='relationships' else set())
            if not isinstance(entry,dict) or set(entry)!=expected:
                raise ValueError(f'{category}: invalid fields')
            eid=entry['id']
            if not isinstance(eid,str) or not re.fullmatch(r'[A-Za-z][A-Za-z0-9_]{0,63}',eid) or eid in seen:
                raise ValueError('IDs must be unique short names')
            seen.add(eid)
            allowed=({'body','profile','hub','rim','spoke','opening','wall','cavity','step','flange','neck','other'} if category=='features' else {'connected','repeated','shared_dimension','hollow','position','symmetry','other'})
            if not isinstance(entry['type'],str) or entry['type'] not in allowed:
                raise ValueError(f'{eid}: unsupported feature or relationship type')
            if entry['status'] not in ('observed','inferred','unresolved'):
                raise ValueError(f'{eid}: expected observed, inferred or unresolved')
            text(entry['description']);text(entry['reason'])
            refs=entry['evidence']
            if not isinstance(refs,list) or len(refs)>64:
                raise ValueError(f'{eid}: expected at most 64 evidence references')
            for ref in refs:
                if not isinstance(ref,dict) or set(ref)!={'view_id','region_id'} or not all(isinstance(v,str) for v in ref.values()) or (ref['view_id'],ref['region_id']) not in regions:
                    raise ValueError(f'{eid}: unknown measured region')
            if category=='relationships':
                links=entry['features']
                if not isinstance(links,list) or not links or len(links)>128 or any(not isinstance(f,str) or f not in feature_ids for f in links):
                    raise ValueError(f'{eid}: unknown feature reference')
            else:feature_ids.add(eid)
            if entry['type']=='connected' and entry['status']=='observed':
                entry['model_status']='observed';entry['status']='inferred'
                entry['review_note']='Visible projected continuity does not prove a connected 3D solid.'
                warnings.append(f"{eid}: {entry['review_note']}")
            reason=None
            if not refs and entry['status']!='unresolved':
                reason='No source region supports this claim.'
            if entry['type'] in {'wall','cavity','hollow'}:
                views={r['view_id'] for r in refs}
                if not any(r['kind']=='internal' and r['view_id'] in views for r in catalog):
                    reason='Outer outlines alone do not establish hidden wall or cavity geometry.'
            if entry['type']=='shared_dimension' and len({r['view_id'] for r in refs})<2:
                reason='Shared dimensions require evidence from at least two views.'
            if reason and entry['status']!='unresolved':
                entry.setdefault('model_status',entry['status']);entry['status']='unresolved'
                entry['review_note']=reason
                warnings.append(f'{eid}: {reason}');unresolved_warnings.append(f'{eid}: {reason}')
    result['unresolved']+=unresolved_warnings
    result['review']={'reference_integrity_checked':True,'drawing_fidelity_verified':False,
                      'policy_warnings':warnings,'executable':False}
    return result


def shared_axis_evidence(catalog):
    """Compare measured spans only on axes shared by assigned projections.

    Equal drawing scale is an assumption. This is evidence, not a physical dimension.
    """
    from itertools import combinations
    spans=[]
    for region in catalog:
        if region['kind']!='view':continue
        mapping=region.get('cad_mapping',{})
        for field,span in [('u_maps_to','horizontal_axis_u'),('v_maps_to','vertical_axis_v')]:
            axis=mapping.get(field,'')[-1:]
            if axis in ('X','Y','Z'):
                spans.append((axis,region['view_id'],region['measured_span_pixels'][span]))
    results=[]
    for left,right in combinations(spans,2):
        if left[0]!=right[0] or left[1]==right[1]:continue
        delta=abs(left[2]-right[2])/max(left[2],right[2],1)
        results.append({'axis':left[0], 'evidence':[{'view_id':v[1],'region_id':'view'} for v in (left,right)],
                        'measured_spans_pixels':[left[2],right[2]], 'relative_difference':round(delta,4),
                        'status':'consistent_spans' if delta<=.1 else 'review_required',
                        'assumption':'Views use the same drawing scale and their assigned directions are correct.',
                        'physical_dimension_verified':False})
    return results


def view_assignment_evidence(evidence):
    """Exclude tiny groups from direction assignment, but retain their regions.

    Text labels can otherwise displace real projections. This opt-in heuristic is
    deliberately recorded, since a tiny group could instead be a real detail view.
    """
    result=copy.deepcopy(evidence)
    groups=result.get('view_groups',[])
    def area(group):
        box=group['bbox_normalized']
        return box[2]*box[3]
    largest=max((area(g) for g in groups),default=0)
    excluded=[g['view_id'] for g in groups if area(g)<largest*.05]
    result['view_groups']=[g for g in groups if g['view_id'] not in excluded]
    result['interpretation_view_filter']={
        'excluded_from_direction_assignment':excluded,
        'rule':'Groups below 5% of the largest group box area remain unassigned; they may be text or detail views.',
        'regions_retained':True}
    return result
