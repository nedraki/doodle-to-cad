"""Issue #16 product evidence: targeted repair of the broken wheel in the real app.

Runs against a test server on http://127.0.0.1:8116 started from this worktree
(uv run uvicorn doodle_to_cad.app:app --host 127.0.0.1 --port 8116).

The pre-repair wheel is a CONTROLLED FIXTURE from scripts/make_repair_fixture.py
(spokes 5 mm short of the rim) seeded into the results dir — the generation step
is not a model-quality claim. The repair itself is real: live model calls via the
app's /revisions/repair endpoint, browser-driven Fix-this-part flow, trimesh
measurements of every preserved dimension.

Writes docs/repair/issue-16/product-final/: report.json, per-step screenshots
and the state JSONs returned by the API.
"""
import json, math, shutil, sys, uuid
from pathlib import Path
import httpx, trimesh
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from doodle_to_cad import config  # noqa: F401  (loads .env)
from doodle_to_cad.build_contract import BuildInput, build
from doodle_to_cad.openscad import mesh_health
from make_repair_fixture import SCAD  # same fixture the tests reference

OUT = ROOT / "docs/repair/issue-16/product-final"
OUT.mkdir(parents=True, exist_ok=True)
BASE = "http://127.0.0.1:8116"
INSTRUCTION = ("Connect every spoke to the rim. Keep the outer diameter, hub, "
               "spoke count, and thickness unchanged. Make the wheel one "
               "connected printable part.")
REFINE = ("The spokes still do not reach the rim. Extend each spoke a few mm "
          "further so it overlaps the rim's inner wall by at least 1 mm, then "
          "union everything. Keep the outer diameter, hub, spoke count, spoke "
          "width and thickness exactly unchanged.")

def save(name, data): (OUT / name).write_text(json.dumps(data, indent=2))

def download(client, url, dest):
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(client.get(BASE + url).content)

def measure(path: Path) -> dict:
    """Independent measurable checks: connectivity + preserved wheel dimensions.

    Wheel lies in XZ with thickness along Y (same layout as the benchmark).
    Occupancy sampling is done on the mid-thickness plane around the model centre.
    """
    mesh = trimesh.load(path, force="mesh")
    health = mesh_health(path)
    cx, cz = mesh.bounds[:, 0].mean(), mesh.bounds[:, 2].mean()
    my = mesh.bounds[:, 1].mean()
    def inside(r, a_deg):
        a = math.radians(a_deg)
        return bool(mesh.contains([[cx + r * math.cos(a), my, cz + r * math.sin(a)]]))
    def clusters(r):
        flags = [inside(r, a * 0.5) for a in range(720)]  # 0.5 deg sampling
        if not any(flags): return []
        idx = [i for i, f in enumerate(flags) if f]
        groups, start, prev = [], idx[0], idx[0]
        for i in idx[1:] + [None]:
            if i is None or i - prev > 4:  # >2 deg gap separates spokes
                groups.append((start, prev)); start = i
            if i is not None: prev = i
        if len(groups) > 1 and groups[0][0] == 0 and groups[-1][1] == 719:  # wrap
            groups[0] = (groups[-1][0] - 720, groups[0][1]); groups.pop()
        return [round((b - a + 1) * 0.5 * math.pi / 180 * r, 2) for a, b in groups]  # arc mm
    def radial(a_deg):
        runs, r, prev = [], 8.0, None
        while r <= 60:
            hit = inside(r, a_deg)
            if hit and prev is None: prev = r
            if not hit and prev is not None: runs.append([prev, round(r, 1)]); prev = None
            r += 0.5
        if prev is not None: runs.append([prev, 60.0])
        return runs
    return {**health,
            "hub_full_cover_radius_mm": max([r for r in (8, 10, 12, 14, 15) if all(inside(r, a) for a in range(0, 360, 5))], default=None),
            "spoke_count_at_r40": len([w for w in clusters(40) if w > 3]),
            "spoke_widths_at_r40_mm": [w for w in clusters(40) if w > 3],
            "spoke_widths_at_r50_mm": [w for w in clusters(50) if w > 3],
            "radial_material_at_0deg_mm": radial(0)}

