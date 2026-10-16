"""Fresh compatibility probes. Never guess an answer to a regression question."""
import json,random,time,shutil,os
from pathlib import Path
import httpx
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'docs/brep/task-11'/os.getenv('BREP_REGRESSION','regressions');OUT.mkdir(parents=True,exist_ok=True)
BASE=os.getenv('DOODLE_TEST_URL','http://127.0.0.1:8103')
fixed=[('wheel','benchmarks/brep-baseline/wheel/drawing.png'),('bookend','benchmarks/cases/001_l_bookend_multiview/source/drawing.png'),('knob','benchmarks/cases/006_stepped_knob/source/drawing.png'),('cable_holder','benchmarks/cases/104_cable_holder/source/drawing.png')]
remaining=sorted(p for p in (ROOT/'benchmarks/cases').glob('*/source/drawing.png') if str(p.relative_to(ROOT)) not in {s for _,s in fixed})
selected=random.Random(20261018).choice(remaining)
cases=fixed+[('random_'+selected.parent.parent.name,str(selected.relative_to(ROOT)))]
(OUT/'selection.json').write_text(json.dumps({'seed':20261018,'cases':cases},indent=2))
summary={}
with httpx.Client(base_url=BASE,timeout=60) as client:
 for name,path in cases:
  if os.getenv('BREP_CASES') and name not in os.environ['BREP_CASES'].split(','):continue
  target=OUT/name;target.mkdir(exist_ok=True);shutil.copy(ROOT/path,target/'input.png')
  form={'backend':'usd-brep','notes':'','object_type':'','dimension':'120','primary_view':'front','projection_standard':'third-angle'}
  if (target/'request.json').exists():
   job=json.loads((target/'request.json').read_text())['job']
  else:
   r=client.post('/api/generate',files={'image':('drawing.png',(ROOT/path).read_bytes(),'image/png')},data=form);r.raise_for_status();job=r.json()['job_id']
   (target/'request.json').write_text(json.dumps({'source':path,'form':form,'job':job},indent=2))
  print(name,job,flush=True)
  question=None
  for _ in range(750):
   state=client.get('/api/generate/'+job).json()
   if state['status']=='waiting_for_answer':
    question=state['question']
    for staged in (ROOT/'results').glob('.recipe-job-*/'+job):shutil.copytree(staged,target/'artifacts'/job,dirs_exist_ok=True)
    client.post('/api/generate/'+job+'/cancel');state=client.get('/api/generate/'+job).json();break
   if state['status'] in {'done','error','cancelled'}:break
   time.sleep(2)
  else:client.post('/api/generate/'+job+'/cancel');raise TimeoutError(job)
  (target/'job.json').write_text(json.dumps(state,indent=2))
  if question:(target/'question.json').write_text(json.dumps(question,indent=2))
  local=ROOT/'results/brep28'/job
  if local.exists():shutil.copytree(local,target/'artifacts'/job,dirs_exist_ok=True)
  summary[name]={'job':job,'status':state['status'],'question_requested':question is not None,'error':state.get('error'),'drawing_status':state.get('result',{}).get('evaluation',{}).get('status') if state.get('result') else None}
  (OUT/'summary.json').write_text(json.dumps(summary,indent=2));print(summary[name],flush=True)
