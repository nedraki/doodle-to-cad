"""Click a visible native face, then confirm a hidden face is not picked through it."""
import json
from pathlib import Path
import httpx
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'docs/brep/task-14';BASE='http://127.0.0.1:8106'
job=json.loads((OUT/'product-final/report.json').read_text())['cutout']['job'];run=httpx.get(BASE+'/api/results/'+job).json()
with sync_playwright() as p:
 b=p.chromium.launch(headless=True,executable_path='/home/sparkie/.cache/ms-playwright/chromium-1243/chrome-linux-arm64/chrome',args=['--no-sandbox','--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader'])
 page=b.new_page(viewport={'width':1600,'height':1400});errors=[];page.on('pageerror',lambda e:errors.append(str(e)));page.goto(BASE,wait_until='networkidle');page.evaluate('(r)=>render(r,null)',run);page.wait_for_function('viewer?.mesh');page.wait_for_timeout(1200);page.evaluate('viewer.setView("front")');page.wait_for_timeout(600);page.select_option('#selectionMode','face');page.click('#clearSelection');page.wait_for_function('currentRun.target_selection.status==="none"&&!geometrySelectionBusy')
 front=next(t for t in run['diagnostics']['selection_catalog']['targets'] if t['rule']=={'kind':'extreme_face','owner':'cut4','axis':1,'side':'min'})
 point=[sum(v[a] for v in front['geometry']['triangles'][:3])/3 for a in range(3)]
 xy=page.evaluate('point=>{const p=new THREE.Vector3(...point).project(viewer.camera),r=viewer.renderer.domElement.getBoundingClientRect();return [r.left+(p.x+1)*r.width/2,r.top+(1-p.y)*r.height/2]}',point)
 page.mouse.click(*xy);page.wait_for_function('(id)=>currentRun.target_selection?.target?.id===id&&!geometrySelectionBusy',arg=front['id'])
 page.locator('#result').screenshot(path=str(OUT/'click-face.png'));report={'job':job,'visible_face_picked':True,'point_mm':point,'browser_errors':errors}
 # Only a rear face is selectable in this injected picker subset. The actual
 # front mesh remains. A click on solid material must not pass through it.
 rear=next(t for t in run['diagnostics']['selection_catalog']['targets'] if t['rule']=={'kind':'extreme_face','owner':'cut4','axis':1,'side':'max'})
 page.evaluate('target=>{window.hiddenPickCount=0;viewer.setGeometrySelection({targets:[target]},null,"face",()=>window.hiddenPickCount++)}',rear)
 rear_point=[sum(v[a] for v in rear['geometry']['triangles'][:3])/3 for a in range(3)]
 xy=page.evaluate('point=>{const p=new THREE.Vector3(...point).project(viewer.camera),r=viewer.renderer.domElement.getBoundingClientRect();const ray=new THREE.Raycaster();ray.setFromCamera(new THREE.Vector2(p.x,p.y),viewer.camera);window.rearRayHits=ray.intersectObjects(viewer.selectionPickers,false).length;return [r.left+(p.x+1)*r.width/2,r.top+(1-p.y)*r.height/2]}',rear_point)
 assert page.evaluate('window.rearRayHits')>0
 page.mouse.click(*xy);page.wait_for_timeout(300);assert page.evaluate('window.hiddenPickCount')==0;report['hidden_face_not_picked']=True
 assert not errors;b.close()
(OUT/'picking-report.json').write_text(json.dumps(report,indent=2));print(report)
