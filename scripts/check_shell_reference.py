"""Independent rounded tray wall, floor, cavity and outside-size checks."""
import json,math,shutil
from pathlib import Path
import numpy as np,trimesh
from doodle_to_cad.brep_checks import section_check
from doodle_to_cad.brep import build_brep
from doodle_to_cad.build_contract import BuildInput
ROOT=Path(__file__).resolve().parents[1]

def outline(x,y,w,h,r):
 points=[]
 for (cx,cy),start in zip([(x+w-r,y+r),(x+w-r,y+h-r),(x+r,y+h-r),(x+r,y+r)],[-90,0,90,180]):
  a=np.linspace(math.radians(start),math.radians(start+90),129);points.extend(np.c_[cx+r*np.cos(a),cy+r*np.sin(a)].tolist())
 return points+[points[0]]

def measure(path,t):
 mesh=trimesh.load(path,force='mesh');mesh.apply_translation(-mesh.bounds[0])
 outer=outline(0,0,60,40,6);inner=outline(t,t,60-2*t,40-2*t,6-t)
 sections=[section_check(mesh,2,z,[outer]+([inner] if z>t else []),.25) for z in [t/2,t-.1,t+.1,10,19.9]]
 for axis,width,at in [(1,60,20),(0,40,30)]:
  u=[[0,0],[width,0],[width,20],[width-t,20],[width-t,t],[t,t],[t,20],[0,20],[0,0]]
  sections.append(section_check(mesh,axis,at,[u],.25))
 expected=20*(2400-(4-math.pi)*36)-(20-t)*((60-2*t)*(40-2*t)-(4-math.pi)*(6-t)**2)
 return {'extents_mm':mesh.extents.tolist(),'wall_and_floor_mm':t,'expected_inner_extents_mm':[60-2*t,40-2*t,20-t],'volume_mm3':float(mesh.volume),'expected_volume_mm3':expected,'sections':sections,'watertight':bool(mesh.is_watertight),'components':len(mesh.split()),'passed':bool(mesh.is_watertight and len(mesh.split())==1 and np.all(abs(mesh.extents-[60,40,20])<.25) and abs(mesh.volume-expected)/expected<.005 and all(s['status']=='passed' for s in sections))}

if __name__=='__main__':
 out=ROOT/'docs/brep/task-12/reference';out.mkdir(exist_ok=True);report={}
 for t in [2,3]:
  target=out/str(t);target.mkdir(exist_ok=True);r=json.loads((ROOT/'benchmarks/brep-shells/reference.recipe.json').read_text());r['parameters']['thickness']['value']=t
  source=target/'recipe.json';source.write_text(json.dumps(r,indent=2));b=build_brep(BuildInput('usd-brep',source,target,render=False));(target/'build.log').write_text(b.log);assert b.ok,b.log
  shutil.copy(b.stl,target/'part.stl');report[str(t)]=measure(target/'part.stl',t)
 box=trimesh.creation.box(extents=[60,40,20]);box.export(out/'negative-solid.stl');report['negative_solid']=measure(out/'negative-solid.stl',2)
 (out/'report.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
 assert report['2']['passed'] and report['3']['passed'] and not report['negative_solid']['passed']
