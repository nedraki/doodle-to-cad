"""Task 02 product check. Start the app with the same DOODLE_RESULTS_DIR.

DOODLE_RESULTS_DIR=results/brep-contract-tests .venv/bin/python scripts/check_build_contract.py
"""
import hashlib
import json
import os
from pathlib import Path
import sys
import uuid

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import httpx
import numpy as np
from PIL import Image
from playwright.sync_api import sync_playwright
from doodle_to_cad.build_contract import BuildInput, CAMERAS, build
from doodle_to_cad.config import ROOT, settings
from doodle_to_cad.openscad import mesh_health
from evaluate_brep import REFERENCES

base = os.getenv('DOODLE_TEST_URL', 'http://127.0.0.1:8081')
evidence = ROOT / 'docs/brep/task-02'
evidence.mkdir(parents=True, exist_ok=True)
out = settings.results_dir / uuid.uuid4().hex[:12]
out.mkdir(parents=True)
source = out / 'model.scad'
source.write_text(REFERENCES['bracket'])
scad = build(BuildInput('openscad', source, out), settings.openscad_bin)
assert scad.ok and set(scad.views) == set(CAMERAS), scad.metadata()
def url(path):
    return '/results/' + path.relative_to(settings.results_dir).as_posix()
scad_result = {'id': out.name, 'backend': 'openscad', 'success': False,
               'model': 'deterministic reference', 'spec': {'object': 'Four-hole bracket'},
               'evaluation': {'accepted': False, 'failures': ['Drawing fidelity has not been evaluated.']},
               'build': scad.metadata(), 'files': {'scad': url(source), 'stl': url(scad.stl),
               'views': {n: url(p) for n,p in scad.views.items()}}}
(out / 'result.json').write_text(json.dumps(scad_result, indent=2))
recipe = json.loads((ROOT / 'benchmarks/brep/bracket.json').read_text())
response = httpx.post(base + '/api/brep/build', json=recipe, timeout=180)
response.raise_for_status()
brep_result = response.json()
assert set(brep_result['files']['views']) == set(CAMERAS), brep_result

def local(url):
    return settings.results_dir / url.removeprefix('/results/')

def mask(path):
    rgb = np.array(Image.open(path).convert('RGB')).astype(int)
    # OpenSCAD Cornfield solid is yellow; the background is near-white.
    return (rgb[:,:,0] - rgb[:,:,2] > 30) & (rgb[:,:,1] - rgb[:,:,2] > 20)

report = {'dimensions_mm': {}, 'view_silhouette_iou': {}, 'downloads': {}, 'browser': {}}
for result in (scad_result, brep_result):
    backend = result['backend']
    health = mesh_health(local(result['files']['stl']))
    assert health['extents_mm'] == [60,40,80], health
    assert health['components'] == 1 and health['watertight']
    report['dimensions_mm'][backend] = health['extents_mm']
    report['downloads'][backend] = {}
    for kind in ('scad', 'source', 'stl', 'usd'):
        if kind not in result['files']:
            continue
        path = result['files'][kind]
        downloaded = httpx.get(base + path)
        downloaded.raise_for_status()
        assert downloaded.content == local(path).read_bytes()
        report['downloads'][backend][kind] = hashlib.sha256(downloaded.content).hexdigest()
    for name,path in result['files']['views'].items():
        (evidence / f'{backend}-{name}.png').write_bytes(local(path).read_bytes())
for name in CAMERAS:
    a = mask(local(scad_result['files']['views'][name]))
    b = mask(local(brep_result['files']['views'][name]))
    assert a.sum() > 1000 and b.sum() > 1000
    iou = float((a & b).sum() / (a | b).sum())
    report['view_silhouette_iou'][name] = iou
    assert iou > .98, (name, iou)
with sync_playwright() as p:
    browser = p.chromium.launch(headless=True, executable_path=os.environ['CHROMIUM_EXECUTABLE'],
        args=['--no-sandbox', '--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'])
    for result in (scad_result, brep_result):
        page = browser.new_page(viewport={'width':1500,'height':1100})
        errors = []
        page.on('pageerror', lambda error: errors.append(str(error)))
        page.goto(base)
        page.evaluate('(result)=>render(result,null)', result)
        page.wait_for_function('viewer && viewer.mesh')
        assert page.locator('#stl').get_attribute('href') == result['files']['stl']
        assert page.locator('#scad').get_attribute('href') == (result['files'].get('source') or result['files']['scad'])
        page.click('[data-views-toggle]')
        page.wait_for_function('Array.from(document.querySelectorAll("#views img")).every(i=>i.complete && i.naturalWidth>0)')
        assert page.locator('#views img').count() == 4
        page.locator('#result').scroll_into_view_if_needed()
        page.screenshot(path=str(evidence / f'{result["backend"]}-viewer.png'))
        assert not errors, errors
        report['browser'][result['backend']] = {'mesh_loaded': True, 'views_loaded': 4, 'download_links_match': True, 'page_errors': errors}
        page.close()
    browser.close()
(evidence / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report, indent=2))
