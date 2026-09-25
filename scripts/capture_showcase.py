"""Short polished 3D showcase clip: load last accepted result, orbit the model
a full turn (thumb hole sweeps into view), then live parametric reshape.
Companion to capture_demo.py — output in docs/demo/."""
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

BASE = "http://127.0.0.1:8066"
OUT = Path("docs/demo")
SHOT = 10


def shot(page, name):
    global SHOT
    p = OUT / f"{SHOT:02d}_{name}.png"
    page.screenshot(path=str(p))
    print(f"[shot] {p}", flush=True)
    SHOT += 1


with sync_playwright() as pw:
    browser = pw.chromium.launch(
        headless=False,
        args=["--use-gl=angle", "--use-angle=swiftshader",
              "--enable-unsafe-swiftshader", "--ignore-gpu-blocklist"])
    ctx = browser.new_context(
        viewport={"width": 1440, "height": 900},
        record_video_dir=str(OUT / "video2"),
        record_video_size={"width": 1440, "height": 900})
    page = ctx.new_page()
    page.goto(BASE, wait_until="networkidle")
    page.wait_for_timeout(2500)

    # load the last accepted result directly (no regeneration)
    page.click("#viewLatest")
    page.wait_for_selector("#result:not([hidden])", timeout=30_000)
    page.wait_for_timeout(7000)  # STL fetch + viewer spin-up
    shot(page, "showcase_loaded")

    # find the viewer canvas and orbit a full turn around the model
    cv = page.query_selector("#viewerWrap canvas")
    bb = cv.bounding_box()
    cx, cy = bb["x"] + bb["width"] / 2, bb["y"] + bb["height"] / 2
    # zoom in a bit first (scroll up)
    page.mouse.move(cx, cy)
    for _ in range(4):
        page.mouse.wheel(0, -120)
        page.wait_for_timeout(150)
    page.wait_for_timeout(600)

    # slow continuous horizontal drag = azimuth sweep (back and forth)
    page.mouse.move(cx, cy)
    page.mouse.down()
    for i in range(200):
        page.mouse.move(cx + i * 5, cy - 30)
        page.wait_for_timeout(20)
    page.mouse.up()
    page.wait_for_timeout(1000)

    # pause on the back side where the hole should face camera; nudge to find it
    for ang_label in ("sweep_a", "sweep_b"):
        page.mouse.move(cx, cy)
        page.mouse.down()
        for i in range(60):
            page.mouse.move(cx + i * 4, cy - 40)
            page.wait_for_timeout(20)
        page.mouse.up()
        page.wait_for_timeout(1200)
        shot(page, f"showcase_{ang_label}")
        page.mouse.move(cx, cy)
        page.mouse.down()
        for i in range(60):
            page.mouse.move(cx - i * 4, cy - 40)
            page.wait_for_timeout(20)
        page.mouse.up()
        page.wait_for_timeout(800)

    # parametric reshape with auto-rotate kept on
    page.click("[data-rotate='1']")  # toggle auto-rotate on
    page.click("#modify")
    page.wait_for_selector("#paramPanel:not([hidden])", timeout=30_000)
    page.wait_for_timeout(1200)
    sl = page.query_selector_all("#paramSliders input[type=range]")
    if sl:
        bb2 = sl[0].bounding_box()
        page.mouse.move(bb2["x"] + bb2["width"] * 0.5, bb2["y"] + bb2["height"] / 2)
        page.mouse.down()
        page.mouse.move(bb2["x"] + bb2["width"] * 0.85, bb2["y"] + bb2["height"] / 2, steps=15)
        page.mouse.up()
        page.wait_for_function(
            "document.querySelector('#paramStatus')?.textContent.includes('param')",
            timeout=180_000)
        page.wait_for_timeout(4000)
    shot(page, "showcase_param")

    ctx.close()
    browser.close()

vid = sorted((OUT / "video2").glob("*.webm"))
print("VIDEO:", vid[-1] if vid else "NONE")
