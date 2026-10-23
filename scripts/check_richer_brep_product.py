"""Exercise real viewer controls and download actual generated/edited geometry."""
import json,os,re,shutil
from pathlib import Path
import httpx
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'docs/brep/task-43'/os.getenv('BREP_TRIAL','trial-01')
BASE=os.getenv('DOODLE_TEST_URL','http://127.0.0.1:8089')
requested=set(filter(None,os.getenv('BREP_CASES','').split(',')))
report=json.loads((OUT/'product-report.json').read_text()) if (OUT/'product-report.json').exists() else {}
with sync_playwright() as p:
 browser=p.chromium.launch(headless=True,executable_path='/home/sparkie/.cache/ms-playwright/chromium-1243/chrome-linux-arm64/chrome',args=['--no-sandbox','--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader'])
 page=browser.new_page(viewport={'width':1600,'height':1200});errors=[]
 page.on('pageerror',lambda e:errors.append(str(e)))
 for name,case in json.loads((OUT/'summary.json').read_text()).items():
    if requested and name not in requested:continue
    target=OUT/name
    if case['status']!='done':report[name]={'status':case['status'],'error':case.get('error')};continue
    result=httpx.get(BASE+'/api/results/'+case['id']).json()
    page.goto(BASE);page.evaluate('(r)=>render(r,null)',result)
    assert page.locator('#dimensionBadge').inner_text()==f"target {result['generation']['maximum_dimension_mm']:g} mm"
    page.wait_for_function('viewer?.mesh');page.evaluate('viewer.setView("isometric")');page.wait_for_timeout(600)
    page.locator('#result').screenshot(path=str(target/'result.png'))
    page.locator('#viewerWrap').screenshot(path=str(target/'part.png'))
    for key in ['source','stl','usd','drawing_checks']:
        response=httpx.get(BASE+result['files'][key]);response.raise_for_status();assert response.content
    params=httpx.get(BASE+'/api/results/'+case['id']+'/params').json()['params']
    recipe=httpx.get(BASE+result['files']['source']).json()
    used=json.dumps(recipe['operations'])
    candidates=[v for v in params if re.search(r'\b'+re.escape(v['name'])+r'\b',used) and v['low']<v['high']]
    keywords={'handle':['bend'],'rounded':['fillet','corner','round'],'bevel':['chamfer','bevel']}
    preferred=[v for v in candidates if any(k in (v['name']+' '+v.get('label','')).lower() for k in keywords.get(name,[]))]
    param=(preferred or candidates)[0]
    value={'handle':24,'rounded':8,'bevel':3}.get(name,round(min(param['high'],param['value']*1.02),2))
    # Bevel across-face width may be exposed instead of its intended setback.
    if name=='bevel' and abs(param['value']-2*2**.5)<.02:value=3*2**.5
    page.click('#modify');page.wait_for_selector('.param-row')
    index=page.evaluate('(n)=>paramState.originalParams.findIndex(p=>p.name===n)',param['name'])
    with page.expect_response(lambda r:'/parametrize' in r.url and r.request.method=='POST',timeout=180000) as pending:
        field=page.locator(f'#param-{index}-number');field.fill(str(value));field.dispatch_event('change')
    edited=pending.value.json();(target/'edit.json').write_text(json.dumps(edited,indent=2))
    if edited.get('ok'):
        page.wait_for_function('(url)=>document.querySelector("#stl").getAttribute("href")===url',arg=edited['stl'])
        page.wait_for_timeout(500)
        for key,selector,suffix in [('source','#scad','recipe.json'),('stl','#stl','stl'),('usd','#usd','usda')]:
            assert page.locator(selector).get_attribute('href')==edited[key]
            response=httpx.get(BASE+edited[key]);response.raise_for_status();(target/('edited.'+suffix)).write_bytes(response.content)
    page.click('#paramClose');page.evaluate('viewer.setView("isometric")');page.wait_for_timeout(300)
    page.locator('#result').screenshot(path=str(target/'edited-result.png'))
    page.locator('#viewerWrap').screenshot(path=str(target/'edited-part.png'))
    last={k:page.locator(s).get_attribute('href') for k,s in [('stl','#stl'),('source','#scad'),('usd','#usd')]}
    invalid=httpx.post(BASE+'/api/results/'+case['id']+'/parametrize',json={param['name']:param['high']+1},timeout=120)
    invalid_body=invalid.json();(target/'invalid-edit.json').write_text(json.dumps({'status_code':invalid.status_code,'response':invalid_body},indent=2))
    assert invalid.status_code>=400 or not invalid_body.get('ok',False),invalid_body
    assert last=={k:page.locator(s).get_attribute('href') for k,s in [('stl','#stl'),('source','#scad'),('usd','#usd')]}
    page.reload();restored=httpx.get(BASE+'/api/results/'+case['id']).json();assert restored==result
    page.evaluate('(r)=>render(r,null)',restored);page.wait_for_function('viewer?.mesh')
    assert page.locator('#stl').get_attribute('href')==result['files']['stl']
    shutil.copytree(ROOT/'results/brep-rich'/case['id'],target/'artifacts'/case['id'],dirs_exist_ok=True)
    report[name]={'status':'done','parameter':param['name'],'before':param['value'],'after':value,'edit_ok':edited.get('ok',False),
                  'matching_downloads':True,'invalid_edit_rejected':True,'prior_display_retained':True,'reload_original':True,'browser_errors':errors.copy()}
    (OUT/'product-report.json').write_text(json.dumps(report,indent=2)+'\n')
 assert not errors,errors
 browser.close()
print(json.dumps(report,indent=2))
