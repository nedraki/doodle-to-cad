"""Task 03 browser checks against the separate BRep test instance."""
import json
import os
from pathlib import Path
import sys

import httpx
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from doodle_to_cad.construction_recipe import migrate_v1

BASE = os.getenv('DOODLE_TEST_URL', 'http://127.0.0.1:8082')
OUT = ROOT / 'docs/brep/task-03'
OUT.mkdir(parents=True, exist_ok=True)
report = {}

def build(recipe):
    response = httpx.post(BASE+'/api/brep/build', json=recipe, timeout=180)
    response.raise_for_status()
    return response.json()

with sync_playwright() as p:
    browser=p.chromium.launch(headless=True, executable_path=os.environ['CHROMIUM_EXECUTABLE'],args=['--no-sandbox','--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader','--ignore-gpu-blocklist'])
    for name in ('bookend','wheel','legacy'):
        path=ROOT/('benchmarks/brep/bracket.json' if name=='legacy' else f'benchmarks/brep-v2/{name}.json')
        recipe=json.loads(path.read_text())
        result=build(recipe)
        page=browser.new_page(viewport={'width':1500,'height':1200})
        errors=[]
        page.on('pageerror',lambda e:errors.append(str(e)))
        page.goto(BASE)
        page.evaluate('(r)=>render(r,null)',result)
        page.wait_for_function('viewer && viewer.mesh')
        page.evaluate('viewer.setView("isometric")')
        page.wait_for_timeout(300)
        page.locator('#result').screenshot(path=str(OUT/f'{name}-original.png'))
        report[name]={'build':result['build'],'diagnostics':result['diagnostics']}
        if name in ('wheel','legacy'):
            before=httpx.get(BASE+result['files']['source']).json()
            page.click('#modify')
            page.wait_for_selector('.param-row')
            parameter='radius' if name=='wheel' else 'hole1_width'
            index=page.evaluate('(name)=>paramState.originalParams.findIndex(p=>p.name===name)',parameter)
            value=80 if name=='wheel' else 12
            field=page.locator(f'#param-{index}-number')
            with page.expect_response(lambda r:'/parametrize' in r.url and r.request.method=='POST',timeout=180000) as response:
                field.fill(str(value));field.dispatch_event('change')
            edited=response.value.json()
            assert edited['ok'],edited
            page.wait_for_function('(u)=>document.querySelector("#stl").getAttribute("href")===u',arg=edited['stl'])
            source=httpx.get(BASE+edited['source']).json()
            expected=json.loads(json.dumps(recipe));expected['parameters'][parameter]['value']=value
            assert source==expected
            assert httpx.get(BASE+result['files']['source']).json()==before
            assert httpx.get(BASE+edited['stl']).status_code==200
            if name=='wheel':
                assert edited['build']['measurements']['extents_mm']==[160,160,8]
                assert len(edited['diagnostics']['connections'])==8
                assert all(c['passed'] for c in edited['diagnostics']['connections'])
            else:
                migrated=build(migrate_v1(source))
                assert abs(migrated['diagnostics']['solid_volume_mm3']-edited['diagnostics']['solid_volume_mm3'])<.001
                report[name]['migrated']=migrated['build']
            page.wait_for_timeout(300)
            page.locator('#result').screenshot(path=str(OUT/f'{name}-controls.png'))
            page.click('#paramClose')
            page.evaluate('viewer.setView("isometric")')
            page.wait_for_timeout(300)
            page.locator('#result').screenshot(path=str(OUT/f'{name}-edited.png'))
            report[name]['edited']={'build':edited['build'],'diagnostics':edited['diagnostics'],'source_preserved':True}
        assert not errors,errors
        report[name]['browser_errors']=errors
        page.close()
    browser.close()
report['invalid']={}
for fixture in sorted((ROOT/'benchmarks/brep-v2/invalid').glob('*.json')):
    response=httpx.post(BASE+'/api/brep/build',json=json.loads(fixture.read_text()),timeout=30)
    assert response.status_code==422,(fixture,response.text)
    report['invalid'][fixture.stem]=response.json()['detail']
(OUT/'report.json').write_text(json.dumps(report,indent=2)+'\n')
print('Product checks passed: bookend, wheel radius edit, legacy edit and migration, eight invalid recipes.')
