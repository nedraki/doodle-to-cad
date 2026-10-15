"""Independent benchmark measurements. This module is never generation input."""
import json,os
from pathlib import Path
import numpy as np
import trimesh
from doodle_to_cad.brep_checks import section_check
from scripts.check_brep_drawing_features import rounded,bevel,handle
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'docs/brep/task-43'/os.getenv('BREP_TRIAL','trial-01')

def measure(path,name,edited=False):
    original=trimesh.load(path,force='mesh');mesh=original.copy()
    # Translation only. A wrong plane, scale or profile must still fail.
    mesh.apply_translation(-mesh.bounds[0])
    if name=='handle':
        R=24 if edited else 20
        mesh.apply_translation([-(R+4),-30,0])
        expected=[2*(R+4),30+R+4,8]
        sections=[section_check(mesh,2,4,[handle(R)],1)]
        # Both straight ends retain a circular Ø8 section in XZ.
        a=np.linspace(0,2*np.pi,257)
        circles=[np.c_[x+4*np.cos(a),4+4*np.sin(a)] for x in [-R,R]]
        sections.append(section_check(mesh,1,-15,circles,1))
        tol=np.asarray(expected)*.02
    elif name=='rounded':
        r=8 if edited else 6;expected=[80,50,30];tol=.5
        sections=[section_check(mesh,2,z,[rounded(80,50,r)],.25) for z in [.01,5,15,25,29.99]]
    elif name=='bevel':
        d=3 if edited else 2;expected=[60,40,20];tol=.5
        sections=[section_check(mesh,axis,pos,[bevel(*dims,d)],.25) for axis,pos,dims in [(2,10,(60,40)),(1,20,(60,20)),(0,30,(40,20))]]
    else:
        return {'scope':'regression geometry only; use saved drawing checks for interpretation','extents_mm':original.extents.tolist(),'watertight':bool(original.is_watertight),'components':len(original.split())}
    dimensions=bool(np.all(np.abs(original.extents-expected)<=tol))
    valid=bool(original.is_watertight and len(original.split())==1)
    return {'status':'passed' if dimensions and valid and all(c['status']=='passed' for c in sections) else 'failed',
            'extents_mm':original.extents.tolist(),'expected_extents_mm':expected,'dimensions_passed':dimensions,'geometry_passed':valid,
            'sections':sections,'world_bounds_mm':original.bounds.tolist(),'scope':'Independent mesh dimensions and sections; does not replace human view/intent review'}

def main():
    report={}
    for name,case in json.loads((OUT/'summary.json').read_text()).items():
        target=OUT/name
        if case['status']!='done':report[name]={'status':'build_failed','error':case['error']};continue
        local=ROOT/'results/brep-rich'/case['id']
        result=json.loads((local/'result.json').read_text())
        path=local/Path(result['files']['stl']).relative_to('/results/'+case['id'])
        report[name]={'original':measure(path,name),'drawing_checks':result['evaluation']}
        if (target/'edited.stl').exists():
            report[name]['edited']=measure(target/'edited.stl',name,True)
            before=report[name]['original'];after=report[name]['edited']
            if name in ['rounded','bevel']:
                b=np.array(before['world_bounds_mm']);a=np.array(after['world_bounds_mm'])
                report[name]['protected_dimensions_passed']=bool(np.max(abs(b-a))<=.05)
            elif name=='handle':report[name]['protected_dimensions_passed']=bool(abs(before['extents_mm'][2]-after['extents_mm'][2])<=.05 and after['status']=='passed')
    (OUT/'measurements.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:{'original':v.get('original',{}).get('status',v.get('status')),'edited':v.get('edited',{}).get('status'),'preserved':v.get('protected_dimensions_passed')} for k,v in report.items()},indent=2))
if __name__=='__main__':main()
