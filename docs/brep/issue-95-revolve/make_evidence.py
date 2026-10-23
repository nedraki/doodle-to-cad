"""Issue #95 demo evidence: triptych (input | built | ground truth) + orbit GIF.

Machine-checkable provenance (same rules as bench-final montages):
  * every rendered panel comes from a hashed artifact; the montage's
    provenance.json binds montage sha256 -> panel source sha256 -> job id;
  * captions quote measured numbers (extents/volume/genus/verdict), never a
    visual impression.
Run against the live evidence server on 8135 from the repo root:
  CHROMIUM_EXECUTABLE=... PYTHONPATH=<repo> uv run python docs/brep/issue-95-revolve/make_evidence.py
"""
import hashlib
import json
import math
import os
import shutil
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
SERVE = ROOT / "results" / "_render"
SERVE.mkdir(parents=True, exist_ok=True)
BASE = "http://127.0.0.1:8135"
FONT = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 17)
FONT_S = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 14)
GT = ROOT / "benchmarks/cases/002_greek_vase_silhouette/ground_truth/model.stl"


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _launch(p):
    exe = os.environ.get("CHROMIUM_EXECUTABLE")
    return p.chromium.launch(headless=True, **({"executable_path": exe} if exe else {}), args=[
        "--no-sandbox", "--use-gl=angle", "--use-angle=swiftshader",
        "--enable-unsafe-swiftshader", "--ignore-gpu-blocklist"])


