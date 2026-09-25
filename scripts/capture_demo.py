"""Drive doodle-to-CAD end-to-end and capture a demo video + screenshots.

Captures: empty app -> live doodle drawing -> generation in flight -> 3D result
-> orbit -> parametric sliders with live recompile. Output in docs/demo/.
"""
import math
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

BASE = "http://127.0.0.1:8066"
OUT = Path("docs/demo")
OUT.mkdir(parents=True, exist_ok=True)
SHOT = 1


def shot(page, name):
    global SHOT
    p = OUT / f"{SHOT:02d}_{name}.png"
    page.screenshot(path=str(p), full_page=False)
    print(f"[shot] {p}", flush=True)
    SHOT += 1


def draw(page, points, pause=0.0):
    page.mouse.move(*points[0])
    page.mouse.down()
    for i in range(1, len(points)):
        x0, y0 = points[i - 1]
        x1, y1 = points[i]
        steps = max(4, int(math.hypot(x1 - x0, y1 - y0) / 4))
        for k in range(1, steps + 1):
            page.mouse.move(x0 + (x1 - x0) * k / steps,
                            y0 + (y1 - y0) * k / steps)
            page.wait_for_timeout(4)
    page.mouse.up()
    if pause:
        page.wait_for_timeout(int(pause * 1000))


def rect(x, y, w, h):
    return [(x, y), (x + w, y), (x + w, y + h), (x, y + h), (x, y)]


def ellipse(cx, cy, rx, ry, n=48):
    return [(cx + rx * math.cos(2 * math.pi * i / n),
             cy + ry * math.sin(2 * math.pi * i / n)) for i in range(n + 1)]


with sync_playwright() as pw:
    browser = pw.chromium.launch(
        headless=False,
        args=["--use-gl=angle", "--use-angle=swiftshader",
              "--enable-unsafe-swiftshader", "--ignore-gpu-blocklist"])
    ctx = browser.new_context(
        viewport={"width": 1440, "height": 900},
        record_video_dir=str(OUT / "video"), record_video_size={"width": 1440, "height": 900})
    page = ctx.new_page()
    page.set_default_timeout(900_000)

    t0 = time.time()
    page.goto(BASE, wait_until="networkidle")
    page.wait_for_timeout(2500)
    shot(page, "app_empty")

    # --- notes + dimension ---
    page.fill('textarea[name="notes"]', "L-shaped book end with a round thumb hole")
    page.fill('input[name="dimension"]', "120")

    # --- doodle: L-shaped bookend profile + circle ---
    c = page.query_selector("#canvas").bounding_box()
    ox, oy = c["x"], c["y"]
    draw(page, [(ox + 300, oy + 170), (ox + 560, oy + 165), (ox + 565, oy + 250),
                (ox + 380, oy + 255), (ox + 375, oy + 620), (ox + 300, oy + 625)], pause=0.4)
    draw(page, ellipse(ox + 460, oy + 380, 62, 58), pause=0.8)
    shot(page, "doodle_drawn")

    # --- launch ---
    page.click("#launch")
    page.wait_for_selector("#working:not([hidden])", timeout=10_000)
    page.wait_for_timeout(4000)
    shot(page, "rocket_flight")

    # --- wait for result (agentic pipeline: LLM + OpenSCAD + supervisor) ---
    page.wait_for_selector("#result:not([hidden])", timeout=900_000)
    print(f"[gen] done in {time.time() - t0:.0f}s", flush=True)
    page.wait_for_timeout(6000)  # let STL load + viewer spin up
    shot(page, "result_3d")

    # --- orbit the model ---
    page.mouse.move(ox + 400, oy + 400)
    page.mouse.down()
    for i in range(45):
        page.mouse.move(ox + 400 + i * 8, oy + 400 + (18 if i > 22 else 0))
        page.wait_for_timeout(16)
    page.mouse.up()
    page.wait_for_timeout(800)
    shot(page, "orbit")

    # --- parametric sliders ---
    page.click("#modify")
    page.wait_for_selector("#paramPanel:not([hidden])", timeout=30_000)
    page.wait_for_timeout(1500)
    shot(page, "param_panel")

    sliders = page.query_selector_all("#paramSliders input[type=range]")
    print(f"[params] {len(sliders)} sliders", flush=True)
    for sl in sliders[:2]:
        bb = sl.bounding_box()
        if not bb:
            continue
        page.mouse.move(bb["x"] + bb["width"] * 0.5, bb["y"] + bb["height"] / 2)
        page.mouse.down()
        page.mouse.move(bb["x"] + bb["width"] * 0.82, bb["y"] + bb["height"] / 2, steps=12)
        page.mouse.up()
        page.wait_for_timeout(600)
    page.wait_for_function(
        "document.querySelector('#paramStatus')?.textContent.includes('param')",
        timeout=180_000)
    page.wait_for_timeout(3500)
    shot(page, "param_live")

    ctx.close()  # flushes the video
    browser.close()

vid = sorted((OUT / "video").glob("*.webm"))
print("VIDEO:", vid[-1] if vid else "NONE")
