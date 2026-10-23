"""Real native builds and browser keep/discard/reload on an existing recipe."""
import json,shutil
from pathlib import Path
import httpx,trimesh
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'docs/brep/task-13/product-final';OUT.mkdir(parents=True,exist_ok=True)
BASE='http://127.0.0.1:8105'
def save(name,data):(OUT/name).write_text(json.dumps(data,indent=2))
with httpx.Client(base_url=BASE,timeout=180) as client:
 if (OUT/'initial.json').exists():initial=json.loads((OUT/'initial.json').read_text())
 else:
  recipe=json.loads((ROOT/'benchmarks/brep-shells/reference.recipe.json').read_text())
  recipe['parameters']['width']={'value':60,'min':40,'max':80,'label':'Outside width'};recipe['operations'][0]['size'][0]='width'
  r=client.post('/api/brep/build',json=recipe);r.raise_for_status();initial=r.json();save('initial.json',initial)
 job=initial['id'];report={'job':job,'source':'saved native recipe, not new drawing generation'}
 with sync_playwright() as p:
  browser=p.chromium.launch(headless=True,executable_path='/home/sparkie/.cache/ms-playwright/chromium-1243/chrome-linux-arm64/chrome',args=['--no-sandbox','--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader'])
  page=browser.new_page(viewport={'width':1600,'height':1300});errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
  page.goto(BASE,wait_until='networkidle');page.evaluate('(r)=>render(r,null)',client.get('/api/results/'+job).json());page.wait_for_function('viewer?.mesh');page.wait_for_timeout(1500)
  def capture(name):
   page.evaluate('viewer.setView("isometric")');page.wait_for_timeout(600);page.locator('#result').screenshot(path=str(OUT/(name+'.png')))
  def edit(name,value):
   page.click('#modify');page.wait_for_function('paramState?.originalParams?.length>0')
   i=page.evaluate('(n)=>paramState.originalParams.findIndex(p=>p.name===n)',name)
   with page.expect_response(lambda r:r.request.method=='POST' and r.url.endswith('/revisions/preview'),timeout=180000) as response:
    field=page.locator(f'#param-{i}-number');field.fill(str(value));field.dispatch_event('change')
   data=response.value.json();assert response.value.ok,data
   page.wait_for_function('(id)=>currentRun?.revision?.id===id',arg=data['revision']['id']);page.click('#paramClose');return data
  capture('original')
  one=edit('thickness',3);save('first-preview.json',one);capture('first-preview')
  assert client.get('/api/results/'+job).json()['revision']['id']=='original'
  page.click('#keepRevision');page.wait_for_function('currentRun?.revision?.candidate===false');saved_one=client.get('/api/results/'+job).json();save('first-kept.json',saved_one)
  two=edit('width',70);save('second-preview.json',two);assert two['revision']['parent_id']==one['revision']['id']
  page.click('#keepRevision');page.wait_for_function('currentRun?.revision?.candidate===false');saved_two=client.get('/api/results/'+job).json();save('second-kept.json',saved_two)
  page.reload(wait_until='networkidle');page.evaluate('(r)=>render(r,null)',client.get('/api/results/'+job).json());page.wait_for_function('viewer?.mesh');page.wait_for_timeout(1200);capture('reloaded')
  assert page.locator('#stl').get_attribute('href')==two['files']['stl']
  params=client.get('/api/results/'+job+'/params').json()['params'];values={x['name']:x['value'] for x in params};assert values['thickness']==3 and values['width']==70
  third=edit('thickness',4);save('discarded-preview.json',third);page.click('#discardRevision');page.wait_for_function('(id)=>currentRun?.revision?.id===id',arg=two['revision']['id']);capture('discard-restored')
  assert page.locator('#stl').get_attribute('href')==two['files']['stl']
  invalid=client.post('/api/results/'+job+'/revisions/preview',json={'parent_id':two['revision']['id'],'selection_version':saved_two['revision']['selection_version'],'updates':{'thickness':25}})
  save('invalid.json',{'status':invalid.status_code,'body':invalid.json()});assert invalid.status_code==422
  assert client.get('/api/results/'+job).json()==saved_two
  report.update(two_edits_kept=True,reload_matches=True,discard_restores=True,invalid_retains=True,browser_errors=errors);assert not errors
  browser.close()
 local=ROOT/'results/brep30'/job;shutil.copytree(local,OUT/'artifacts'/job,dirs_exist_ok=True)
 for label,result in [('original',initial),('edited',two)]:
  path=local/Path(result['files']['stl']).relative_to('/results/'+job);mesh=trimesh.load(path,force='mesh');report[label]={'extents':mesh.extents.tolist(),'watertight':mesh.is_watertight,'components':len(mesh.split())}
 assert report['edited']['extents']==[70,40,20]
 save('report.json',report);print(json.dumps(report,indent=2))