def preserved(before, after):
    tol_rel, tol_abs = 0.02, 0.5
    dims = {}
    for i, axis in enumerate("xyz"):
        b, a = before["extents_mm"][i], after["extents_mm"][i]
        dims[f"extent_{axis}"] = {"before": b, "after": a,
            "preserved": abs(a - b) <= max(tol_abs, tol_rel * max(abs(b), abs(a)))}
    def close(key, rel=0.15, abs_floor=1.5):
        b, a = before[key], after[key]
        if b is None or a is None: return {"before": b, "after": a, "preserved": None}
        if isinstance(b, list):
            ok = len(b) == len(a) and all(abs(x - y) <= max(abs_floor, rel * max(abs(x), abs(y))) for x, y in zip(b, a))
        else:
            ok = b == a if key == "spoke_count_at_r40" else abs(a - b) <= max(abs_floor, rel * max(abs(b), abs(a)))
        return {"before": b, "after": a, "preserved": bool(ok)}
    for key in ("hub_full_cover_radius_mm", "spoke_count_at_r40", "spoke_widths_at_r40_mm"):
        dims[key] = close(key)
    return dims

run_id = uuid.uuid4().hex[:12]
out_dir = ROOT / "results" / run_id
report = {"run_id": run_id, "fixture": "scripts/make_repair_fixture.py broken wheel "
          "(synthetic, spokes short of rim); repair via live model calls"}
