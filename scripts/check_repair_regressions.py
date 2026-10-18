"""Issue #16 fresh compatibility probes on the OpenSCAD backend.

Fixed cases (wheel, bookend, knob, cable holder) plus one random drawing
chosen from benchmarks/cases with a recorded seed. Never guess an answer to a
regression question: clarification requests are cancelled and retained.

Run with the test server on DOODLE_TEST_URL (default http://127.0.0.1:8116).
Writes docs/repair/issue-16/regressions/: selection.json (seed + cases),
per-case input/request/job/artifacts plus result.png and part.png.
"""
import json, os, random, shutil, time
from pathlib import Path
import httpx
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs/repair/issue-16/regressions"
OUT.mkdir(parents=True, exist_ok=True)
BASE = os.getenv("DOODLE_TEST_URL", "http://127.0.0.1:8116")
SEED = 20261018
fixed = [("wheel", "benchmarks/brep-baseline/wheel/drawing.png"),
         ("bookend", "benchmarks/cases/001_l_bookend_multiview/source/drawing.png"),
         ("knob", "benchmarks/cases/006_stepped_knob/source/drawing.png"),
         ("cable_holder", "benchmarks/cases/104_cable_holder/source/drawing.png")]
remaining = sorted(p for p in (ROOT / "benchmarks/cases").glob("*/source/drawing.png")
                   if str(p.relative_to(ROOT)) not in {s for _, s in fixed})
selected = random.Random(SEED).choice(remaining)
cases = fixed + [("random_" + selected.parent.parent.name, str(selected.relative_to(ROOT)))]
(OUT / "selection.json").write_text(json.dumps({"seed": SEED, "cases": cases}, indent=2))
summary_path = OUT / "summary.json"
summary = json.loads(summary_path.read_text()) if summary_path.exists() else {}
with httpx.Client(base_url=BASE, timeout=60) as client:
    for name, path in cases:
        if os.getenv("CASES") and name not in os.environ["CASES"].split(","):
            continue
        target = OUT / name
        target.mkdir(exist_ok=True)
        shutil.copy(ROOT / path, target / "input.png")
        form = {"backend": "openscad", "notes": "", "object_type": "", "dimension": "120",
                "primary_view": "front", "projection_standard": "third-angle",
                "refine_mode": "regularize", "method": "3D print", "strict_watertight": "on"}
        if (target / "request.json").exists():
            job = json.loads((target / "request.json").read_text())["job"]
        else:
            r = client.post("/api/generate", files={"image": ("drawing.png", (ROOT / path).read_bytes(), "image/png")}, data=form)
            r.raise_for_status(); job = r.json()["job_id"]
            (target / "request.json").write_text(json.dumps({"source": path, "form": form, "job": job}, indent=2))
        print(name, job, flush=True)
        question = None
        for _ in range(900):
            state = client.get("/api/generate/" + job).json()
            if state["status"] == "waiting_for_answer":
                question = state["question"]
                client.post("/api/generate/" + job + "/cancel")
                state = client.get("/api/generate/" + job).json(); break
            if state["status"] in {"done", "error", "cancelled"}:
                break
            time.sleep(2)
        else:
            client.post("/api/generate/" + job + "/cancel")
            raise TimeoutError(job)
        (target / "job.json").write_text(json.dumps(state, indent=2))
        if question:
            (target / "question.json").write_text(json.dumps(question, indent=2))
        local = ROOT / "results" / job
        if local.exists():
            shutil.copytree(local, target / "artifacts" / job, dirs_exist_ok=True)
        summary[name] = {"job": job, "status": state["status"],
                         "question_requested": question is not None,
                         "error": state.get("error"),
                         "evaluation": (state.get("result") or {}).get("evaluation")}
        summary_path.write_text(json.dumps(summary, indent=2))
        print(summary[name], flush=True)

# Screenshots for every completed case.
with sync_playwright() as p:
    browser = p.chromium.launch(headless=True,
        executable_path="/home/sparkie/.cache/ms-playwright/chromium-1243/chrome-linux-arm64/chrome",
        args=["--no-sandbox", "--use-gl=angle", "--use-angle=swiftshader", "--enable-unsafe-swiftshader"])
    page = browser.new_page(viewport={"width": 1600, "height": 1300})
    for name, case in summary.items():
        if case["status"] != "done":
            continue
        r = httpx.get(BASE + "/api/results/" + case["job"]).json()
        page.goto(BASE)
        page.evaluate("(r)=>render(r,null)", r)
        page.wait_for_function("viewer?.mesh"); page.wait_for_timeout(1000)
        page.evaluate('viewer.setView("isometric")'); page.wait_for_timeout(600)
        page.locator("#result").screenshot(path=str(OUT / name / "result.png"))
        page.locator("#viewerWrap").screenshot(path=str(OUT / name / "part.png"))
    browser.close()
print("regressions done")
