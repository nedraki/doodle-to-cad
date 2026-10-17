"""Probe native face matching without changing the published worker contract yet."""
import sys,json
from pathlib import Path
import numpy as np,trimesh,usd_brep as sm
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'workers/brep'))
from selection_catalog import catalog
OUT=ROOT/'docs/brep/task-14/native-probe';OUT.mkdir(exist_ok=True)
for width in [60,70]:
 blank=sm.create_box((0,0,0),width,5,80);tool=sm.create_box((10,-1,20),10,7,15);body=sm.boolean_difference(blank.copy(),tool.copy())
 arrays=sm.tessellate(body,chord_height_tolerance=.05).to_mesh_arrays();stream=arrays['faces'];faces=[];i=0
 while i<len(stream):
  assert stream[i]==3;faces.append(stream[i+1:i+4]);i+=4
 mesh=trimesh.Trimesh(vertices=arrays['points'],faces=faces,process=True)
 ops=[{'id':'blank','kind':'box','depends_on':[]},{'id':'tool','kind':'box','depends_on':[]},{'id':'cutout','kind':'difference','left':'blank','right':'tool','depends_on':['blank','tool']}]
 data=catalog(sm,body,{'blank':blank,'tool':tool,'cutout':body},ops,'cutout',mesh)
 cutout=next(t for t in data['targets'] if t['rule']['kind']=='box_cutout');assert cutout['match_count']==4
 mesh.export(OUT/f'width-{width}.stl');sm.usd.export_brep(body,str(OUT/f'width-{width}.usda'))
 (OUT/f'width-{width}.json').write_text(json.dumps(data,indent=2));print(width,[(t['label'],t['match_count']) for t in data['targets']],flush=True)
