"""Measure and display the saved same-input OpenSCAD comparison; no generation."""
import json
from pathlib import Path
import httpx
from playwright.sync_api import sync_playwright
from scripts.measure_richer_brep import measure
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'docs/brep/task-43/openscad-comparison';BASE='http://127.0.0.1:8089'
report={}
with sync_playwright() as p:
 b=p.chromium.launch(headless=True,executable_path='/home/sparkie/.cache/ms-playwright/chromium-1243/chrome-linux-arm64/chrome',args=['--no-sandbox','--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader'])
 page=b.new_page(viewport={'width':1600,'height':1200})
 for name,case in json.loads((OUT/'summary.json').read_text()).items():
  if case['status']!='done':report[name]=case;continue
  result=httpx.get(BASE+'/api/results/'+case['id']).json()
  page.goto(BASE);page.evaluate('(r)=>render(r,null)',result);page.wait_for_function('viewer?.mesh');page.evaluate('viewer.setView("isometric")');page.wait_for_timeout(500)
  page.locator('#result').screenshot(path=str(OUT/name/'result.png'));page.locator('#viewerWrap').screenshot(path=str(OUT/name/'part.png'))
  mesh=ROOT/'results/brep-rich'/case['id']/Path(result['files']['stl']).name
  report[name]={'id':case['id'],'pipeline_accepted':result['success'],'evaluation':result['evaluation'],'measurements':measure(mesh,name),'duration_seconds':result['duration_seconds'],'parameters':httpx.get(BASE+'/api/results/'+case['id']+'/params').json()['params']}
 b.close()
(OUT/'comparison-report.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({k:{'accepted':v.get('pipeline_accepted'),'independent_checks':v.get('measurements',{}).get('status')} for k,v in report.items()},indent=2))
