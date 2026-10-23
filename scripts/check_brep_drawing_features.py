"""Deterministic feature checks. Reference recipes are NEVER generation input."""
import json, math, os
from pathlib import Path
import numpy as np
import trimesh
from doodle_to_cad.brep import build_brep
from doodle_to_cad.build_contract import BuildInput
from doodle_to_cad.brep_checks import section_check
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'docs/brep/task-07'

def rounded(w,h,r):
    points=[]
    for cx,cy,start in [(w-r,h-r,0),(r,h-r,90),(r,r,180),(w-r,r,270)]:
        for a in np.linspace(start,start+90,65):points.append([cx+r*math.cos(math.radians(a)),cy+r*math.sin(math.radians(a))])
    return points+[points[0]]

def bevel(w,h,d):
    return [[d,0],[w-d,0],[w,d],[w,h-d],[w-d,h],[d,h],[0,h-d],[0,d],[d,0]]

def handle(R=20,r=4,L=30):
    pts=[[-R-r,-L],[-R-r,0]]
    pts += [[(R+r)*math.cos(a),(R+r)*math.sin(a)] for a in np.linspace(math.pi,0,257)]
    pts += [[R+r,-L],[R-r,-L],[R-r,0]]
    pts += [[(R-r)*math.cos(a),(R-r)*math.sin(a)] for a in np.linspace(0,math.pi,257)]
    return pts+[[-R+r,-L],pts[0]]

def recipe(ops):return {'version':1,'units':'mm','parameters':{},'operations':ops,'output':ops[-1]['id']}
def box(size):return {'id':'box','kind':'box','origin':[0,0,0],'size':size}
def main():
    OUT.mkdir(parents=True,exist_ok=True)
    cases={
      'rounded':(recipe([box([80,50,30]),{'id':'rounded','kind':'fillet','body':'box','radius':6,'selector':'parallel_z'}]),rounded(80,50,6),[5,15,25],.25),
      'bevel':(recipe([box([60,40,20]),{'id':'bevel','kind':'chamfer','body':'box','radius':2*math.sqrt(2)}]),bevel(60,40,2),[5,10,15],.25),
      'handle':(recipe([{'id':'arc','kind':'arc_pipe','origin':[0,0,4],'bend_radius':20,'radius':4,'angle':180},
        {'id':'left','kind':'cylinder','origin':[-20,-30,4],'axis':'y','height':30,'radius':4},
        {'id':'right','kind':'cylinder','origin':[20,-30,4],'axis':'y','height':30,'radius':4},
        {'id':'join','kind':'union','left':'arc','right':'left'}, {'id':'part','kind':'union','left':'join','right':'right'}]),handle(),[4],1.)}
    report={}
    for name,(source,contour,levels,tol) in cases.items():
        out=OUT/name;out.mkdir(exist_ok=True)
        path=out/'reference.recipe.json';path.write_text(json.dumps(source,indent=2))
        built=build_brep(BuildInput('usd-brep',path,out,render=False))
        if not built.ok:
            report[name]={'build':'failed','diagnostics':[d.message for d in built.diagnostics]};continue
        mesh=trimesh.load(built.stl,force='mesh')
        positive=[section_check(mesh,2,z,[contour],tol) for z in levels]
        bounds=mesh.bounds
        wrong=trimesh.creation.box(extents=mesh.extents,transform=trimesh.transformations.translation_matrix(bounds.mean(axis=0)))
        negative=section_check(wrong,2,levels[0],[contour],tol)
        # A round section must not pass the rectangular-profile contract.
        report[name]={'build':'passed','measurements':built.measurements,'positive':positive,'wrong_sharp_or_straight_candidate':negative,'source':'deterministic reference, not generated'}
    circle=trimesh.creation.cylinder(radius=4,height=10,sections=128)
    rect=[[-3,-2],[3,-2],[3,2],[-3,2],[-3,-2]]
    rectangular=trimesh.creation.box(extents=[6,4,10])
    report['section_type']={'rectangular':section_check(rectangular,2,0,[rect],.25),'wrong_circle':section_check(circle,2,0,[rect],.25)}
    (OUT/'feature-report.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))
    assert all(r['build']=='passed' and all(c['status']=='passed' for c in r['positive']) and r['wrong_sharp_or_straight_candidate']['status']=='failed' for k,r in report.items() if k!='section_type')
    assert report['section_type']['rectangular']['status']=='passed' and report['section_type']['wrong_circle']['status']=='failed'
if __name__=='__main__':main()
