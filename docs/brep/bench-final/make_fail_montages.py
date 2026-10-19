"""Compose failure montages for docs/brep/bench-final.

Rows: [input drawing | what usd-brep built | ground truth], captioned with the
published verdict/failure text. Renders missing meshes through the product's
own CadViewer (wall app on 8114); reuses pipeline view-isometric.png renders
where the run saved them.
"""
import glob
import json
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


def render_stl(stl_path, out_png, view='isometric'):
    dst = RENDER_SERVE / f"{out_png.stem}.stl"
    shutil.copy2(stl_path, dst)
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        import os
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
    d.text((16, 14), 'KERNEL REFUSAL (published)', font=FONT, fill=(180, 40, 20))
    words, line, y = text.split(), '', 52
    for word in words:
        while d.textlength(line + word, font=FONT_S) > w - 32:
            d.text((16, y), line, font=FONT_S, fill=(30, 40, 50)); y += 19; line = ''
        line += word + ' '
    d.text((16, y), line, font=FONT_S, fill=(30, 40, 50))
    return im


def brep_stl(run_id):
    hits = sorted(glob.glob(f'{ROOT}/results/bench-final/{run_id}/brep-*/model.stl'))
    return hits[-1] if hits else None


def row(drawing, backend='usd-brep', trial=1, gt=None, os_alt=None, refusal=None):
    runs = json.load(open(BENCH / 'runs' / drawing / backend / f'trial-{trial:02d}' / 'row.json'))
    input_png = BENCH / 'runs' / drawing / backend / f'trial-{trial:02d}' / 'input.png'
    left = thumb(input_png)
    rid = runs.get('run_id')
    status = (runs.get('product') or {}).get('status') or runs.get('job_status')
    fails = '; '.join((runs.get('product') or {}).get('failures') or [])[:150]
    if refusal:
        mid = refusal_panel(refusal)
        cap_mid = 'usd-brep: refused (no mesh)'
    else:
        stl = brep_stl(rid)
        mid = thumb(render_stl(stl, OUT / f'{drawing}_{backend}_t{trial}_brep.png')) if stl \
            else refusal_panel('no mesh was produced for this trial')
        cap_mid = f'usd-brep built  [{status}]'
    if gt:
        gp = Path(gt)
        if gp.suffix == '.stl':
            gp = render_stl(gp, OUT / f'{drawing}_t{trial}_gt.png')
        g = thumb(gp)
        cap_right = 'ground truth (reference STL)'
    else:
        der = ROOT / 'benchmarks/cases' / drawing / 'derived' / 'view-isometric.png'
        g = thumb(der)
        cap_right = 'ground truth (pipeline render)'
    W, H, LBL, CAP = 420 * 3 + 32, 300 + 34 + 66, 40, 44
    sheet = Image.new('RGB', (W, H), (250, 250, 250))
    d = ImageDraw.Draw(sheet)
    d.text((12, 8), f'{drawing}   ·   usd-brep trial {trial}', font=FONT, fill=(20, 30, 40))
    for i, (im, cap) in enumerate(((left, 'input drawing (sheet)'), (mid, cap_mid), (g, cap_right))):
        x = 8 + i * 420
        sheet.paste(im, (x, LBL))
        d.text((x + 6, LBL + 300 + 6), cap, font=FONT_S, fill=(60, 70, 80))
    d.text((12, H - 30), ('failure: ' + (fails or refusal or ''))[:170], font=FONT_S, fill=(150, 40, 30))
    name = f'{drawing}_t{trial}.png'
    sheet.save(OUT / name)
    print('row', name, '|', status)


if __name__ == '__main__':
    row('003_front_grille_multiview')
    row('101_bltouch_bracket')
    row('007_angle_bracket_holes')
    row('wheel', trial=2, gt=BENCH / 'references' / 'wheel-reference.stl')
    row('constant_radius_handle', gt=BENCH / 'references' / 'curved_handle-reference.stl')
    vase = json.load(open(BENCH / 'runs' / '002_greek_vase_silhouette' / 'usd-brep' / 'trial-01' / 'row.json'))
    msg = (vase.get('error') or {}).get('message', '')
    # rebuild the vase row manually: input + refusal panel + no GT render available
    import PIL.Image as I
    runs_dir = BENCH / 'runs' / '002_greek_vase_silhouette' / 'usd-brep' / 'trial-01'
    left = thumb(runs_dir / 'input.png')
    mid = refusal_panel(msg)
    gtf = ROOT / 'benchmarks/cases/002_greek_vase_silhouette/derived/view-isometric.png'
    g = thumb(gtf)
    W, H, LBL = 420 * 3 + 32, 300 + 34 + 66, 40
    sheet = I.new('RGB', (W, H), (250, 250, 250))
    d = ImageDraw.Draw(sheet)
    d.text((12, 8), '002_greek_vase_silhouette   ·   usd-brep trial 1', font=FONT, fill=(20, 30, 40))
    for i, (im, cap) in enumerate(((left, 'input drawing (sheet)'),
                                   (mid, 'usd-brep: refused'),
                                   (g, 'ground truth (pipeline render)'))):
        x = 8 + i * 420
        sheet.paste(im, (x, LBL))
        d.text((x + 6, LBL + 300 + 6), cap, font=FONT_S, fill=(60, 70, 80))
    d.text((12, H - 30), msg[:170], font=FONT_S, fill=(150, 40, 30))
    sheet.save(OUT / '002_greek_vase_silhouette_t1.png')
    print('rows done')
