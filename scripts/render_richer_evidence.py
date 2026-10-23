"""Lay out actual input and viewer screenshots. Never synthesize part images."""
import html,json,os
from pathlib import Path
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1]
TRIAL=os.getenv('BREP_TRIAL','trial-01');OUT=ROOT/'docs/brep/task-43'/TRIAL
with sync_playwright() as p:
 b=p.chromium.launch(headless=True,executable_path='/home/sparkie/.cache/ms-playwright/chromium-1243/chrome-linux-arm64/chrome',args=['--no-sandbox','--allow-file-access-from-files'])
 page=b.new_page(viewport={'width':1800,'height':760},device_scale_factor=1)
 for name in ['handle','rounded','bevel']:
  target=OUT/name
  if not (target/'edited-part.png').exists():continue
  measurements=json.loads((OUT/'measurements.json').read_text())[name]
  product=json.loads((OUT/'product-report.json').read_text())[name]
  status=measurements.get('edited',{}).get('status','unverified')
  title=f"{name.replace('_',' ').title()} — drawing → generated BRep → edited BRep"
  sub=f"{TRIAL} | {product['parameter']}: {product['before']:g} → {product['after']:g} | independent feature checks: {status}"
  cards=''.join(f'<figure><img src="{file}"><figcaption>{label}</figcaption></figure>' for file,label in [('input.png','Actual submitted drawing'),('part.png','Actual generated part'),('edited-part.png','Actual parameter edit')])
  document=f'''<!doctype html><meta charset="utf-8"><style>body{{font:22px Arial;background:#f4f1e9;color:#172633;margin:35px}}h1{{font-size:32px}}.cards{{display:flex;gap:18px}}figure{{margin:0;flex:1;min-width:0;background:white;border:1px solid #bbb;border-radius:12px;overflow:hidden}}img{{width:100%;height:470px;object-fit:contain}}figcaption{{padding:18px;font-weight:bold}}footer{{margin-top:24px;font-size:19px}}</style><h1>{html.escape(title)}</h1><p>{html.escape(sub)}</p><div class="cards">{cards}</div><footer>Images are captured from the application. Build validity and drawing fidelity are reported separately. All attempts are retained.</footer>'''
  (target/'comparison.html').write_text(document)
  page.goto((target/'comparison.html').as_uri());page.screenshot(path=str(target/'comparison.png'),full_page=True)
 b.close()
