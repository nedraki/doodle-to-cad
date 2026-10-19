"""Compose failure montages for docs/brep/bench-final.

Rows: [input drawing | what usd-brep built | ground truth], captioned with the
published verdict/failure text. Provenance rules (added after the Codex
review of 907eed7, which caught that sorting brep-* dirs picks random
revisions — it selected an edited 96 mm bracket instead of the measured
80 mm original):
  * the mesh rendered is ALWAYS the archived `runs/.../stl/model.stl` copy
    written by the harness, verified sha256 against the row's build.sha256
    BEFORE rendering — a mismatch aborts the montage;
  * every montage gets a provenance.json entry binding image sha256 to
    row.json sha256, mesh sha256 and panel sources, so audit.py can prove
    image-to-row correspondence (a swapped image fails the audit);
  * captions quote measured row data only — no visual impressions.
"""
import hashlib
import json
import os
import shutil
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path('/tmp/doodle-brep-32')
BENCH = ROOT / 'docs/brep/bench-final'
OUT = BENCH / 'images'
OUT.mkdir(exist_ok=True)
RENDER_SERVE = ROOT / 'results' / '_render'
RENDER_SERVE.mkdir(exist_ok=True)

BASE = 'http://127.0.0.1:8114'
FONT = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 17)
FONT_S = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 14)


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def render_stl(stl_path, out_png):
    dst = RENDER_SERVE / f"{out_png.stem}.stl"
    shutil.copy2(stl_path, dst)
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, executable_path=os.environ.get(
            'CHROMIUM_EXECUTABLE',
            '/home/sparkie/.cache/ms-playwright/chromium-1234/chrome-linux/chrome'), args=[
            '--no-sandbox', '--use-gl=angle', '--use-angle=swiftshader',
            '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'])
        page = browser.new_page(viewport={'width': 520, 'height': 420})
        page.goto(BASE + '/')
        page.evaluate("""async ({url}) => {
            document.getElementById('working').hidden = true;
            document.getElementById('error').hidden = true;
            const res = document.getElementById('result'); res.hidden = false;
            const wrap = document.getElementById('viewerWrap');
            document.getElementById('views').before(wrap);
            document.querySelectorAll('#inputTools, #views').forEach(e => e.style.display='none');
            wrap.querySelectorAll('.viewer-tools, .viewer-hint').forEach(e => e.style.display='none');
            const v = new CadViewer(wrap);
            await v.showStl(url, 'front');
            // true isometric camera: three-quarter view so flat plates show their face
            const box = new THREE.Box3().setFromObject(v.mesh);
            const c = box.getCenter(new THREE.Vector3());
            const s = box.getSize(new THREE.Vector3());
            const dist = 2.4 * Math.max(s.x, s.y, s.z);
            const dir = new THREE.Vector3(1, -0.85, 1).normalize();
            v.camera.position.copy(c).addScaledVector(dir, dist);
            v.controls.target.copy(c);
            v.camera.near = Math.max(dist / 1000, 0.05);
            v.camera.far = dist * 20;
            v.camera.updateProjectionMatrix();
            v.controls.update();
            await new Promise(r => setTimeout(r, 1200));
        }""", {'url': '/results/_render/' + dst.name})
        page.wait_for_timeout(600)
        page.locator('#viewerWrap').screenshot(path=str(out_png))
        browser.close()
    return out_png


