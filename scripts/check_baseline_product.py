"""Record one live OpenSCAD generation and editing checks for issue 18.

Set DOODLE_TEST_URL and CHROMIUM_EXECUTABLE when needed. Never mock model responses.
"""
import hashlib
import json
import os
import shutil
from pathlib import Path
import time

import httpx
from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'docs/brep/baseline-01'
BASE=os.getenv('DOODLE_TEST_URL','http://127.0.0.1:8079')


def download(page, selector, label):
    href=page.locator(selector).get_attribute('href')
    response=httpx.get(BASE+href,timeout=30)
    response.raise_for_status()
    assert response.content
    extension=href.split('?')[0].rsplit('.',1)[-1]
    path=OUT/f'{label}.{extension}'
    path.write_bytes(response.content)
    return dict(url=href,bytes=len(response.content),sha256=hashlib.sha256(response.content).hexdigest())


def edit_and_reset(page, label):
    page.click('#modify')
    page.wait_for_selector('.param-row')
    page.wait_for_function('viewer && viewer.mesh')
    data=page.evaluate('({base:paramState.base,params:paramState.originalParams})')
    assert data['params']
    first=data['params'][0]
    value=first['value']
    changed=round(min(first['high'], value*1.05),2)
    if changed==value:changed=round(max(first['low'],value*0.95),2)
    assert changed!=value
    original=page.locator('#stl').get_attribute('href')
    before={key:download(page,selector,label+'-original-'+key) for key,selector in [('stl','#stl'),('source','#scad')]}
    field=page.locator('#param-0-number')
    field.fill(str(changed));field.dispatch_event('change')
    page.wait_for_function('(url)=>document.querySelector("#stl").getAttribute("href")!==url',arg=original,timeout=120000)
    edited={key:download(page,selector,label+'-edited-'+key) for key,selector in [('stl','#stl'),('source','#scad')]}
    assert before['stl']['sha256']!=edited['stl']['sha256']
    page.screenshot(path=str(OUT/f'{label}-edited.png'))
    field.fill(str(first['high']+100));field.dispatch_event('change')
    assert field.get_attribute('aria-invalid')=='true'
    assert page.locator('#stl').get_attribute('href')==edited['stl']['url']
    page.click('#paramReset')
    page.wait_for_function('(url)=>document.querySelector("#stl").getAttribute("href")===url',arg=original)
    assert float(field.input_value())==value
    page.screenshot(path=str(OUT/f'{label}-reset.png'))
    page.click('#paramClose')
    return dict(parameter=first['name'],original_value=value,edited_value=changed,original=before,edited=edited,invalid_input_retained_mesh=True,reset_passed=True)


def main():
    OUT.mkdir(parents=True,exist_ok=True)
    report={'base_url':BASE,'attempts':[]}
    try:
        with sync_playwright() as p:
            browser=p.chromium.launch(headless=True,executable_path=os.getenv('CHROMIUM_EXECUTABLE'),args=['--no-sandbox','--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader','--ignore-gpu-blocklist'])
            page=browser.new_page(viewport={'width':1500,'height':1000})
            errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
            page.goto(BASE)
            page.locator('#image').set_input_files(str(ROOT/'docs/demo/kit_sketch.png'))
            page.wait_for_function('dirty')
            page.locator('[name="notes"]').fill('L-shaped bookend')
            page.locator('[name="dimension"]').fill('100')
            page.screenshot(path=str(OUT/'openscad-input.png'))
            start=time.monotonic()
            page.click('#launch')
            page.wait_for_function('jobId!==null',timeout=30000)
            job=page.evaluate('jobId');report['job_id']=job
            (OUT/'live-job.json').write_text(json.dumps({'job_id':job,'base_url':BASE},indent=2))
            print('Generation submitted:',job,flush=True)
            page.wait_for_function('currentRun!==null || !document.querySelector("#error").hidden',timeout=900000)
            result=page.evaluate('currentRun')
            assert result, page.locator('#error').inner_text()
            report['generation_seconds']=round(time.monotonic()-start,3)
            report['result']=result
            result_root=ROOT/os.getenv('DOODLE_BASELINE_RESULTS','results/baseline-issue18')
            if (result_root/result['id']).is_dir():
                shutil.copytree(result_root/result['id'],OUT/'generation',dirs_exist_ok=True)
            report['attempts']=result.get('attempts',[])
            page.wait_for_function('viewer && viewer.mesh')
            page.screenshot(path=str(OUT/'openscad-generated.png'))
            print('Generation completed; supervisor accepted:',result['success'],flush=True)
            report['openscad_edit']=edit_and_reset(page,'openscad')
            page.reload();page.click('#viewLatest')
            page.wait_for_function('(id)=>currentRun?.id===id',arg=result['id'])
            report['reload_passed']=True
            # Exercise the existing deterministic BRep import, then load it through product UI.
            recipe=json.loads((ROOT/'benchmarks/brep/bracket.json').read_text())
            r=httpx.post(BASE+'/api/brep/build',json=recipe,timeout=130);r.raise_for_status();brep=r.json()
            report['brep_result']=brep
            page.reload();page.click('#viewLatest')
            page.wait_for_function('(id)=>currentRun?.id===id',arg=brep['id'])
            report['brep_edit']=edit_and_reset(page,'brep')
            report['brep_usd']=download(page,'#usd','brep-original-usd')
            assert not errors,errors
            report['browser_errors']=errors
            report['product_checks_passed']=True
            browser.close()
    except Exception as error:
        report['failure']=str(error)
        raise
    finally:
        (OUT/'product-checks.json').write_text(json.dumps(report,indent=2)+'\n')
    print('Generation, parameter changes, reset, reload and downloads passed.',flush=True)

if __name__=='__main__':main()
