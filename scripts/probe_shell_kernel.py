"""Uniform inward shell of a rounded tray; retain the outside dimensions."""
from pathlib import Path
import usd_brep as sm,math
OUT=Path('docs/brep/task-12/probe');OUT.mkdir(exist_ok=True)
for t in [2,3,25]:
 try:
  b=sm.create_box((0,0,0),60,40,20)
  edges=[]
  for e in b.edges():
   lo,hi=sm.edge_bounding_box(e,tight=True)
   if hi[2]-lo[2]>1 and abs(hi[0]-lo[0])<1e-6 and abs(hi[1]-lo[1])<1e-6:edges.append(e)
  sm.fillet_edges(b,edges,radius=6)
  faces=[]
  for f in b.faces():
   lo,hi=sm.face_bounding_box(f,tight=True)
   if abs(lo[2]-20)<1e-4 and abs(hi[2]-20)<1e-4:faces.append(f)
  result=sm.shell_brep(b,-t,faces_to_shell=faces)
  path=OUT/f'thickness-{t}.usda';sm.usd.export_brep(result,str(path))
  print(t,'opening_faces',len(faces),'solid',result.is_manifold_solid(),'volume',result.volume(relative_accuracy=1e-8),'expected',20*(2400-(4-math.pi)*36)-(20-t)*((60-2*t)*(40-2*t)-(4-math.pi)*(6-t)**2),'bounds',sm.brep_bounding_box(result),'reload',[(x.is_manifold_solid(),x.volume(relative_accuracy=1e-8)) for x in sm.usd.import_breps(str(path))],flush=True)
 except Exception as e:print(t,type(e).__name__,str(e),flush=True)
