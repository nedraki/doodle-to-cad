"""Product checks for saved direct BRep runs; no fabricated geometry or screenshots."""
import json
import os
from pathlib import Path
import shutil

import httpx
from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'docs/brep/task-06'
BASE=os.getenv('DOODLE_TEST_URL','http://127.0.0.1:8086')
summary=json.loads((OUT/'summary.json').read_text())
report={}
with sync_playwright() as p:
 browser=p.chromium.launch(headless=True,executable_path=os.getenv('CHROMIUM_EXECUTABLE','/home/sparkie/.cache/ms-playwright/chromium-1243/chrome-linux-arm64/chrome'),args=['--no-sandbox','--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader','--ignore-gpu-blocklist'])
 page=browser.new_page(viewport={'width':1600,'height':1200})
 errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
 page.goto(BASE)
 assert page.locator('[name=backend]').input_value()=='openscad'
 page.select_option('[name=backend]','usd-brep')
 assert page.locator('#backendHelp').is_visible()
 for name,case in summary.items():
    target=OUT/name
    state=httpx.get(BASE+'/api/generate/'+case['id']).json()
    if state['status']!='done':
        page.evaluate('(text)=>showError(text,false)',state['error']['message'])
        page.locator('#error').screenshot(path=str(target/'failure.png'))
        report[name]={'status':state['status'],'error':state['error']}
        continue
    result=state['result']
    assert result['generation']['generated_scad'] is False and not result['success']
    assert result['build']['source_format']=='brep-recipe-v2'
    assert 'score' not in result['evaluation']
    local=ROOT/'results/brep-direct-product'/case['id']
    for scad in local.rglob('*.scad'):
        assert scad.name=='preview.scad' and scad.read_text()=='import("model.stl");\n'
    page.evaluate('(r)=>render(r,null)',result)
    page.wait_for_function('viewer?.mesh',timeout=30000)
    page.evaluate('viewer.setView("isometric")')
    page.wait_for_timeout(600)
    page.locator('#result').screenshot(path=str(target/'result.png'))
    page.locator('#viewerWrap').screenshot(path=str(target/'part.png'))
    for key in ('stl','usd','source','evidence','generation'):
        response=httpx.get(BASE+result['files'][key]);response.raise_for_status();assert response.content
    params=httpx.get(BASE+'/api/results/'+case['id']+'/params').json()['params']
    candidates=[v for v in params if v['low']<v['value']<v['high'] and v['unit']!='count']
    assert candidates,'Expected an editable dimension'
    param=candidates[0]
    value=round(min(param['high'],param['value']*1.02),2)
    page.click('#modify');page.wait_for_selector('.param-row')
    index=page.evaluate('(n)=>paramState.originalParams.findIndex(p=>p.name===n)',param['name'])
    with page.expect_response(lambda r:'/parametrize' in r.url and r.request.method=='POST',timeout=180000) as pending:
        field=page.locator(f'#param-{index}-number');field.fill(str(value));field.dispatch_event('change')
    edited=pending.value.json()
    (target/'edit.json').write_text(json.dumps(edited,indent=2))
    if edited.get('ok'):
        page.wait_for_function('(url)=>document.querySelector("#stl").getAttribute("href")===url',arg=edited['stl'])
        for key,selector in [('stl','#stl'),('source','#scad'),('usd','#usd')]:
            assert page.locator(selector).get_attribute('href')==edited[key]
            response=httpx.get(BASE+edited[key]);response.raise_for_status()
            (target/('edited.'+{'stl':'stl','source':'recipe.json','usd':'usda'}[key])).write_bytes(response.content)
    page.click('#paramClose')
    page.locator('#result').screenshot(path=str(target/'edited-result.png'))
    page.reload()
    restored=httpx.get(BASE+'/api/results/'+case['id']).json()
    assert restored==result
    page.evaluate('(r)=>render(r,null)',restored)
    page.wait_for_function('viewer?.mesh',timeout=30000)
    assert page.locator('#stl').get_attribute('href')==result['files']['stl']
    # Include edited revisions in the archived native outputs.
    shutil.copytree(local,target/'artifacts'/case['id'],dirs_exist_ok=True)
    report[name]={'status':'done','downloaded':['stl','usd','source','evidence','generation'],'reloaded_original':True,
                  'parameter':param['name'],'value':value,'edit_ok':edited.get('ok',False),
                  'measurements':result['build']['measurements']}
 assert not errors,errors
 browser.close()
(OUT/'product-report.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report,indent=2))
