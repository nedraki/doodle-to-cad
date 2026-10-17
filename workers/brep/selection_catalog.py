"""Bounded native targets and their actual mesh/edge overlays for one build."""
import hashlib
import json
import numpy as np
from doodle_to_cad.selection_rules import match_faces, outer_vertical_edges, TOLERANCE


def catalog(sm, body, bodies, operations, output_id, mesh):
    bounds=sm.brep_bounding_box(body)
    native_faces=body.faces()
    face_bounds=[sm.face_bounding_box(f,tight=True) for f in native_faces]
    body_bounds={name:sm.brep_bounding_box(b) for name,b in bodies.items()}
    rules=[]
    for axis in range(3):
        for side in ['min','max']:
            rules.append((f'Outside {"XYZ"[axis]} {side} face',{'kind':'extreme_face','owner':output_id,'axis':axis,'side':side}))
    for op in operations:
        if op['kind']=='difference' and next((x['kind'] for x in operations if x['id']==op['right']),None)=='box':
            rules.append((f'Cutout {op["id"]}',{'kind':'box_cutout','owner':op['id'],'cutter':op['right'],'expected_faces':4}))
    triangles=np.asarray(mesh.triangles);centers=triangles.mean(axis=1)
    targets=[];unresolved=[]
    def append(label,rule,geometry,count):
        identity=hashlib.sha256(json.dumps(rule,sort_keys=True).encode()).hexdigest()[:16]
        targets.append({'id':identity,'label':label,'rule':rule,'match_count':count,'geometry':geometry})
    for label,rule in rules:
        match=match_faces(rule,output_id,bounds,face_bounds,operations,body_bounds)
        if match['status']!='matched':
            unresolved.append({'rule':rule,'status':match['status'],'reason':match['reason']});continue
        indices=set()
        for face_index in match['indices']:
            lo,hi=np.asarray(face_bounds[face_index]);face=native_faces[face_index]
            possible=np.where(np.all((centers>=lo-TOLERANCE)&(centers<=hi+TOLERANCE),axis=1))[0]
            for i in possible:
                # closest_point respects the trimmed face, including its holes.
                _,distance=face.closest_point(tuple(centers[i]))
                if distance<TOLERANCE:indices.add(int(i))
        if not indices:continue
        append(label,rule,{'triangles':triangles[sorted(indices)].reshape(-1,3).tolist()},len(match['indices']))
    native_edges=body.edges();edge_bounds=[sm.edge_bounding_box(e,tight=True) for e in native_edges]
    edges=outer_vertical_edges(bounds,edge_bounds)
    if edges:
        lines=[]
        for i in edges:
            e=native_edges[i];a,b=e.parameter_range();lines.append([e.point_at(a),e.point_at(b)])
        append('Outer vertical edges',{'kind':'outer_vertical_edges','owner':output_id,'expected_edges':len(edges)}, {'lines':lines},len(edges))
    return {'version':1,'status':'available','unresolved':unresolved,'output_owner':output_id,'targets':targets,
            'supported':'Axis-aligned extreme planar faces, four-wall box cutouts and straight outer vertical edges. Recheck after every rebuild.'}