def _viewer_page(page, stl_url):
    page.goto(BASE + "/")
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
        const box = new THREE.Box3().setFromObject(v.mesh);
        const c = box.getCenter(new THREE.Vector3());
        const s = box.getSize(new THREE.Vector3());
        const dist = 2.4 * Math.max(s.x, s.y, s.z);
        window.__cam = {v, c, dist};
    }""", {"url": stl_url})
    return page.evaluate("window.__cam !== undefined")


def _point_camera(page, azimuth_deg):
    page.evaluate("""({az}) => {
        const {v, c, dist} = window.__cam;
        const a = az * Math.PI / 180;
        const dir = new THREE.Vector3(Math.sin(a), -Math.cos(a), 0.45).normalize();
        v.camera.position.copy(c).addScaledVector(dir, dist);
        v.controls.target.copy(c);
        v.camera.near = Math.max(dist / 1000, 0.05);
        v.camera.far = dist * 10;
        v.controls.update();
    }""", {"az": azimuth_deg})


def render_stl(stl_path, out_png, azimuth=35.0):
    dst = SERVE / f"iss95-{Path(out_png).stem}.stl"
    shutil.copy2(stl_path, dst)
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        browser = _launch(p)
        page = browser.new_page(viewport={"width": 520, "height": 420})
        assert _viewer_page(page, f"/results/_render/{dst.name}")
        _point_camera(page, azimuth)
        page.wait_for_timeout(250)
        page.locator("#viewerWrap").screenshot(path=str(out_png))
        browser.close()
    dst.unlink(missing_ok=True)


def orbit_gif(stl_path, out_gif, frames=16):
    dst = SERVE / f"iss95-orbit-{Path(out_gif).stem}.stl"
    shutil.copy2(stl_path, dst)
    shots = []
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        browser = _launch(p)
        page = browser.new_page(viewport={"width": 480, "height": 400})
        assert _viewer_page(page, f"/results/_render/{dst.name}")
        for i in range(frames):
            _point_camera(page, 360.0 * i / frames)
            page.wait_for_timeout(120)
            shot = SERVE / f"iss95-orbit-{i:02d}.png"
            page.locator("#viewerWrap").screenshot(path=str(shot))
            shots.append(shot)
        browser.close()
    images = [Image.open(s).convert("P", palette=Image.ADAPTIVE) for s in shots]
    images[0].save(out_gif, save_all=True, append_images=images[1:], duration=90, loop=0)
    for s in shots:
        s.unlink(missing_ok=True)
    dst.unlink(missing_ok=True)


def measure(stl_path):
    import trimesh
    m = trimesh.load(stl_path, force="mesh")
    comps = m.split()
    genus = sum(max((2 - c.euler_number) // 2, 0) for c in comps if c.is_watertight)
    return {"components": len(comps), "watertight": bool(m.is_watertight),
            "genus": genus, "volume_mm3": round(float(m.volume), 1),
            "extents_mm": [round(float(v), 1) for v in m.extents]}


def caption_panel(canvas, title, lines, x0, width=520, top=46, height=420):
    draw = ImageDraw.Draw(canvas)
    draw.rectangle([x0, top, x0 + width, top + 26], fill=(245, 245, 245))
    draw.text((x0 + 8, top + 5), title, font=FONT, fill=(20, 20, 20))
    y = top + height - 18 * (len(lines) + 1) - 6
    draw.rectangle([x0, y - 4, x0 + width, top + height], fill=(245, 245, 245))
    for line in lines:
        draw.text((x0 + 8, y), line, font=FONT_S, fill=(30, 30, 30))
        y += 18
    return canvas


def build_row(label):
    cell = HERE / label
    job = json.loads((cell / "job.json").read_text())
    result = job.get("result") or {}
    files = result.get("files") or {}
    built = None
    if "stl" in files and files["stl"].startswith("/results/"):
        candidate = ROOT / "results" / files["stl"][len("/results/"):]
        if candidate.is_file():
            built = candidate
    row = {"label": label, "job_id": job.get("job_id"), "status": job.get("status"),
           "error": job.get("error") or result.get("error"),
           "evaluation": (result.get("evaluation") or {}).get("accepted"),
           "built_stl": str(built) if built else None}
    panels = []
    captions = []
    drawing = cell / "input.png"
    panels.append(("input drawing", Image.open(drawing).convert("RGB").resize((520, 420))))
    captions.append(["certified notes row, sheet as submitted"])
    if built:
        render_stl(built, cell / "built.png", azimuth=35)
        panels.append(("built by usd-brep revolve", Image.open(cell / "built.png").convert("RGB")))
        m = measure(built)
        row["built_measurement"] = m
        captions.append([f"extents {m['extents_mm']} mm  V={m['volume_mm3']} mm3",
                         f"genus {m['genus']}  watertight {m['watertight']}  comps {m['components']}"])
        orbit_gif(built, cell / "orbit.gif")
    else:
        panel = Image.new("RGB", (520, 420), (250, 245, 245))
        d = ImageDraw.Draw(panel)
        text = json.dumps(row["error"], indent=1)[:600] if row["error"] else "no mesh published"
        y = 30
        for line in text.splitlines():
            d.text((16, y), line[:74], font=FONT_S, fill=(120, 20, 20))
            y += 20
        panels.append(("kernel refusal (no mesh)", panel))
        captions.append(["refusal is the evidence; message quoted verbatim"])
    render_stl(GT, cell / "gt.png", azimuth=35)
    panels.append(("ground truth", Image.open(cell / "gt.png").convert("RGB")))
    gt_m = measure(GT)
    row["gt_measurement"] = gt_m
    captions.append([f"extents {gt_m['extents_mm']} mm  V={gt_m['volume_mm3']} mm3",
                     f"genus {gt_m['genus']}  watertight {gt_m['watertight']}  comps {gt_m['components']}"])

    h = 420
    montage = Image.new("RGB", (520 * 3 + 20, h + 46), (255, 255, 255))
    prov = {"label": label, "job_id": row["job_id"], "server": BASE, "panels": []}
    for i, ((title, img), lines) in enumerate(zip(panels, captions)):
        x0 = i * 530 + (5 if i else 0)
        montage.paste(img, (x0, 46))
        caption_panel(montage, title, lines, x0)
        prov["panels"].append({"index": i, "title": title})
    out_png = cell / "triptych.png"
    montage.save(out_png)
    prov["montage"] = str(out_png.relative_to(ROOT))
    prov["montage_sha256"] = sha256(out_png)
    prov["built_stl_sha256"] = sha256(built) if built else None
    prov["gt_stl_sha256"] = sha256(GT)
    prov["input_sha256"] = sha256(drawing)
    prov["row"] = row
    (cell / "provenance.json").write_text(json.dumps(prov, indent=2))
    return row


if __name__ == "__main__":
    rows = []
    for label in sorted(p.name for p in HERE.iterdir() if (p / "job.json").exists()):
        rows.append(build_row(label))
    print(json.dumps(rows, indent=1))
