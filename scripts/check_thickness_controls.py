"""Browser-only payload contract checks; mocked answer endpoint, no geometry claim."""
import json
from pathlib import Path
from playwright.sync_api import sync_playwright
OUT=Path('docs/brep/task-12');report={}
with sync_playwright() as p:
 b=p.chromium.launch(headless=True,executable_path='/home/sparkie/.cache/ms-playwright/chromium-1243/chrome-linux-arm64/chrome',args=['--no-sandbox']);page=b.new_page();errors=[];page.on('pageerror',lambda e:errors.append(str(e)));page.goto('http://127.0.0.1:8104')
 captured=[]
 def answer(route):
  captured.append(route.request.post_data_json);route.fulfill(status=200,content_type='application/json',body='{"status":"running"}')
 page.route('**/api/generate/control-test/answer',answer)
 for kind in ['wall_thickness','floor_thickness','uniform_thickness','recess','through']:
  opening=kind in ['recess','through']
  q={'id':kind,'kind':'opening_extent' if opening else kind,'feature_label':'Tray','reason':'Missing value','text':'Specify the detail','maximum_depth_mm':60,'maximum_thickness_mm':60}
  page.evaluate('(q)=>{document.querySelector("#working").hidden=false;showClarification("control-test",{status:"waiting_for_answer",question:q})}',q)
  if opening:
   page.locator(f'[name=openingChoice][value={kind}]').check()
   if kind=='recess':page.locator('[name=depth]').fill('5')
  else:page.locator('[name=thickness]').fill('2')
  with page.expect_response(lambda r:'/control-test/answer' in r.url):page.locator('#clarificationForm [type=submit]').click()
  page.wait_for_selector('#clarificationPanel',state='detached')
  expected={'question_id':kind}
  if opening:
   expected['choice']=kind
   if kind=='recess':expected['depth_mm']=5
  else:expected['thickness_mm']=2
  assert captured[-1]==expected,(captured[-1],expected)
  report[kind]={'payload':captured[-1],'passed':True}
 page.unroute('**/api/generate/control-test/answer');pending=[]
 page.route('**/api/generate/control-test/answer',lambda route:pending.append(route))
 first={**q,'id':'late-first','kind':'uniform_thickness','feature_label':'First question'}
 page.evaluate('(q)=>showClarification("control-test",{status:"waiting_for_answer",question:q})',first)
 page.locator('[name=thickness]').fill('2')
 with page.expect_request(lambda r:'/control-test/answer' in r.url):page.locator('#clarificationForm [type=submit]').click()
 page.wait_for_timeout(100);assert pending
 second={**first,'id':'next-question','feature_label':'Second question'}
 page.evaluate('(q)=>showClarification("control-test",{status:"waiting_for_answer",question:q})',second)
 with page.expect_response(lambda r:'/control-test/answer' in r.url):pending[0].fulfill(status=200,content_type='application/json',body='{"status":"running"}')
 page.wait_for_timeout(200)
 assert page.evaluate('clarificationId')=='next-question'
 assert 'Second question' in page.locator('#clarificationPanel').inner_text()
 report['late_answer_keeps_new_question']={'passed':True}
 report['browser_errors']=errors;assert not errors; b.close()
(OUT/'ui-controls.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
