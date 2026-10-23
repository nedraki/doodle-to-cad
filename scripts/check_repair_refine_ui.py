"""Issue #16: Refine instruction runs on the DISPLAYED candidate (browser).

Seeds the same controlled broken-wheel fixture, generates repair candidate 1,
then uses the Refine instruction button (visible only while a candidate is
displayed) to produce candidate 2 whose parent is candidate 1 — proving
refinement operates on the displayed candidate and the pre-repair version
stays recoverable. Keeps everything separate from check_repair_product.py so
a refine failure cannot hide the keep/discard evidence.

Test server must run on http://127.0.0.1:8116.
Writes docs/repair/issue-16/product-final/ (refine-* files only).
"""
import json, shutil, sys, uuid
from pathlib import Path
import httpx
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from doodle_to_cad import config  # noqa: F401
from doodle_to_cad.build_contract import BuildInput, build
from make_repair_fixture import SCAD

OUT = ROOT / "docs/repair/issue-16/product-final"
OUT.mkdir(parents=True, exist_ok=True)
BASE = "http://127.0.0.1:8116"
INSTRUCTION = ("Connect every spoke to the rim. Keep the outer diameter, hub, "
               "spoke count, and thickness unchanged.")
REFINE = ("Good start. Extend any spoke that still falls short of the rim so "
          "all spokes overlap the rim inner wall. Keep everything else "
          "unchanged.")

def save(name, data): (OUT / name).write_text(json.dumps(data, indent=2))

run_id = uuid.uuid4().hex[:12]
out_dir = ROOT / "results" / run_id
report = {"run_id": run_id, "flow": "candidate -> Refine instruction -> candidate(parent=candidate)"}
with httpx.Client(base_url=BASE, timeout=900) as client:
    out_dir.mkdir(parents=True)
    (out_dir / "model.scad").write_text(SCAD)
    shutil.copy(ROOT / "benchmarks/brep-baseline/wheel/drawing.png", out_dir / "input.png")
    built = build(BuildInput("openscad", out_dir / "model.scad", out_dir), "openscad")
    assert built.stl, built.log[-2000:]
    (out_dir / "result.json").write_text(json.dumps({
        "id": run_id, "backend": "openscad", "success": True,
        "spec": {"object": "eight-spoke wheel"}, "model": "fixture", "model_source": "seeded",
        "fixture": {"kind": "synthetic_broken_wheel", "generator": "scripts/make_repair_fixture.py"},
        "evaluation": {"accepted": True, "score": 88, "failures": []},
        "files": {"scad": f"/results/{run_id}/model.scad", "source": f"/results/{run_id}/model.scad",
                  "stl": f"/results/{run_id}/model.stl",
                  "views": {k: f"/results/{run_id}/{v.name}" for k, v in built.views.items()}}}, indent=2))
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True,
            executable_path="/home/sparkie/.cache/ms-playwright/chromium-1243/chrome-linux-arm64/chrome",
            args=["--no-sandbox", "--use-gl=angle", "--use-angle=swiftshader", "--enable-unsafe-swiftshader"])
        page = browser.new_page(viewport={"width": 1600, "height": 1300})
        errors = []
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.goto(BASE, wait_until="networkidle")
        page.evaluate("(r)=>render(r,null)", client.get(f"/api/results/{run_id}").json())
        page.wait_for_function("viewer?.mesh")

        def generate(button, instruction):
            page.click(button)
            page.wait_for_selector("#repairDialog[open]")
            page.fill("#repairInstruction", instruction)
            with page.expect_response(lambda r: r.request.method == "POST" and r.url.endswith("/revisions/repair"),
                                      timeout=900000) as resp:
                page.click("#repairGenerate")
            response = resp.value
            data = response.json()
            if response.ok:
                page.wait_for_function("(id)=>currentRun?.revision?.id===id", arg=data["revision"]["id"])
            else:
                page.click(".close-repair")
            return response.status, data

        status, first = generate("#fixPart", INSTRUCTION)
        report["first"] = {"status": status, "revision_id": (first.get("revision") or {}).get("id"),
                           "parent_id": (first.get("revision") or {}).get("parent_id"),
                           "detail": first.get("detail")}
        save("refine-first-candidate.json", first if status == 200 else {"status": status, "detail": first.get("detail")})
        if status != 200:
            save("refine-report.json", report); sys.exit(1)
        page.evaluate('viewer.setView("isometric")'); page.wait_for_timeout(600)
        page.locator("#result").screenshot(path=str(OUT / "refine-candidate-1.png"))
        assert page.is_visible("#refineRepair"), "Refine button must be offered on a repair candidate"
        assert not page.is_visible("#fixPart"), "Fix-this-part is hidden while a candidate is displayed"

        status, second = generate("#refineRepair", REFINE)
        report["refined"] = {"status": status, "revision_id": (second.get("revision") or {}).get("id"),
                             "parent_id": (second.get("revision") or {}).get("parent_id"),
                             "detail": second.get("detail")}
        save("refine-second-candidate.json", second if status == 200 else {"status": status, "detail": second.get("detail")})
        if status == 200:
            assert second["revision"]["parent_id"] == first["revision"]["id"], \
                "Refine must build on the DISPLAYED candidate"
            assert second["repair"]["started_from"] in ("parent-revision", "displayed-parameter-edit")
            page.evaluate('viewer.setView("isometric")'); page.wait_for_timeout(600)
            page.locator("#result").screenshot(path=str(OUT / "refine-candidate-2.png"))
            # Pre-repair version stays recoverable: discard returns to original.
            page.click("#discardRevision")
            page.wait_for_function("(id)=>currentRun?.revision?.id===id", arg="original")
            page.locator("#result").screenshot(path=str(OUT / "refine-after-discard.png"))
            store = json.loads((out_dir / "revisions.json").read_text())
            report["recoverable"] = {"selected": store["selected"],
                                     "candidate_1_still_in_history": first["revision"]["id"] in store["revisions"],
                                     "candidate_2_still_in_history": second["revision"]["id"] in store["revisions"]}
            assert store["selected"] == "original"
        report["browser_errors"] = errors
        assert not errors, errors
        browser.close()
    shutil.copytree(out_dir, OUT / "artifacts" / run_id, dirs_exist_ok=True)
    save("refine-report.json", report)
    print(json.dumps(report, indent=2))
