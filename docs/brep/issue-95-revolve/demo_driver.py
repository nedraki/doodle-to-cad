"""Issue #95 live-demo driver: submit the certified vase drawing over HTTP.

Two product-faithful trials against the running evidence server:
  A certified      — notes verbatim from the frozen bench-final plan row.
  B hollow-specified — notes add open top + wall 4 mm + floor 4 mm, like a
                       user answering the vessel-thickness clarification.
Writes request.json / job.json per trial and prints a summary table.
"""
import hashlib
import json
import sys
import time
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[3]
BASE = "http://127.0.0.1:8135"
DRAWING = ROOT / "benchmarks/cases/002_greek_vase_silhouette/source/drawing.png"
OUT = Path(__file__).resolve().parent

TRIALS = [
    ("A-certified", "Greek vase from a single silhouette"),
    ("B-hollow-specified", "Greek vase from a single silhouette. Hollow vessel: open top, "
     "wall thickness 4 mm, floor thickness 4 mm."),
]


def run(label, notes):
    cell = OUT / label
    cell.mkdir(parents=True, exist_ok=True)
    image = DRAWING.read_bytes()
    (cell / "input.png").write_bytes(image)
    form = {"backend": "usd-brep", "notes": notes, "object_type": "", "method": "3D print",
            "primary_view": "front", "projection_standard": "third-angle",
            "strict_watertight": "true", "view_directions": "[]", "refine_mode": "regularize",
            "dimension": "120", "ask_missing_dimensions": "false"}
    (cell / "request.json").write_text(json.dumps(
        {"form": form, "image_sha256": hashlib.sha256(image).hexdigest(),
         "source": str(DRAWING.relative_to(ROOT)), "server": BASE}, indent=2))
    with httpx.Client(base_url=BASE, timeout=60) as client:
        response = client.post("/api/generate", files={"image": ("drawing.png", image, "image/png")}, data=form)
        response.raise_for_status()
        job = response.json()["job_id"]
        deadline = time.monotonic() + 1200
        status = {}
        while time.monotonic() < deadline:
            status = client.get(f"/api/generate/{job}").json()
            if status.get("status") in ("done", "error", "failed"):
                break
            time.sleep(10)
        (cell / "job.json").write_text(json.dumps(status, indent=2))
    result = status.get("result") or {}

    def walk(value):
        if isinstance(value, str):
            yield value
        elif isinstance(value, dict):
            for v in value.values():
                yield from walk(v)
    for url in walk(result.get("files") or {}):
        if url.startswith("/results/"):
            src = ROOT / "results" / url[len("/results/"):]
            if src.is_file():
                (cell / url.split("/")[-1]).write_bytes(src.read_bytes())
    evaluation = result.get("evaluation") or {}
    row = {"label": label, "job_id": job, "status": status.get("status"), "stage": status.get("stage"),
           "error": status.get("error") or result.get("error"),
           "accepted": evaluation.get("accepted"), "score": evaluation.get("score"),
           "files": result.get("files") or {}}
    print(json.dumps(row))
    return row


if __name__ == "__main__":
    wanted = set(sys.argv[1:]) or None
    rows = [run(*trial) for trial in TRIALS if not wanted or trial[0] in wanted]
    (OUT / "demo-rows.json").write_text(json.dumps(rows, indent=2))
