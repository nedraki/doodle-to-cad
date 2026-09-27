"""Browser regression checks and optional orbit capture against a running app.

Run with .venv/bin/python scripts/check_viewer.py --base-url http://127.0.0.1:8080
Requires the dev Playwright browser installation. No generation requests are made.
"""
import argparse
import io
import json
from pathlib import Path
from urllib.request import urlopen

import trimesh
from PIL import Image
from playwright.sync_api import sync_playwright


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:8080")
    parser.add_argument("--browser", help="Optional installed Chromium executable")
    parser.add_argument("--run-id", help="Existing result to display; defaults to latest")
    parser.add_argument("--output", type=Path, help="Save screenshots and an orbit GIF")
    args = parser.parse_args()
    base = args.base_url.rstrip("/")
    result_url = f"{base}/results/{args.run_id}/result.json" if args.run_id else f"{base}/api/results/latest"
    with urlopen(result_url) as response:
        result = json.load(response)
    assert result["files"]["stl"], "Choose an existing result with an STL"

    with sync_playwright() as pw:
        browser = pw.chromium.launch(
            executable_path=args.browser, headless=True,
            args=["--use-angle=swiftshader", "--enable-unsafe-swiftshader"],
        )
        page = browser.new_page(viewport={"width": 1440, "height": 1000})
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.route("**/api/results/latest", lambda route: route.fulfill(json=result))
        page.goto(base)
        # Match the existing run's size control for an honest result screenshot.
        dimension = result.get("spec", {}).get("user_intent", {}).get("authoritative_max_dimension_mm")
        if dimension:
            page.fill('input[name="dimension"]', str(dimension))
        page.click("#viewLatest")
        page.wait_for_function("viewer && viewer.mesh")
        page.wait_for_timeout(200)
        assert page.evaluate("viewer.camera.up.toArray()") == [0, 0, 1]
        assert not page.evaluate("viewer.controls.autoRotate")
        assert page.evaluate("""() => {
          viewer.grid.updateMatrixWorld();
          const p = viewer.grid.geometry.attributes.position;
          for (let i = 0; i < p.count; i++) {
            const point = new THREE.Vector3().fromBufferAttribute(p, i).applyMatrix4(viewer.grid.matrixWorld);
            if (Math.abs(point.z + 0.02) > 1e-6) return false;
          }
          return true;
        }"""), "Build grid must lie in the XY plane"

        # Saved run metadata, rather than the current input form, selects Drawing view.
        for primary in ("front", "top", "right", "left", "rear", "bottom"):
            page.evaluate("async primary => { await viewer.showStl(currentRun.files.stl, primary); }", primary)
            direction = page.evaluate("viewer.camera.position.clone().sub(viewer.controls.target).normalize().toArray()")
            expected = {"front": (1, -1), "rear": (1, 1), "right": (0, 1),
                        "left": (0, -1), "top": (2, 1), "bottom": (2, -1)}[primary]
            assert abs(direction[expected[0]] - expected[1]) < 1e-6, (primary, direction)

        # Check screen handedness, especially top +Y up and right +Y right.
        for view, horizontal, vertical in (("front", [1, 0, 0], [0, 0, 1]),
                                           ("top", [1, 0, 0], [0, 1, 0]),
                                           ("right", [0, 1, 0], [0, 0, 1])):
            page.evaluate("name => viewer.setView(name)", view)
            assert page.evaluate("""([horizontal, vertical]) => {
              viewer.camera.updateMatrixWorld();
              const center = viewer.controls.target.clone();
              const origin = center.clone().project(viewer.camera);
              const h = center.clone().add(new THREE.Vector3(...horizontal)).project(viewer.camera);
              const v = center.clone().add(new THREE.Vector3(...vertical)).project(viewer.camera);
              return h.x > origin.x && v.y > origin.y;
            }""", [horizontal, vertical]), view

        # Exercise extreme aspect ratios with a translated, asymmetric bounding box.
        for extents in ([180, 25, 30], [25, 30, 180]):
            mesh = trimesh.creation.box(extents=extents)
            mesh.apply_translation([37, 61, extents[2] / 2])
            payload = mesh.export(file_type="stl")
            page.route("**/viewer-fixture.stl", lambda route: route.fulfill(body=payload, content_type="application/octet-stream"))
            page.evaluate("async () => { await viewer.showStl('/viewer-fixture.stl'); }")
            for width, height in ((1440, 1000), (1024, 768), (1920, 1080)):
                page.set_viewport_size({"width": width, "height": height})
                page.wait_for_timeout(100)
                for view in ("front", "top", "right", "isometric"):
                    page.evaluate("name => viewer.setView(name)", view)
                    assert_fits(page)
                page.evaluate("document.querySelector('#paramPanel').hidden = false")
                page.wait_for_timeout(100)
                assert_fits(page)
                page.evaluate("document.querySelector('#paramPanel').hidden = true")
                page.wait_for_timeout(100)
            page.unroute("**/viewer-fixture.stl")

        # Mesh replacement must not reset a manually chosen camera or target.
        page.evaluate("async () => { await viewer.showStl(currentRun.files.stl); viewer.setView('isometric'); }")
        canvas = page.locator(".viewer-viewport")
        box = canvas.bounding_box()
        page.mouse.move(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)
        page.mouse.down()
        page.mouse.move(box["x"] + box["width"] / 2 + 80, box["y"] + box["height"] / 2 + 20, steps=12)
        page.mouse.up()
        # Drain damping before comparing camera states (software rendering varies in fps).
        page.evaluate("viewer.controls.enableDamping = false; viewer.controls.update(); viewer.controls.enableDamping = true")
        camera = "[...viewer.camera.position.toArray(), ...viewer.controls.target.toArray()]"
        before = page.evaluate(camera)
        page.route("**/viewer-fixture.stl", lambda route: route.fulfill(body=payload, content_type="application/octet-stream"))
        page.evaluate("async () => { await viewer.replaceStl('/viewer-fixture.stl'); }")
        after = page.evaluate(camera)
        assert max(abs(a - b) for a, b in zip(before, after)) < 0.001
        page.unroute("**/viewer-fixture.stl")

        if args.output:
            args.output.mkdir(parents=True, exist_ok=True)
            page.set_viewport_size({"width": 1440, "height": 1000})
            page.evaluate("async () => { await viewer.showStl(currentRun.files.stl, currentRun.controls?.primary_view); }")
            page.wait_for_timeout(200)
            for view in ("drawing", "top", "right", "isometric"):
                page.click(f'[data-camera-view="{view}"]')
                page.wait_for_timeout(100)
                page.screenshot(path=str(args.output / f"{view}.png"))
            page.click('[data-rotate]')
            # Real rendered orbit frames; temporarily increase speed for a short demo.
            page.evaluate("viewer.controls.autoRotateSpeed = 8")
            frames = []
            for _ in range(36):
                page.wait_for_timeout(120)
                frames.append(Image.open(io.BytesIO(page.locator('#viewerWrap').screenshot())).convert('RGB'))
                assert_fits(page)
            frames[0].save(args.output / "orbit.gif", save_all=True, append_images=frames[1:], duration=150, loop=0)
            page.evaluate("viewer.setAutoRotate(false)")
            (args.output / "capture.json").write_text(json.dumps({"run_id": result["id"], "source": base}, indent=2))
        assert not errors, errors
        browser.close()
    print("PASS: camera directions, handedness, viewport/sidebar fitting, mesh replacement, browser errors")


def assert_fits(page):
    assert page.evaluate("""() => {
      viewer.camera.updateMatrixWorld();
      const box = new THREE.Box3().setFromObject(viewer.mesh);
      for (const x of [box.min.x, box.max.x])
        for (const y of [box.min.y, box.max.y])
          for (const z of [box.min.z, box.max.z]) {
            const p = new THREE.Vector3(x, y, z).project(viewer.camera);
            if (Math.abs(p.x) > 1 || Math.abs(p.y) > 1 || Math.abs(p.z) > 1) return false;
          }
      return true;
    }"""), "Model bounding box clipped by the viewport"


if __name__ == "__main__":
    main()
