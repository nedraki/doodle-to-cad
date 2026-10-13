"""Task 04: opt-in developer UI, persisted jobs, edits, downloads, cancellation."""
import json
import os
from pathlib import Path
import subprocess
import time

import httpx
from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'docs/brep/task-04';OUT.mkdir(parents=True,exist_ok=True)
BASE=os.getenv('DOODLE_TEST_URL','http://127.0.0.1:8083')
recipe=json.loads((ROOT/'benchmarks/brep-v2/bookend.json').read_text())
report={}
with sync_playwright() as p:
 browser=p.chromium.launch(headless=True,executable_path=os.environ['CHROMIUM_EXECUTABLE'],args=['--no-sandbox','--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader','--ignore-gpu-blocklist'])
 page=browser.new_page(viewport={'width':1500,'height':1200})
 errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
 page.goto(BASE)
 assert page.locator('#recipeDeveloper').count()==0
 page.goto(BASE+'/?dev=recipes')
 page.locator('#recipeFile').set_input_files(str(ROOT/'benchmarks/brep-v2/bookend.json'))
 page.click('#buildRecipe')
 page.wait_for_function('jobId !== null')
 job=page.evaluate('jobId')
 page.screenshot(path=str(OUT/'job-progress.png'))
 page.reload()
 page.wait_for_function('currentRun?.backend === "usd-brep" && viewer?.mesh',timeout=180000)
 assert page.evaluate('currentRun.id')==job
 result=page.evaluate('currentRun')
 assert result['success'] is False and 'score' not in result['evaluation']
 assert 'BRep' in page.locator('#statusBadge').inner_text()
 page.reload()
 page.wait_for_function('currentRun?.id === '+json.dumps(job)+' && viewer?.mesh',timeout=30000)
 page.evaluate('viewer.setView("isometric")')
 page.wait_for_timeout(300)
 page.locator('#result').screenshot(path=str(OUT/'bookend-result.png'))
 report['result']=result
 report['reload_during_and_after_job']=True
 page.click('#modify');page.wait_for_selector('.param-row')
 index=page.evaluate('paramState.originalParams.findIndex(p=>p.name==="hole1_width")')
 field=page.locator(f'#param-{index}-number')
 with page.expect_response(lambda r:'/parametrize' in r.url and r.request.method=='POST',timeout=180000) as pending:
  field.fill('12');field.dispatch_event('change')
 edited=pending.value.json();assert edited['ok']
 page.wait_for_function('(u)=>document.querySelector("#stl").getAttribute("href")===u',arg=edited['stl'])
 for key,selector in [('stl','#stl'),('source','#scad'),('usd','#usd')]:
  assert page.locator(selector).get_attribute('href')==edited[key]
  response=httpx.get(BASE+edited[key]);response.raise_for_status();assert response.content
 source=httpx.get(BASE+edited['source']).json();assert source['parameters']['hole1_width']['value']==12
 report['edits_and_downloads']=True
 assert not errors,errors
 browser.close()
# Cancel while the real kernel worker exists, rather than simulating a UI delay.
with httpx.Client(base_url=BASE,timeout=40) as client:
 response=client.post('/api/brep/jobs',json=recipe);response.raise_for_status();job=response.json()['job_id']
 worker_pids=[];runner=None;stages=[]
 for _ in range(1000):
  status=client.get('/api/generate/'+job).json();stages.append(status['stage'])
  if status['stage']=='building solid':
   for line in subprocess.check_output(['ps','-eo','pid,args'],text=True).splitlines():
    if 'doodle_to_cad.recipe_job_worker' in line and job in line:
     runner=int(line.split()[0]);children=Path(f'/proc/{runner}/task/{runner}/children')
     worker_pids=[int(pid) for pid in children.read_text().split()]
     break
   if worker_pids:break
  if status['status']!='running':raise AssertionError('Job completed before kernel cancellation check')
  time.sleep(.005)
 assert worker_pids,'Did not observe the real kernel worker'
 response=client.post('/api/generate/'+job+'/cancel');response.raise_for_status()
 assert response.json()['status']=='cancelled'
 status=client.get('/api/generate/'+job).json();assert status['result'] is None
 for pid in [runner]+worker_pids:
  stat=Path(f'/proc/{pid}/stat');assert not stat.exists() or stat.read_text().split()[2]=='Z'
 assert client.get('/results/'+job+'/result.json').status_code==404
 report['cancellation']={'status':status['status'],'stages':list(dict.fromkeys(stages)),'observed_kernel_processes':len(worker_pids),'processes_stopped':True,'no_published_result':True}
(OUT/'report.json').write_text(json.dumps(report,indent=2)+'\n')
print('Recipe job browser, reload, edit/download, and real kernel cancellation checks passed.')
