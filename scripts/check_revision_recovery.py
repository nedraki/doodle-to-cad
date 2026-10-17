"""Verify persisted native result after server restart, plus delayed browser response guard."""
import json
from pathlib import Path
import httpx
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'docs/brep/task-13/product-final';BASE='http://127.0.0.1:8105'
expected=json.loads((OUT/'second-kept.json').read_text());job=expected['id']
saved=httpx.get(BASE+'/api/results/'+job).json();assert saved==expected
report={'server_restart_matches':True}
with sync_playwright() as p:
 b=p.chromium.launch(headless=True,executable_path='/home/sparkie/.cache/ms-playwright/chromium-1243/chrome-linux-arm64/chrome',args=['--no-sandbox','--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader'])
 page=b.new_page(viewport={'width':1600,'height':1300});errors=[];page.on('pageerror',lambda e:errors.append(str(e)));page.goto(BASE,wait_until='networkidle');page.evaluate('(r)=>render(r,null)',saved);page.wait_for_function('viewer?.mesh');page.wait_for_timeout(1800);page.evaluate('viewer.setView("isometric")');page.wait_for_timeout(500)
 assert page.locator('#resultTitle').inner_text()=='SAVED BREP EDIT'
 page.locator('#result').screenshot(path=str(OUT/'server-restart.png'))
 # Hold a response from an older preview, discard it, then release it. The data
 # is a previously saved native candidate; this part tests UI ordering only.
 held=[];page.route('**/revisions/preview',lambda route:held.append(route))
 page.click('#modify');page.wait_for_function('paramState?.originalParams?.length>0');i=page.evaluate('paramState.originalParams.findIndex(p=>p.name==="thickness")')
 field=page.locator(f'#param-{i}-number');field.fill('4');field.dispatch_event('change')
 for _ in range(100):
  if held:break
  page.wait_for_timeout(100)
 assert held
 page.click('#paramReset');page.wait_for_function('(id)=>currentRun?.revision?.id===id&&!revisionBusy',arg=saved['revision']['id'])
 stale=json.loads((OUT/'discarded-preview.json').read_text())
 held[0].fulfill(status=200,content_type='application/json',body=json.dumps(stale));page.wait_for_timeout(1000)
 assert page.evaluate('currentRun.revision.id')==saved['revision']['id']
 assert page.locator('#stl').get_attribute('href')==saved['files']['stl']
 assert page.locator('#keepRevision').is_hidden()
 report.update(delayed_preview_ignored=True,browser_errors=errors);assert not errors;b.close()
(OUT/'recovery-report.json').write_text(json.dumps(report,indent=2));print(report)
