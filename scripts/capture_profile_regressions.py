"""Save real app screenshots for the completed regression builds."""
import json
from pathlib import Path
import httpx
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'docs/brep/task-09/regressions';BASE='http://127.0.0.1:8099'
with sync_playwright() as p:
 b=p.chromium.launch(headless=True,executable_path='/home/sparkie/.cache/ms-playwright/chromium-1243/chrome-linux-arm64/chrome',args=['--no-sandbox','--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader'])
 page=b.new_page(viewport={'width':1600,'height':1300})
 for name,case in json.loads((OUT/'summary.json').read_text()).items():
  if case['status']!='done':continue
  r=httpx.get(BASE+'/api/results/'+case['job']).json();page.goto(BASE);page.evaluate('(r)=>render(r,null)',r);page.wait_for_function('viewer?.mesh');page.wait_for_timeout(1000);page.evaluate('viewer.setView("isometric")');page.wait_for_timeout(600)
  page.locator('#result').screenshot(path=str(OUT/name/'result.png'));page.locator('#viewerWrap').screenshot(path=str(OUT/name/'part.png'))
 b.close()
