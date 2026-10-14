import json
import os
from pathlib import Path
import httpx
from playwright.sync_api import sync_playwright
root=Path(__file__).resolve().parents[1];base=os.getenv('DOODLE_TEST_URL','http://127.0.0.1:8086')
with sync_playwright() as p:
 b=p.chromium.launch(headless=True,executable_path=os.getenv('CHROMIUM_EXECUTABLE','/home/sparkie/.cache/ms-playwright/chromium-1243/chrome-linux-arm64/chrome'),args=['--no-sandbox'])
 page=b.new_page(viewport={'width':1500,'height':1100});page.goto(base)
 assert page.locator('[name=backend]').input_value()=='openscad'
 page.select_option('[name=backend]','usd-brep')
 page.locator('#image').set_input_files(str(root/'benchmarks/cases/001_l_bookend_multiview/source/drawing.png'))
 page.wait_for_function('dirty')
 with page.expect_response(lambda r:r.url.endswith('/api/generate') and r.request.method=='POST') as pending:
  page.click('#launch')
 response=pending.value;assert response.ok,response.text()
 job=response.json()['job_id']
 page.wait_for_function('jobId!==null')
 page.screenshot(path=str(root/'docs/brep/task-06/direct-form-progress.png'))
 page.click('#abort')
 page.wait_for_function('jobId===null')
 state=httpx.get(base+'/api/generate/'+job).json()
 assert state['status']=='cancelled',state
 generation=httpx.get(base+'/results/'+job+'/generation.json').json()
 assert generation['path']=='drawing-to-brep'
 assert httpx.get(base+'/api/results/'+job).status_code==404
 (root/'docs/brep/task-06/form-report.json').write_text(json.dumps({'submitted_through_product':True,'default':'openscad','selected':'usd-brep','state':state,'generation':generation},indent=2))
 b.close()
print('Real form submission, backend selection and cancel passed.')
