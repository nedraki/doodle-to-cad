import usd_brep as sm,math,json
from pathlib import Path
out=Path('docs/brep/task-10/probe');out.mkdir(exist_ok=True)
points=[(17,-15,0),(23,-15,0),(23,-15,8),(17,-15,8),(17,-15,0)]
profile=[sm.create_line_segment(a,b) for a,b in zip(points,points[1:])]
path=[sm.create_line_segment((20,-15,4),(20,0,4)),sm.create_arc((0,0,4),20,0,180),sm.create_line_segment((-20,0,4),(-20,-15,4))]
for move in [True,False]:
 try:
  b=sm.sweep_along_planar_path(profile,path,move_profile=move);p=out/f'move-{move}.usda';sm.usd.export_brep(b,str(p));reloaded=sm.usd.import_breps(str(p));print('MOVE',move,'solid',b.is_manifold_solid(),'volume',b.volume(relative_accuracy=1e-8),'expected',48*(30+20*math.pi),'bounds',sm.brep_bounding_box(b),'reload',[(x.is_manifold_solid(),x.volume(relative_accuracy=1e-8)) for x in reloaded],flush=True)
 except Exception as e:print(type(e).__name__,str(e),flush=True)
