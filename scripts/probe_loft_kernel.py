"""Explicit rectangle-corner to circular-quadrant correspondence, no healing."""
from pathlib import Path
import usd_brep as sm,json
OUT=Path('docs/brep/task-11/probe');OUT.mkdir(exist_ok=True)
for width in [40,50]:
 points=[(width/2,15,0),(-width/2,15,0),(-width/2,-15,0),(width/2,-15,0),(width/2,15,0)]
 rect=[sm.create_line_segment(a,b) for a,b in zip(points,points[1:])]
 circle=[sm.create_arc((0,0,50),10,a,a+90) for a in [45,135,225,-45]]
 try:
  b=sm.create_skin_primitive([4,4],rect+circle,degree=1,cap_ends=True)
  p=OUT/f'width-{width}.usda';sm.usd.export_brep(b,str(p));loaded=sm.usd.import_breps(str(p))
  print(width,'solid',b.is_manifold_solid(),'volume',b.volume(relative_accuracy=1e-8),'bounds',sm.brep_bounding_box(b),'reload',[(x.is_manifold_solid(),x.volume(relative_accuracy=1e-8)) for x in loaded],flush=True)
 except Exception as e:print(width,type(e).__name__,str(e),flush=True)
