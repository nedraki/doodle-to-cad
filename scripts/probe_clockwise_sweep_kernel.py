"""Record the kernel's unsupported direct clockwise construction, without repair."""
import usd_brep as sm,math
from pathlib import Path
out=Path('docs/brep/task-10/probe');out.mkdir(parents=True,exist_ok=True)
p=[(0,0,0),(6,0,0),(6,0,8),(0,0,8),(0,0,0)]
profile=[sm.create_line_segment(a,b) for a,b in zip(p,p[1:])]
path=[sm.create_line_segment((3,0,4),(3,15,4)),sm.create_arc((23,15,4),20,180,0),sm.create_line_segment((43,15,4),(43,0,4))]
b=sm.sweep_along_planar_path(profile,path,move_profile=True)
print('solid',b.is_manifold_solid(),'volume',b.volume(relative_accuracy=1e-8),'expected',48*(30+20*math.pi),'bounds',sm.brep_bounding_box(b))
p=out/'clockwise-invalid.usda';sm.usd.export_brep(b,str(p))
print('reloaded',[x.volume(relative_accuracy=1e-8) for x in sm.usd.import_breps(str(p))])
