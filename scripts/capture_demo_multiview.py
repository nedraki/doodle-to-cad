"""Demo v2: hand-draw the benchmark-style multiview bookend sheet with the pen.

Front view = plate outline with FOUR rectangular through-cutout loops;
right view = thin L side profile, heights aligned. NO text notes — the
pipeline must infer everything from ink alone. Then: generate, orbit to
show the holes, and dump the STL path for geometric verification.

Output: docs/demo/mv_*.png + docs/demo/video_mv/*.webm + last_run.json
"""
import json
import random
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

BASE = "http://127.0.0.1:8066"
OUT = Path("docs/demo")
SHOT = 20
rng = random.Random(7)


def shot(page, name):
    global SHOT
    p = OUT / f"{SHOT:02d}_{name}.png"
    page.screenshot(path=str(p))
    print(f"[shot] {p}", flush=True)
    SHOT += 1


def wobbly(page, x0, y0, x1, y1, amp=1.6, step=6):
    """A straight-ish hand stroke: subdivided, jittered, drawn as one drag."""
    n = max(3, int(max(abs(x1 - x0), abs(y1 - y0)) / step))
    page.mouse.move(x0 + rng.uniform(-1, 1), y0 + rng.uniform(-1, 1))
    page.mouse.down()
    for k in range(1, n + 1):
        t = k / n
        nx = (rng.uniform(-amp, amp) if 0 < k < n else 0)
        ny = (rng.uniform(-amp, amp) if 0 < k < n else 0)
        page.mouse.move(x0 + (x1 - x0) * t + nx, y0 + (y1 - y0) * t + ny)
        page.wait_for_timeout(4)
    page.mouse.up()
    page.wait_for_timeout(30)


def rect(page, x, y, w, h, corner_overshoot=True):
    """Rectangle as 4 strokes with small corner overshoots = hand-drawn look."""
    o = 3 if corner_overshoot else 0
    wobbly(page, x - o, y, x + w + o, y)
    wobbly(page, x + w, y - o, x + w, y + h + o)
    wobbly(page, x + w + o, y + h, x - o, y + h)
    wobbly(page, x, y + h + o, x, y - o)


def l_profile(page, x, y, w, h, t):
    """Thin L: vertical leg left, foot along bottom (side view of bookend)."""
    wobbly(page, x, y, x + t, y)                       # top of wall
    wobbly(page, x + t, y, x + t, y + h - t)           # wall inner face
    wobbly(page, x + t, y + h - t, x + w, y + h - t)   # foot top
    wobbly(page, x + w, y + h - t, x + w, y + h)       # foot end
    wobbly(page, x + w, y + h, x, y + h)               # bottom
    wobbly(page, x, y + h, x, y)                       # back outer face


with sync_playwright() as pw:
    browser = pw.chromium.launch(
        headless=False,
        args=["--use-gl=angle", "--use-angle=swiftshader",
              "--enable-unsafe-swiftshader", "--ignore-gpu-blocklist"])
    ctx = browser.new_context(
        viewport={"width": 1440, "height": 900},
        record_video_dir=str(OUT / "video_mv"),
        record_video_size={"width": 1440, "height": 900})
    page = ctx.new_page()
    page.set_default_timeout(900_000)
    page.goto(BASE, wait_until="networkidle")
    page.wait_for_timeout(2500)

    page.fill('input[name="dimension"]', "100")   # reference height 100 mm

    c = page.query_selector("#canvas").bounding_box()
    ox, oy = c["x"], c["y"]
    print(f"[canvas] {c}", flush=True)

    # ---- FRONT view (left): plate with four rectangular cutout loops ----
    rect(page, ox + 110, oy + 95, 300, 430)                    # plate outline
    rect(page, ox + 140, oy + 125, 90, 55)                     # squarish, upper-left
    rect(page, ox + 265, oy + 120, 28, 150)                    # narrow vert, upper-mid
    rect(page, ox + 140, oy + 330, 30, 160)                    # narrow vert, lower-left
    rect(page, ox + 335, oy + 300, 30, 190)                    # narrow vert, lower-right
    shot(page, "mv_front_done")

    # ---- RIGHT view: thin L profile, top aligned with front view ----
    l_profile(page, ox + 520, oy + 95, 190, 430, 52)  # 12% wall, like the reference sketch
    shot(page, "mv_sheet_done")

    page.fill('textarea[name="notes"]', "L-shaped bookend")  # family hint only
    # ---- launch ----
    page.click("#launch")
    page.wait_for_selector("#working:not([hidden])", timeout=10_000)
    page.wait_for_timeout(5000)
    shot(page, "mv_rocket_flight")

    t0 = time.time()
    page.wait_for_selector("#result:not([hidden])", timeout=900_000)
    print(f"[gen] done in {time.time() - t0:.0f}s", flush=True)
    page.wait_for_timeout(7000)

    badge = page.text_content("#statusBadge") or "?"
    title = page.text_content("#resultTitle") or "?"
    text = page.text_content("#resultText") or "?"
    print(f"[result] badge={badge!r} title={title!r}\n[text] {text!r}", flush=True)
    shot(page, "mv_result")

    # persist run info (stl url, score, attempts) from the DOM
    info = page.evaluate("""() => ({
        stl: document.querySelector('#stl')?.getAttribute('href'),
        scad: document.querySelector('#scad')?.getAttribute('href'),
        badge: document.querySelector('#statusBadge')?.textContent,
        text: document.querySelector('#resultText')?.textContent
    })""")
    print(f"[run] {json.dumps(info)}", flush=True)
    (OUT / "last_run.json").write_text(json.dumps(info, indent=2))

    # orbit low so the cutouts face camera
    cv = page.query_selector("#viewerWrap canvas")
    bb = cv.bounding_box()
    cx, cy = bb["x"] + bb["width"] / 2, bb["y"] + bb["height"] / 2
    page.mouse.move(cx, cy)
    for _ in range(3):
        page.mouse.wheel(0, -110)
        page.wait_for_timeout(140)
    page.mouse.down()
    for i in range(90):
        page.mouse.move(cx + i * 5, cy - 25)
        page.wait_for_timeout(20)
    page.mouse.up()
    page.wait_for_timeout(1500)
    shot(page, "mv_orbit_a")
    # sweep the other way and pause where the perforated plate should face us
    page.mouse.down()
    for i in range(180):
        page.mouse.move(cx + 450 - i * 5, cy - 10)
        page.wait_for_timeout(18)
    page.mouse.up()
    page.wait_for_timeout(1500)
    shot(page, "mv_orbit_b")

    ctx.close()
    browser.close()

vid = sorted((OUT / "video_mv").glob("*.webm"))
print("VIDEO:", vid[-1] if vid else "NONE")
