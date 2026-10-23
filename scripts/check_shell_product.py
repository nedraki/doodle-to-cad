"""Live drawing generation and viewer edit; independent drawing contract after generation."""
import json,os,time,shutil,math,re
from pathlib import Path
import httpx,numpy as np,trimesh
from playwright.sync_api import sync_playwright
from doodle_to_cad.brep_checks import section_check
ROOT=Path(__file__).resolve().parents[1]
BASE=os.getenv('DOODLE_TEST_URL','http://127.0.0.1:8104')
OUT=ROOT/'docs/brep/task-12'/os.getenv('BREP_TRIAL','trial-01');OUT.mkdir(parents=True,exist_ok=True)
from scripts.check_shell_reference import measure
def save(name,data):(OUT/name).write_text(json.dumps(data,indent=2)+'\n')
if __name__=='__main__':
 source=ROOT/'benchmarks/brep-shells'/os.getenv('BREP_INPUT','drawing.png');shutil.copy(source,OUT/'input.png');report={}
 with sync_playwright() as p:
  browser=p.chromium.launch(headless=True,executable_path='/home/sparkie/.cache/ms-playwright/chromium-1243/chrome-linux-arm64/chrome',args=['--no-sandbox','--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader'])
  page=browser.new_page(viewport={'width':1600,'height':1300});errors=[];page.on('pageerror',lambda e:errors.append(str(e)));page.goto(BASE)
  if (OUT/'request.json').exists():job=json.loads((OUT/'request.json').read_text())['job']
  else:
   page.locator('#image').set_input_files(str(source));page.wait_for_timeout(600)
   page.locator('[name=backend]').select_option('usd-brep');page.locator('[name=primary_view]').select_option('top');page.locator('[name=dimension]').fill('60')
   with page.expect_response(lambda r:r.url==BASE+'/api/generate' and r.request.method=='POST',timeout=30000) as pending:page.locator('#launch').click()
   job=pending.value.json()['job_id'];save('request.json',{'source':str(source.relative_to(ROOT)),'notes':'','backend':'usd-brep','primary_view':'top','dimension':60,'job':job})
  print('job',job,flush=True)
  answered=[]
  for _ in range(750):
   state=httpx.get(BASE+'/api/generate/'+job,timeout=30).json()
   if state['status']=='waiting_for_answer':
    q=state['question'];save('question-'+str(len(answered)+1)+'.json',q)
    if os.getenv('BREP_INPUT')=='missing-thickness.png' and q['kind'] in {'wall_thickness','floor_thickness','uniform_thickness'} and q['id'] not in answered:
     page.evaluate('({id,job})=>{document.querySelector("#working").hidden=false;showClarification(id,job)}',{'id':job,'job':state})
     page.locator('#clarificationPanel').wait_for(timeout=15000)
     page.locator('#working').screenshot(path=str(OUT/('question-'+str(len(answered)+1)+'.png')))
     bad=httpx.post(BASE+'/api/generate/'+job+'/answer',json={'question_id':q['id'],'thickness_mm':0});assert bad.status_code==422
     save('invalid-answer.json',{'status':bad.status_code,'response':bad.json()})
     page.locator('#clarificationForm [name=thickness]').fill('2');page.locator('#clarificationPanel').screenshot(path=str(OUT/'answer.png'));page.locator('#clarificationForm [type=submit]').click();answered.append(q['id'])
    elif q['id'] not in answered:
     for staged in (ROOT/'results').glob('.recipe-job-*/'+job):shutil.copytree(staged,OUT/'artifacts'/job,dirs_exist_ok=True)
     httpx.post(BASE+'/api/generate/'+job+'/cancel');state=httpx.get(BASE+'/api/generate/'+job).json();break
   if state['status'] in {'done','error','cancelled'}:break
   time.sleep(2)
  else:raise TimeoutError(job)
  save('job.json',state);local=ROOT/'results/brep29'/job
  report={'job':job,'status':state['status'],'error':state.get('error'),'answered_thickness_questions':len(answered)}
  if state['status']=='done':
   result=state['result'];page.evaluate('(r)=>render(r,null)',result);page.wait_for_function('viewer?.mesh');page.wait_for_timeout(1000);page.evaluate('viewer.setView("isometric")');page.wait_for_timeout(600)
   page.locator('#result').screenshot(path=str(OUT/'result.png'));page.locator('#viewerWrap').screenshot(path=str(OUT/'part.png'))
   for key,suffix in [('source','recipe.json'),('stl','stl'),('usd','usda')]:
    r=httpx.get(BASE+result['files'][key]);r.raise_for_status();(OUT/('original.'+suffix)).write_bytes(r.content)
   recipe=json.loads((OUT/'original.recipe.json').read_text());report['uses_inward_shell']=any(o['kind']=='shell' for o in recipe['operations']);report['original']=measure(OUT/'original.stl',2)
   params=httpx.get(BASE+'/api/results/'+job+'/params').json()['params']
   names=' '.join(str(o.get('thickness','')) for o in recipe['operations'] if o['kind']=='shell')
   candidates=[v for v in params if re.search(r'\b'+re.escape(v['name'])+r'\b',names) and abs(v['value']-2)<.01 and v['low']<=3<=v['high']]
   report['editable_thickness_found']=bool(candidates)
   if candidates:
    param=candidates[0];page.click('#modify');page.wait_for_selector('.param-row');index=page.evaluate('(n)=>paramState.originalParams.findIndex(p=>p.name===n)',param['name'])
    with page.expect_response(lambda r:'/parametrize' in r.url and r.request.method=='POST',timeout=180000) as pending:
     field=page.locator(f'#param-{index}-number');field.fill('3');field.dispatch_event('change')
    edited=pending.value.json();save('edit.json',edited);report['edit_ok']=edited.get('ok',False)
    if report['edit_ok']:
     page.wait_for_function('(url)=>document.querySelector("#stl").getAttribute("href")===url',arg=edited['stl']);page.wait_for_timeout(1000)
     for key,selector,suffix in [('source','#scad','recipe.json'),('stl','#stl','stl'),('usd','#usd','usda')]:
      assert page.locator(selector).get_attribute('href')==edited[key]
      r=httpx.get(BASE+edited[key]);r.raise_for_status();(OUT/('edited.'+suffix)).write_bytes(r.content)
     report['edited']=measure(OUT/'edited.stl',3)
    page.click('#paramClose');page.evaluate('viewer.setView("isometric")');page.wait_for_timeout(600);page.locator('#result').screenshot(path=str(OUT/'edited-result.png'));page.locator('#viewerWrap').screenshot(path=str(OUT/'edited-part.png'))
    last=page.locator('#stl').get_attribute('href');invalid=httpx.post(BASE+'/api/results/'+job+'/parametrize',json={param['name']:param['high']+1},timeout=120)
    save('invalid-edit.json',{'status':invalid.status_code,'response':invalid.json()});report['invalid_edit_rejected']=invalid.status_code>=400 or not invalid.json().get('ok',False);report['prior_display_retained']=page.locator('#stl').get_attribute('href')==last
    page.reload();restored=httpx.get(BASE+'/api/results/'+job).json();page.evaluate('(r)=>render(r,null)',restored);page.wait_for_function('viewer?.mesh');report['reload_original']=restored==result and page.locator('#stl').get_attribute('href')==result['files']['stl']
  if local.exists():shutil.copytree(local,OUT/'artifacts'/job,dirs_exist_ok=True)
  if (local/'clarifications.json').exists():report['answered_thickness_questions']=sum(x['status']=='answered' and x['question']['kind'] in {'wall_thickness','floor_thickness','uniform_thickness'} for x in json.loads((local/'clarifications.json').read_text()))
  report['browser_errors']=errors;save('report.json',report);print(json.dumps(report,indent=2),flush=True);browser.close()
