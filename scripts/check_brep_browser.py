"""Run against the local app with its BRep worker configured (default port 8077)."""
import os
import json
from pathlib import Path
from playwright.sync_api import sync_playwright
import httpx
base=os.getenv('DOODLE_TEST_URL','http://127.0.0.1:8077')
recipe=json.loads(Path('benchmarks/brep/bracket.json').read_text())
r=httpx.post(base+'/api/brep/build',json=recipe,timeout=130)
r.raise_for_status();result=r.json()
with sync_playwright() as p:
 browser=p.chromium.launch(headless=True,executable_path=os.getenv('CHROMIUM_EXECUTABLE'),args=['--no-sandbox','--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader','--ignore-gpu-blocklist'])
 page=browser.new_page(viewport={'width':1500,'height':1000})
 errors=[]
 page.on('pageerror',lambda e: errors.append(str(e)))
 page.goto(base)
 page.evaluate('(result)=>render(result,null)',result)
 page.click('#modify')
 page.wait_for_selector('.param-row')
 print('parameter rows',page.locator('.param-row').count())
 print('numeric controls',page.locator('.param-row input[type=number]').count())
 print('first controls',page.locator('.param-row input').evaluate_all('(els)=>els.slice(0,8).map(e=>({id:e.id,type:e.type,value:e.value}))'))
 page.wait_for_function('viewer && viewer.mesh')
 before=page.locator('#stl').get_attribute('href')
 # Hole 1 width is the seventh numeric parameter (after x and z).
 field=page.locator('#param-6-number')
 field.fill('12');field.dispatch_event('change')
 page.wait_for_function('(old)=>document.querySelector("#stl").getAttribute("href")!==old',arg=before)
 assert 'Edited BRep' in page.locator('#statusBadge').inner_text()
 after=page.locator('#stl').get_attribute('href')
 assert page.locator('#usd').get_attribute('href').split('/')[-2] == after.split('/')[-2]
 field.fill('1000');field.dispatch_event('change')
 assert field.get_attribute('aria-invalid')=='true'
 assert page.locator('#stl').get_attribute('href')==after
 page.click('#paramReset')
 page.wait_for_function('(old)=>document.querySelector("#stl").getAttribute("href")===old',arg=before)
 page.screenshot(path='docs/brep/bracket-editor.png')
 assert page.locator('.param-row').count()==20
 assert page.locator('#scad').inner_text()=='📥 Recipe .json'
 assert '/model.usda' in page.locator('#usd').get_attribute('href')
 assert not errors,errors
 browser.close()
print('browser checks passed',result['id'])
