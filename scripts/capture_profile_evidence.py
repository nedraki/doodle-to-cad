"""Compose actual input and viewer screenshots into a labelled evidence sheet."""
from pathlib import Path
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'docs/brep/task-09';trial=OUT/'trial-02'
html='''<!doctype html><style>body{margin:0;padding:24px;background:#eee;font:20px sans-serif;color:#182633}h1{font-size:28px}main{display:grid;grid-template-columns:repeat(3,1fr);gap:16px}section{background:white;padding:12px}img{width:100%;height:420px;object-fit:contain}p{font-size:17px;line-height:1.5}.note{font-size:18px}</style><h1>Drawing → generated BRep → thickness edit</h1><main>'''
for title,file,caption in [('Input drawing',trial/'input.png','Empty notes. Top view. Maximum dimension: 60 mm.'),('Generated: 6 mm thick',trial/'part.png','Notch 20 × 10 mm; corner R6; Ø8 through-hole at (12, 15).'),('Edited in app: 10 mm thick',trial/'edited-part.png','Same 60 × 40 mm outline and hole. Only thickness changed.')]:
 html+=f'<section><h2>{title}</h2><img src="{file.as_uri()}"><p>{caption}</p></section>'
html+='</main><p class="note">Actual app screenshots · Independent sections passed at three heights in each part · Maximum boundary error 0.058 mm (limit 0.25 mm)<br>One successful live trial after one failed interpretation attempt. Current scope: closed XY line/arc profiles.</p>'
pagefile=OUT/'comparison.html';pagefile.write_text(html)
with sync_playwright() as p:
 b=p.chromium.launch(headless=True,executable_path='/home/sparkie/.cache/ms-playwright/chromium-1243/chrome-linux-arm64/chrome',args=['--no-sandbox']);page=b.new_page(viewport={'width':1800,'height':760});page.goto(pagefile.as_uri());page.screenshot(path=str(OUT/'comparison.png'),full_page=True);b.close()
pagefile.unlink()