with httpx.Client(base_url=BASE, timeout=900) as client:
    # ---- seed the controlled broken-wheel run -------------------------------
    out_dir.mkdir(parents=True)
    (out_dir / "model.scad").write_text(SCAD)
    shutil.copy(ROOT / "benchmarks/brep-baseline/wheel/drawing.png", out_dir / "input.png")
    built = build(BuildInput("openscad", out_dir / "model.scad", out_dir), "openscad")
    assert built.stl, built.log[-2000:]
    result = {"id": run_id, "backend": "openscad", "success": True,
              "spec": {"object": "eight-spoke wheel"},
              "model": "fixture", "model_source": "seeded",
              "fixture": {"kind": "synthetic_broken_wheel",
                          "generator": "scripts/make_repair_fixture.py",
                          "authority": "Controlled test fixture, not a user doodle or generation claim."},
              "evaluation": {"accepted": True, "score": 88, "failures": []},
              "files": {"scad": f"/results/{run_id}/model.scad",
                        "source": f"/results/{run_id}/model.scad",
                        "stl": f"/results/{run_id}/model.stl",
                        "views": {k: f"/results/{run_id}/{v.name}" for k, v in built.views.items()}}}
    (out_dir / "result.json").write_text(json.dumps(result, indent=2))
    before = measure(out_dir / "model.stl")
    save("before-measurement.json", before)
    assert before["components"] == 2 and before["watertight"], before

    browser_errors = []
    attempts = []
    discarded_still_there = False
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True,
            executable_path="/home/sparkie/.cache/ms-playwright/chromium-1243/chrome-linux-arm64/chrome",
            args=["--no-sandbox", "--use-gl=angle", "--use-angle=swiftshader", "--enable-unsafe-swiftshader"])
        page = browser.new_page(viewport={"width": 1600, "height": 1300})
        page.on("pageerror", lambda e: browser_errors.append(str(e)))
        page.goto(BASE, wait_until="networkidle")
        page.evaluate("(r)=>render(r,null)", client.get(f"/api/results/{run_id}").json())
        page.wait_for_function("viewer?.mesh"); page.wait_for_timeout(1200)
        def capture(name):
            page.evaluate('viewer.setView("isometric")'); page.wait_for_timeout(600)
            page.locator("#result").screenshot(path=str(OUT / (name + ".png")))
        capture("broken")

        # ---- Fix this part -> instruction -> generate (real model call) ----
        def request_repair(instruction):
            page.click("#fixPart" if page.is_visible("#fixPart") else "#refineRepair")
            page.wait_for_selector("#repairDialog[open]")
            page.fill("#repairInstruction", instruction)
            with page.expect_response(
                    lambda r: r.request.method == "POST" and r.url.endswith("/revisions/repair"),
                    timeout=900000) as resp:
                page.click("#repairGenerate")
            response = resp.value
            data = response.json()
            entry = {"instruction": instruction, "status": response.status}
            if response.ok:
                page.wait_for_function("(id)=>currentRun?.revision?.id===id", arg=data["revision"]["id"])
                entry.update(revision_id=data["revision"]["id"],
                             checks={c["name"]: c["status"] for c in data["repair"]["checks"]},
                             started_from=data["repair"]["started_from"],
                             files=data["files"])
                stl = out_dir / Path(data["files"]["stl"]).relative_to(f"/results/{run_id}")
                entry["measurement"] = measure(stl)
                entry["preservation"] = preserved(before, entry["measurement"])
            else:
                entry["error"] = data.get("detail")
                err = page.locator("#repairError")
                entry["ui_error"] = err.text_content() if err.is_visible() else None
                page.click(".close-repair")
            attempts.append(entry); save("attempts.json", attempts)
            return response.ok, data

        ok, candidate = request_repair(INSTRUCTION)
        if ok:
            capture("repair-candidate")
            save("candidate.json", candidate)
        # Refine until one connected watertight part (max 3 attempts; all retained)
        n = 1
        while ok and n < 3 and not (candidate["repair"].get("checks") and
              {c["name"]: c["status"] for c in candidate["repair"]["checks"]}.get("connected_components") == "passed"):
            n += 1
            ok, candidate = request_repair(REFINE)
            if ok: capture(f"repair-candidate-{n}"); save(f"candidate-{n}.json", candidate)
        if not ok:
            report["repair_succeeded"] = False; report["attempts"] = attempts
            save("report.json", report); print(json.dumps(report, indent=2)); sys.exit(1)

        # ---- Keep the repair -------------------------------------------------
        page.click("#keepRevision")
        page.wait_for_function("currentRun?.revision?.candidate===false")
        kept = client.get(f"/api/results/{run_id}").json()
        save("kept.json", kept)
        assert kept["revision"]["id"] == candidate["revision"]["id"]
        assert kept["revision"]["parent_id"] == "original"
        assert page.locator("#stl").get_attribute("href") == kept["files"]["stl"]
        assert page.locator("#scad").get_attribute("href") == kept["files"]["scad"]
        assert page.locator("#originalStl").get_attribute("href") == f"/results/{run_id}/model.stl"
        params = client.get(f"/api/results/{run_id}/params",
                            params={"revision_id": kept["revision"]["id"]}).json()
        assert params["revision_id"] == kept["revision"]["id"]
        original_params = client.get(f"/api/results/{run_id}/params", params={"revision_id": "original"}).json()
        save("kept-params.json", {"kept": params, "original": original_params})
        capture("repair-kept")
        (OUT / "kept-model.scad").write_text(
            json.loads((out_dir / "revisions.json").read_text())["revisions"][kept["revision"]["id"]]["source_text"])

        # ---- second candidate + Discard restores the kept repair -------------
        page.click("#fixPart"); page.wait_for_selector("#repairDialog[open]")
        page.fill("#repairInstruction", "Make the hub slightly larger.")
        with page.expect_response(
                lambda r: r.request.method == "POST" and r.url.endswith("/revisions/repair"),
                timeout=900000) as resp:
            page.click("#repairGenerate")
        second = resp.value.json(); second_ok = resp.value.ok
        if second_ok:
            page.wait_for_function("(id)=>currentRun?.revision?.id===id", arg=second["revision"]["id"])
            save("second-candidate.json", {k: v for k, v in second.items() if k != "source_text"})
            capture("second-candidate")
            page.click("#discardRevision")
            page.wait_for_function("(id)=>currentRun?.revision?.id===id", arg=kept["revision"]["id"])
            assert page.locator("#stl").get_attribute("href") == kept["files"]["stl"]
            capture("discard-restored")
            discarded_still_there = kept["revision"]["id"] in json.dumps(
                json.loads((out_dir / "revisions.json").read_text())["revisions"])
        else:
            save("second-candidate-failure.json", {"status": resp.value.status, "detail": second.get("detail")})
            page.click(".close-repair")

        # ---- stale response cannot overwrite --------------------------------
        stale = client.post(f"/api/results/{run_id}/revisions/keep",
                            json={"revision_id": "original", "selection_version": 0})
        assert stale.status_code == 409, stale.text
        still_kept = client.get(f"/api/results/{run_id}").json()
        assert still_kept["revision"]["id"] == kept["revision"]["id"]

        after = measure(Path(kept["files"]["stl"].replace("/results/" + run_id, str(out_dir))))
        save("after-measurement.json", after)
        report.update(
            repair_succeeded=True, attempts=attempts,
            connected_after=after["components"] == 1, watertight_after=after["watertight"],
            extents_after=after["extents_mm"],
            preservation=preserved(before, after),
            keep_matches=True, discard_restores=bool(second_ok and discarded_still_there),
            stale_keep_rejected=True,
            params_follow_displayed=True,
            app_checks={c["name"]: c["status"] for c in kept["repair"]["checks"]},
            browser_errors=browser_errors)
        assert not browser_errors, browser_errors
        browser.close()

    shutil.copytree(out_dir, OUT / "artifacts" / run_id, dirs_exist_ok=True)
    save("report.json", report)
    print(json.dumps({k: report[k] for k in ("connected_after", "watertight_after", "extents_after",
          "preservation", "keep_matches", "discard_restores", "stale_keep_rejected",
          "params_follow_displayed", "app_checks")}, indent=2))
