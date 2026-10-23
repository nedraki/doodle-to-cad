"""Live drawing trials. Contract targets are used ONLY by later measurement scripts."""
import hashlib,json,os,shutil,time
from pathlib import Path
import httpx
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'docs/brep/task-43'/os.getenv('BREP_TRIAL','trial-01')
BASE=os.getenv('DOODLE_TEST_URL','http://127.0.0.1:8089')
BACKEND=os.getenv('GENERATION_BACKEND','usd-brep')
OUT.mkdir(parents=True,exist_ok=True)
# Explicit drawing/control whitelist. No expected geometry is sent to the model.
cases=[('handle','benchmarks/brep-baseline/curved_handle/drawing.png','top',54),
 ('rounded','benchmarks/brep-features/rounded_housing/drawing.png','top',80),
 ('bevel','benchmarks/brep-features/bevelled_block/drawing.png','top',60),
 ('wheel','benchmarks/brep-baseline/wheel/drawing.png','front',120),
 ('bookend','benchmarks/cases/001_l_bookend_multiview/source/drawing.png','front',120),
 ('knob','benchmarks/cases/006_stepped_knob/source/drawing.png','front',120),
 ('cable_holder','benchmarks/cases/104_cable_holder/source/drawing.png','front',120),
 ('random_lcd_knob','benchmarks/cases/102_lcd_knob/source/drawing.png','front',50)]
requested=set(filter(None,os.getenv('BREP_CASES','').split(',')))
summary=json.loads((OUT/'summary.json').read_text()) if (OUT/'summary.json').exists() else {}
with httpx.Client(base_url=BASE,timeout=90) as client:
 for name,path,view,maximum in cases:
    if requested and name not in requested:continue
    target=OUT/name;target.mkdir(exist_ok=True)
    image=(ROOT/path).read_bytes();(target/'input.png').write_bytes(image)
    form={'backend':BACKEND,'notes':'','object_type':'','dimension':str(maximum),'primary_view':view,'projection_standard':'third-angle'}
    (target/'submitted-request.json').write_text(json.dumps({'form':form,'image_sha256':hashlib.sha256(image).hexdigest(),'source':path,'reference_geometry_sent':False},indent=2))
    response=client.post('/api/generate',files={'image':('drawing.png',image,'image/png')},data=form)
    response.raise_for_status();job=response.json()['job_id'];print(name,job,'started',flush=True)
    deadline=time.monotonic()+2400
    while time.monotonic()<deadline:
        status=client.get('/api/generate/'+job).json()
        if status['status'] not in ('running','cancelling'):break
        time.sleep(2)
    else:
        client.post('/api/generate/'+job+'/cancel');raise TimeoutError(job)
    (target/'job.json').write_text(json.dumps(status,indent=2))
    local=ROOT/'results/brep-rich'/job
    if local.exists():shutil.copytree(local,target/'artifacts'/job,dirs_exist_ok=True)
    summary[name]={'id':job,'status':status['status'],'error':status.get('error'),'source':path}
    (OUT/'summary.json').write_text(json.dumps(summary,indent=2))
    with (OUT/'history.jsonl').open('a') as f:f.write(json.dumps({'case':name,**summary[name]})+'\n')
    print(name,status['status'],status.get('error'),flush=True)
