"""Independent end/mid-section and volume contract for the rectangular-to-round loft."""
import json,math,shutil
from pathlib import Path
import numpy as np,trimesh
from doodle_to_cad.brep_checks import section_check
from doodle_to_cad.brep import build_brep
from doodle_to_cad.build_contract import BuildInput
ROOT=Path(__file__).resolve().parents[1]

def contour(width,z):
 corners=np.array([[width/2,15],[-width/2,15],[-width/2,-15],[width/2,-15],[width/2,15]])
 points=[];t=np.linspace(0,1,257)[:,None];weight=math.sqrt(.5)
 for i,a in enumerate([45,135,225,315]):
  a=math.radians(a);p0=10*np.array([math.cos(a),math.sin(a)]);p1=10/weight*np.array([math.cos(a+math.pi/4),math.sin(a+math.pi/4)]);p2=10*np.array([math.cos(a+math.pi/2),math.sin(a+math.pi/2)])
  arc=((1-t)**2*p0+2*weight*t*(1-t)*p1+t*t*p2)/((1-t)**2+2*weight*t*(1-t)+t*t)
  line=(1-t)*corners[i]+t*corners[i+1]
  points.extend(((1-z/50)*line+(z/50)*arc)[:-1].tolist())
 return points+[points[0]]

def measure(path,width):
 mesh=trimesh.load(path,force='mesh');mesh.apply_translation([-mesh.bounds[:,0].mean(),-mesh.bounds[:,1].mean(),-mesh.bounds[0,2]])
 sections=[section_check(mesh,2,z,[contour(width,z)],.25) for z in [.1,12.5,25,37.5,49.9]]
 mid=np.array(contour(width,25));area=abs(np.sum(mid[:-1,0]*mid[1:,1]-mid[1:,0]*mid[:-1,1]))/2
 expected=50*(width*30+4*area+math.pi*100)/6
 return {'extents_mm':mesh.extents.tolist(),'volume_mm3':float(mesh.volume),'expected_volume_mm3':expected,'sections':sections,'watertight':bool(mesh.is_watertight),'components':len(mesh.split()),'passed':bool(mesh.is_watertight and len(mesh.split())==1 and np.all(abs(mesh.extents-[width,30,50])<.25) and abs(mesh.volume-expected)/expected<.005 and all(s['status']=='passed' for s in sections))}

if __name__=='__main__':
 out=ROOT/'docs/brep/task-11/reference';out.mkdir(exist_ok=True);report={}
 for width in [40,48]:
  target=out/str(width);target.mkdir(exist_ok=True);r=json.loads((ROOT/'benchmarks/brep-lofts/reference.recipe.json').read_text());r['parameters']['rectangle_width']['value']=width
  source=target/'recipe.json';source.write_text(json.dumps(r,indent=2));b=build_brep(BuildInput('usd-brep',source,target,render=False));(target/'build.log').write_text(b.log);assert b.ok,b.log
  shutil.copy(b.stl,target/'part.stl');report[str(width)]=measure(target/'part.stl',width)
 box=trimesh.creation.box(extents=[40,30,50]);box.export(out/'negative-box.stl');report['negative_box']=measure(out/'negative-box.stl',40)
 (out/'report.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
 assert report['40']['passed'] and report['48']['passed'] and not report['negative_box']['passed']
