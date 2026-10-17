"""Select actual native geometry, edit in the app, and check matched/lost/split states."""
import json,shutil
from pathlib import Path
import httpx
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'docs/brep/task-14/product-final';OUT.mkdir(parents=True,exist_ok=True);BASE='http://127.0.0.1:8106'
def save(path,data):path.write_text(json.dumps(data,indent=2))
with httpx.Client(base_url=BASE,timeout=180) as client,sync_playwright() as p:
 b=p.chromium.launch(headless=True,executable_path='/home/sparkie/.cache/ms-playwright/chromium-1243/chrome-linux-arm64/chrome',args=['--no-sandbox','--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader'])
 page=b.new_page(viewport={'width':1600,'height':1400});errors=[];page.on('pageerror',lambda e:errors.append(str(e)));report={}
 for name,source,mode,kind,owner,edits in [
  ('cutout','benchmarks/brep-selection/bookend.json','feature','box_cutout','cut4',[('width',70,'matched'),('hole4_x',90,'lost')]),
  ('enclosure_face','benchmarks/brep-shells/reference.recipe.json','face','extreme_face',None,[('thickness',3,'matched')]),
  ('outer_edges','benchmarks/brep-selection/bookend.json','edges','outer_vertical_edges',None,[('width',70,'matched')]),
  ('split_cutout','benchmarks/brep-selection/split-bookend.json','feature','box_cutout','cut4',[('bridge_z',56,'ambiguous')])]:
  out=OUT/name;out.mkdir(exist_ok=True)
  if (out/'initial.json').exists():initial=json.loads((out/'initial.json').read_text())
  else:
   response=client.post('/api/brep/build',json=json.loads((ROOT/source).read_text()));response.raise_for_status();initial=response.json();save(out/'initial.json',initial)
  job=initial['id'];page.goto(BASE,wait_until='networkidle');page.evaluate('(r)=>render(r,null)',client.get('/api/results/'+job).json());page.wait_for_function('viewer?.mesh');page.wait_for_timeout(1200)
  catalog=initial['diagnostics']['selection_catalog'];assert catalog['status']=='available',catalog
  candidates=[t for t in catalog['targets'] if t['rule']['kind']==kind and (owner is None or t['rule']['owner']==owner)]
  if name=='enclosure_face':candidates=[t for t in candidates if t['rule']['axis']==0 and t['rule']['side']=='max']
  target=candidates[0];page.select_option('#selectionMode',mode);page.select_option('#selectionTarget',target['id']);page.wait_for_function('currentRun?.target_selection?.status==="matched"')
  page.evaluate('viewer.setView("isometric")');page.wait_for_timeout(600);page.locator('#result').screenshot(path=str(out/'selected.png'))
  saved=client.get('/api/results/'+job).json();assert saved['target_selection']['rule']==target['rule'];save(out/'selected.json',saved)
  camera=page.evaluate('[viewer.camera.position.toArray(),viewer.controls.target.toArray()]')
  checks=[]
  for parameter,value,expected in edits:
   page.click('#modify');page.wait_for_function('paramState?.originalParams?.length>0');i=page.evaluate('(name)=>paramState.originalParams.findIndex(p=>p.name===name)',parameter)
   with page.expect_response(lambda r:r.request.method=='POST' and r.url.endswith('/revisions/preview'),timeout=180000) as response:
    field=page.locator(f'#param-{i}-number');field.fill(str(value));field.dispatch_event('change')
   edited=response.value.json();save(out/(parameter+'-response.json'),edited);assert response.value.ok,edited
   page.wait_for_function('(id)=>currentRun?.revision?.id===id',arg=edited['revision']['id']);page.click('#paramClose')
   assert edited['target_selection']['status']==expected,edited['target_selection']
   after_camera=page.evaluate('[viewer.camera.position.toArray(),viewer.controls.target.toArray()]')
   save(out/(parameter+'-camera.json'),{'before':camera,'after':after_camera})
   assert max(abs(a-b) for before,after in zip(camera,after_camera) for a,b in zip(before,after))<1e-7
   if expected!='matched':assert page.evaluate('viewer.selectionOverlay.children.length')==0
   page.locator('#result').screenshot(path=str(out/(parameter+'-'+expected+'.png')));checks.append({'parameter':parameter,'value':value,'selection':expected,'camera_preserved':True})
   if expected=='matched':
    page.click('#keepRevision');page.wait_for_function('currentRun?.revision?.candidate===false')
  if edits[-1][2]!='matched':
   page.click('#discardRevision');page.wait_for_function('currentRun?.target_selection?.status==="matched"');checks.append({'discard_restores_selection':True})
  restored=client.get('/api/results/'+job).json();page.reload(wait_until='networkidle');page.evaluate('(r)=>render(r,null)',restored);page.wait_for_function('viewer?.mesh');assert page.locator('#selectionStatus').inner_text().startswith('Selected:')
  shutil.copytree(ROOT/'results/brep31'/job,out/'artifacts'/job,dirs_exist_ok=True)
  report[name]={'job':job,'checks':checks,'reload_selection':True};save(OUT/'report.json',report);print(name,report[name],flush=True)
 report['browser_errors']=errors;save(OUT/'report.json',report);assert not errors;b.close()
