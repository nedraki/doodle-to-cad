"""Compose actual input and viewer screenshots into a labelled evidence sheet."""
from pathlib import Path
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'docs/brep/task-12';trial=OUT/'trial-01'
html='''<!doctype html><style>body{margin:0;padding:24px;background:#eee;font:20px sans-serif;color:#182633}h1{font-size:28px}main{display:grid;grid-template-columns:repeat(3,1fr);gap:16px}section{background:white;padding:12px}img{width:100%;height:420px;object-fit:contain}p{font-size:17px;line-height:1.5}.note{font-size:18px}</style><h1>Drawing → generated BRep → wall and floor edit</h1><main>'''
for title,file,caption in [('Input drawing',trial/'input.png','Empty notes. Top view. Maximum dimension: 60 mm.'),('Generated: 2 mm walls + floor',trial/'part.png','Open top. Inner space: 56 × 36 × 18 mm. Outside: 60 × 40 × 20 mm.'),('Edited: 3 mm walls + floor',trial/'edited-part.png','Inner space: 54 × 34 × 17 mm. Outside dimensions and R6 stay fixed.')]:
 html+=f'<section><h2>{title}</h2><img src="{file.as_uri()}"><p>{caption}</p></section>'
html+='</main><p class="note">Actual app screenshots · Seven independent sections passed for each part · Boundary tolerance: 0.25 mm<br>A separate missing-thickness trial asked one question, saved the answer and passed the same geometry checks.</p>'
pagefile=OUT/'comparison.html';pagefile.write_text(html)
with sync_playwright() as p:
 b=p.chromium.launch(headless=True,executable_path='/home/sparkie/.cache/ms-playwright/chromium-1243/chrome-linux-arm64/chrome',args=['--no-sandbox']);page=b.new_page(viewport={'width':1800,'height':760});page.goto(pagefile.as_uri());page.screenshot(path=str(OUT/'comparison.png'),full_page=True);b.close()
pagefile.unlink()
