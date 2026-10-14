"""Live drawing-to-BRep benchmark; keep all failures and native 3D artifacts."""
import json
import os
from pathlib import Path
import secrets
import shutil
import time
import httpx

ROOT=Path(__file__).resolve().parents[1]
OUT=Path(os.getenv('BREP_EVIDENCE_DIR',str(ROOT/'docs/brep/task-06')))
BASE=os.getenv('DOODLE_TEST_URL','http://127.0.0.1:8086')
OUT.mkdir(parents=True,exist_ok=True)
selection=OUT/'selection.json'
if not selection.exists():
    candidates=sorted(p.name for p in (ROOT/'benchmarks/cases').iterdir() if (p/'source/drawing.png').exists() and not p.name.startswith(('001_','006_')))
    selection.write_text(json.dumps({'selected':secrets.choice(candidates),'candidates':candidates},indent=2))
selected=json.loads(selection.read_text())['selected']
cases={'wheel':ROOT/'benchmarks/brep-baseline/wheel/drawing.png',
       'bookend':ROOT/'benchmarks/cases/001_l_bookend_multiview/source/drawing.png',
       'knob':ROOT/'benchmarks/cases/006_stepped_knob/source/drawing.png',
       'random':ROOT/'benchmarks/cases'/selected/'source/drawing.png'}
requested=os.getenv('BREP_CASES','').split(',')
summary=json.loads((OUT/'summary.json').read_text()) if (OUT/'summary.json').exists() else {}
with httpx.Client(base_url=BASE,timeout=60) as client:
 for name,path in cases.items():
    if requested!=[''] and name not in requested:continue
    target=OUT/name;target.mkdir(exist_ok=True)
    shutil.copy2(path,target/'input.png')
    response=client.post('/api/generate',files={'image':('drawing.png',path.read_bytes(),'image/png')},data={'backend':'usd-brep','notes':'','dimension':'120'})
    response.raise_for_status();job=response.json()['job_id']
    print(name,job,'started',flush=True)
    deadline=time.monotonic()+2400
    while time.monotonic()<deadline:
        status=client.get('/api/generate/'+job).json()
        if status['status'] not in ('running','cancelling'):break
        time.sleep(2)
    else:raise TimeoutError(job)
    (target/'job.json').write_text(json.dumps(status,indent=2))
    source=Path(os.getenv('DOODLE_TEST_RESULTS_DIR',str(ROOT/'results/brep-direct-product')))/job
    # Complete audit bundle: input, interpretation, prompts, recipe, logs, native outputs.
    if source.exists():shutil.copytree(source,target/'artifacts'/job,dirs_exist_ok=True)
    summary[name]={'id':job,'source':str(path.relative_to(ROOT)),'status':status['status'],'error':status.get('error')}
    with (OUT/'history.jsonl').open('a') as history:history.write(json.dumps({'case':name,**summary[name]})+'\n')
    (OUT/'summary.json').write_text(json.dumps(summary,indent=2))
    print(name,status['status'],status.get('error'),flush=True)
print(json.dumps(summary,indent=2),flush=True)
