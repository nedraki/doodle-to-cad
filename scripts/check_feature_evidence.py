"""Task 05 live, note-free interpretation fixtures. No kernel or source generation."""
import json
import os
from pathlib import Path
import shutil
import time

import httpx
from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'docs/brep/task-05'
BASE=os.getenv('DOODLE_TEST_URL','http://127.0.0.1:8085')
selected=json.loads((OUT/'selection.json').read_text())['selected']
cases={
 'wheel':ROOT/'benchmarks/brep-baseline/wheel/drawing.png',
 'bookend':ROOT/'benchmarks/cases/001_l_bookend_multiview/source/drawing.png',
 'knob':ROOT/'benchmarks/cases/006_stepped_knob/source/drawing.png',
 'random':ROOT/'benchmarks/cases'/selected/'source/drawing.png',
 'ambiguous':ROOT/'benchmarks/feature-evidence/ambiguous-outline.png',
}
requested=set(filter(None,os.getenv("EVIDENCE_CASES", "").split(",")))
summary=json.loads((OUT/"summary.json").read_text()) if requested and (OUT/"summary.json").exists() else {}
for name,path in cases.items():
 if requested and name not in requested:continue
 target=OUT/name;target.mkdir(parents=True,exist_ok=True)
 started=time.monotonic()
 if name=='ambiguous':
  with sync_playwright() as playwright:
   browser=playwright.chromium.launch(headless=True,executable_path=os.environ['CHROMIUM_EXECUTABLE'],args=['--no-sandbox'])
   page=browser.new_page();page.goto(BASE+'/?dev=evidence')
   page.locator('#image').set_input_files(str(path))
   with page.expect_response(lambda r:'/api/dev/interpret' in r.url,timeout=600000) as pending:
    page.click('#interpretEvidence')
   live=pending.value
   response=httpx.Response(live.status,content=live.body())
   page.wait_for_function('document.querySelector("#evidenceStatus").textContent.includes("Evidence ready")',timeout=30000)
   browser.close()
 else:
  response=httpx.post(BASE+'/api/dev/interpret',files={'image':('drawing.png',path.read_bytes(),'image/png')},data={'primary_view':'front','projection_standard':'third-angle'},timeout=600)
 (target/'response.json').write_text(response.text)
 print(name,response.status_code,round(time.monotonic()-started,2),flush=True)
 if not response.is_success:
  summary[name]={'error':response.text};continue
 result=response.json();shutil.copy2(path,target/'input.png')
 for key in ('overlay','interpretation'):
  r=httpx.get(BASE+result['files'][key]);r.raise_for_status();(target/('overlay.png' if key=='overlay' else 'interpretation.json')).write_bytes(r.content)
 # Keep raw model output so policy downgrades remain auditable.
 original=ROOT/'results/brep-evidence-product'/result['id']
 for raw in original.glob('feature-interpretation-*.raw.txt'):shutil.copy2(raw,target/raw.name)
 claims=result['interpretation']
 summary[name]={'id':result['id'],'notes':result['notes'],'source':str(path.relative_to(ROOT)),
                'features':len(claims['features']),'relationships':len(claims['relationships']),
                'unresolved':claims['unresolved'],'conflicts':claims['conflicts']}
(OUT/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
with sync_playwright() as p:
 browser=p.chromium.launch(headless=True,executable_path=os.environ['CHROMIUM_EXECUTABLE'],args=['--no-sandbox'])
 page=browser.new_page(viewport={'width':1500,'height':1100});errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
 page.goto(BASE);assert page.locator('#featureEvidence').count()==0
 page.goto(BASE+'/?dev=evidence')
 for name in cases:
  if 'error' in summary[name]:continue
  result=json.loads((OUT/name/'response.json').read_text())
  page.evaluate('(r)=>renderFeatureEvidence(r)',result)
  page.wait_for_function('document.querySelector("#evidenceReport img").complete && document.querySelector("#evidenceReport img").naturalWidth > 0')
  page.locator('#featureEvidence').screenshot(path=str(OUT/name/'evidence-panel.png'))
  page.evaluate('document.querySelector("#featureEvidence").scrollIntoView({block:"start"})')
  page.screenshot(path=str(OUT/name/'evidence-overview.png'))
 assert not errors,errors
 browser.close()
print(json.dumps(summary,indent=2),flush=True)