def thumb(path, w=420, h=300, bg=(24, 32, 38)):
    im = Image.open(path).convert('RGB')
    im.thumbnail((w - 12, h - 12))
    canvas = Image.new('RGB', (w, h), bg)
    canvas.paste(im, ((w - im.width) // 2, (h - im.height) // 2))
    return canvas


def refusal_panel(text, w=420, h=300):
    im = Image.new('RGB', (w, h), (255, 249, 237))
    d = ImageDraw.Draw(im)
    d.rectangle([0, 0, w - 1, h - 1], outline=(255, 89, 60), width=3)
    d.text((16, 14), 'MODEL-STAGE REFUSAL (published)', font=FONT, fill=(180, 40, 20))
    words, line, y = text.split(), '', 52
    for word in words:
        while d.textlength(line + word, font=FONT_S) > w - 32:
            d.text((16, y), line, font=FONT_S, fill=(30, 40, 50)); y += 19; line = ''
        line += word + ' '
    d.text((16, y), line, font=FONT_S, fill=(30, 40, 50))
    return im


def row(drawing, trial=1, gt=None):
    cell = BENCH / 'runs' / drawing / 'usd-brep' / f'trial-{trial:02d}'
    r = json.loads((cell / 'row.json').read_text())
    status = (r.get('product') or {}).get('status') or r.get('job_status')

    # mesh provenance: ONLY the harness-archived copy, hash-verified vs row
    mesh = None
    if r.get('build') and (r['build'] or {}).get('sha256'):
        archived = cell / 'stl' / 'model.stl'
        if not archived.exists():
            raise SystemExit(f'{drawing}: archived STL missing — refusing to compose')
        if sha256(archived) != r['build']['sha256']:
            raise SystemExit(f'{drawing}: archived STL hash != row build.sha256 — refusing')
        mesh = archived

    panels = {'input': {'path': str((cell / 'input.png').relative_to(BENCH)),
                        'sha256': sha256(cell / 'input.png')}}
    left = thumb(cell / 'input.png')
    if mesh:
        render_stl(mesh, OUT / f'{drawing}_usd-brep_t{trial}_brep.png')
        mid = thumb(OUT / f'{drawing}_usd-brep_t{trial}_brep.png')
        cap_mid = f'usd-brep built [{status}] (mesh sha {r["build"]["sha256"][:12]})'
        panels['brep_mesh'] = {'path': str(mesh.relative_to(BENCH)), 'sha256': r['build']['sha256']}
    else:
        msg = (r.get('error') or {}).get('message', 'no mesh produced')
        mid = refusal_panel(msg)
        cap_mid = 'usd-brep: refused at model stage (no mesh)'
        panels['brep_mesh'] = {'path': None, 'sha256': None}
    if gt:
        gp = Path(gt)
        if gp.suffix == '.stl':
            render_stl(gp, OUT / f'{drawing}_t{trial}_gt.png')
            g = thumb(OUT / f'{drawing}_t{trial}_gt.png')
            cap_right = 'ground truth (reference STL)'
            panels['gt'] = {'path': str(Path(gt).relative_to(BENCH)), 'sha256': sha256(gt)}
        else:
            g = thumb(gp)
            cap_right = 'ground truth (pipeline render)'
            panels['gt'] = {'path': str(gp.relative_to(BENCH)), 'sha256': sha256(gp)}
    else:
        der = ROOT / 'benchmarks/cases' / drawing / 'derived' / 'view-isometric.png'
        g = thumb(der)
        cap_right = 'ground truth (pipeline render)'
        panels['gt'] = {'path': 'repo:' + str(der.relative_to(ROOT)), 'sha256': sha256(der)}

    b = r.get('build') or {}
    facts = (f"measured: genus={b.get('genus')} extents={b.get('extents_mm')} "
             f"volume={b.get('volume_mm3')}mm3")
    fails = '; '.join((r.get('product') or {}).get('failures') or []) \
        or ((r.get('error') or {}).get('message') or '')

    W, H, LBL = 420 * 3 + 32, 300 + 34 + 96, 40
    # layout invariant (round-2 footer overlap): footer band must sit fully
    # below the caption line — constants checked, not eyeballed
    assert H - 66 > (LBL + 300 + 6 + 18), "footer would overlap panel captions"
    sheet = Image.new('RGB', (W, H), (250, 250, 250))
    d = ImageDraw.Draw(sheet)
    d.text((12, 8), f'{drawing}   ·   usd-brep trial {trial}', font=FONT, fill=(20, 30, 40))
    for i, (im, cap) in enumerate(((left, 'input drawing (sheet)'), (mid, cap_mid), (g, cap_right))):
        x = 8 + i * 420
        sheet.paste(im, (x, LBL))
        d.text((x + 6, LBL + 300 + 6), cap, font=FONT_S, fill=(60, 70, 80))
    d.text((12, H - 66), facts[:185], font=FONT_S, fill=(30, 40, 60))
    d.text((12, H - 42), ('failure: ' + fails)[:185], font=FONT_S, fill=(150, 40, 30))
    name = f'{drawing}_t{trial}.png'
    sheet.save(OUT / name)

    prov_file = OUT / 'provenance.json'
    prov = json.loads(prov_file.read_text()) if prov_file.exists() else {}
    prov[name] = {'row': str((cell / 'row.json').relative_to(BENCH)),
                  'row_sha256': sha256(cell / 'row.json'),
                  'image_sha256': sha256(OUT / name), 'verdict': status,
                  'measured': facts, 'failures': fails, 'panels': panels}
    prov_file.write_text(json.dumps(prov, indent=2))
    print('row', name, '|', status)


if __name__ == '__main__':
    for f in OUT.glob('*.png'):
        f.unlink()
    (OUT / 'provenance.json').unlink(missing_ok=True)
    row('003_front_grille_multiview')
    row('101_bltouch_bracket')
    row('007_angle_bracket_holes')
    row('wheel', trial=2, gt=BENCH / 'references' / 'wheel-reference.stl')
    row('constant_radius_handle', gt=BENCH / 'references' / 'curved_handle-reference.stl')
    row('002_greek_vase_silhouette')
