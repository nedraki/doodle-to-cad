"""Live app trial: real model, question controls, native geometry and screenshots."""
import json,os,time,shutil
from pathlib import Path
import httpx
import numpy as np
import trimesh
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1]
BASE=os.getenv('DOODLE_TEST_URL','http://127.0.0.1:8095')
OUT=ROOT/'docs/brep/task-08'/os.getenv('BREP_TRIAL','trial-01');OUT.mkdir(parents=True,exist_ok=True)
cases=os.getenv('BREP_CASES','through,recess,clear,cancel').split(',')
summary={}
with sync_playwright() as p:
 browser=p.chromium.launch(headless=True,executable_path='/home/sparkie/.cache/ms-playwright/chromium-1243/chrome-linux-arm64/chrome',args=['--no-sandbox','--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader'])
 for name in cases:
  target=OUT/name;target.mkdir(exist_ok=True)
  source=ROOT/'benchmarks/brep-clarification'/('clear-through.png' if name=='clear' else 'ambiguous.png')
  shutil.copy(source,target/'input.png')
  page=browser.new_page(viewport={'width':1600,'height':1300});errors=[]
  page.on('pageerror',lambda e:errors.append(str(e)))
  page.goto(BASE)
  if (target/'request.json').exists():
   job=json.loads((target/'request.json').read_text())['job'];print(name,job,'resume saved trial',flush=True)
  else:
   page.locator('#image').set_input_files(str(source));page.wait_for_timeout(600)
   page.locator('[name=backend]').select_option('usd-brep');page.locator('[name=primary_view]').select_option('top');page.locator('[name=dimension]').fill('40')
   with page.expect_response(lambda r:r.url==BASE+'/api/generate' and r.request.method=='POST',timeout=30000) as response:
    page.locator('#launch').click()
   job=response.value.json()['job_id'];print(name,job,'started',flush=True)
   (target/'request.json').write_text(json.dumps({'source':str(source.relative_to(ROOT)),'notes':'','backend':'usd-brep','primary_view':'top','dimension':40,'job':job},indent=2))
  answered=[json.loads(p.read_text())['id'] for p in target.glob('question-*.json')];deadline=time.monotonic()+1500
  while time.monotonic()<deadline:
   state=httpx.get(BASE+'/api/generate/'+job,timeout=30).json()
   if state['status']=='waiting_for_answer':
    q=state['question']
    if q['id'] not in answered:
     page.locator('#clarificationPanel').wait_for(timeout=15000)
     page.locator('#working').screenshot(path=str(target/f'question-{len(answered)+1}.png'))
     (target/f'question-{len(answered)+1}.json').write_text(json.dumps(q,indent=2))
     if name in {'clear','cancel'}:
      page.locator('#cancelQuestion').click();answered.append(q['id'])
     else:
      page.locator(f'input[name=openingChoice][value={name}]').check()
      if name=='recess':page.locator('#clarificationForm [name=depth]').fill('5')
      page.locator('#clarificationPanel').screenshot(path=str(target/'answer.png'))
      page.locator('#clarificationForm [type=submit]').click();answered.append(q['id'])
   if state['status'] in {'done','error','cancelled'}:break
   time.sleep(2)
  else:
   httpx.post(BASE+'/api/generate/'+job+'/cancel');raise TimeoutError(job)
  (target/'job.json').write_text(json.dumps(state,indent=2))
  report={'job':job,'status':state['status'],'questions':len(answered),'error':state.get('error'),'browser_errors':errors}
  local=ROOT/'results/brep25'/job
  if state['status']=='done':
   page.evaluate('(r)=>render(r,null)',state['result'])
   page.wait_for_function('typeof viewer!=="undefined" && viewer?.mesh',timeout=30000)
   page.wait_for_timeout(1000);page.evaluate('viewer.setView("isometric")');page.wait_for_timeout(600)
   page.locator('#result').screenshot(path=str(target/'result.png'));page.locator('#viewerWrap').screenshot(path=str(target/'part.png'))
   result=state['result']
   for key in ['source','stl','usd']:
    r=httpx.get(BASE+result['files'][key]);r.raise_for_status();assert r.content
   mesh=trimesh.load(local/Path(result['files']['stl']).relative_to('/results/'+job),force='mesh')
   # Independent contract used only AFTER generation: 40×30×12, centred Ø8 opening.
   expected_volume=40*30*12-np.pi*4**2*(5 if name=='recess' else 12)
   from doodle_to_cad.brep_checks import section_check
   shifted=mesh.copy();shifted.apply_translation(-shifted.bounds[0])
   outer=[[0,0],[40,0],[40,30],[0,30],[0,0]]
   a=np.linspace(0,2*np.pi,257);hole=np.c_[20+4*np.cos(a),15+4*np.sin(a)]
   sections=[section_check(shifted,2,z,[outer]+([hole] if name!='recess' or z>7 else []),.25) for z in [1,6,8,11]]
   report['measurements']={'extents_mm':mesh.extents.tolist(),'volume_mm3':float(mesh.volume),'expected_volume_mm3':float(expected_volume),'watertight':bool(mesh.is_watertight),'components':len(mesh.split()),'sections':sections}
   report['feature_passed']=bool(np.all(abs(mesh.extents-[40,30,12])<.25) and abs(mesh.volume-expected_volume)<10 and mesh.is_watertight and len(mesh.split())==1 and all(s['status']=='passed' for s in sections))
  else:
   page.wait_for_timeout(2500);page.locator('#stage').screenshot(path=str(target/'stopped.png'))
   report['no_completed_result']=not (local/'result.json').exists()
  if local.exists():shutil.copytree(local,target/'artifacts'/job,dirs_exist_ok=True)
  report['flow_passed'] = (state['status']=='cancelled' and bool(answered) and report.get('no_completed_result',False)) if name=='cancel' else (state['status']=='done' and report.get('feature_passed',False) and (len(answered)==0 if name=='clear' else len(answered)==1))
  summary[name]=report;(OUT/'summary.json').write_text(json.dumps(summary,indent=2));print(name,report,flush=True)
  page.close()
 browser.close()
