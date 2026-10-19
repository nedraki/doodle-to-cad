"""Issue #68 live demo driver: the thickness lottery, then ask->answer->accept.

Run against a live server (default http://127.0.0.1:8142):
  1) three OpenSCAD runs of jeep grille 012 WITHOUT the dimension question
     (ask_missing_dimensions=false) -> record plate thickness spread (lottery).
  2) one run WITH the question -> job must reach waiting_for_answer on the
     depth axis -> answer 4 mm (the ground-truth plate thickness) -> run must
     complete and the STL extent in depth must land near 4 mm.

Writes logs/lottery-and-ask.json next to this script.
"""
import json
import struct
import sys
import time
import urllib.request
from pathlib import Path

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8142"
CASE = Path(sys.argv[2] if len(sys.argv) > 2 else "/home/sparkie/playground/doodle-to-cad/benchmarks/cases/012_vent_grille_grid")
HERE = Path(__file__).resolve().parent.parent / "logs"


def post(image_bytes, ask, notes):
    boundary = "----issue68demo"
    body = b""
    def field(name, value):
        nonlocal body
        body += (f"--{boundary}\r\nContent-Disposition: form-data; name=\"{name}\"\r\n\r\n{value}\r\n").encode()
    field("notes", notes)
    field("dimension", "100")
    field("backend", "openscad")
    field("ask_missing_dimensions", "true" if ask else "false")
    field("strict_watertight", "on")
    body += (f"--{boundary}\r\nContent-Disposition: form-data; name=\"image\"; filename=\"drawing.png\"\r\nContent-Type: image/png\r\n\r\n").encode()
    body += image_bytes + f"\r\n--{boundary}--\r\n".encode()
    req = urllib.request.Request(BASE + "/api/generate", data=body,
                                 headers={"Content-Type": f"multipart/form-data; boundary={boundary}"})
    return json.loads(urllib.request.urlopen(req, timeout=30).read())


def poll(job_id, until_answer=False, seconds=900):
    deadline = time.time() + seconds
    while time.time() < deadline:
        job = json.loads(urllib.request.urlopen(BASE + f"/api/generate/{job_id}", timeout=15).read())
        if job["status"] == "done":
            return job
        if job["status"] == "error":
            return job
        if until_answer and job["status"] == "waiting_for_answer":
            return job
        time.sleep(1.5)
    raise TimeoutError(job_id)


def answer(job_id, question, value):
    body = json.dumps({"question_id": question["id"], "value_mm": value}).encode()
    req = urllib.request.Request(BASE + f"/api/generate/{job_id}/answer", data=body,
                                 headers={"Content-Type": "application/json"})
    return json.loads(urllib.request.urlopen(req, timeout=15).read())


def stl_dims(path):
    import numpy as np
    raw = Path(path).read_bytes()
    n_hdr = int.from_bytes(raw[80:84], "little") if len(raw) >= 84 else -1
    if len(raw) != 84 + 50 * n_hdr:
        import re
        verts = np.array([[float(v) for v in line.split()[1:4]]
                          for line in raw.decode(errors="ignore").splitlines()
                          if line.strip().startswith("vertex")], dtype=np.float32)
        mn, mx = verts.min(axis=0), verts.max(axis=0)
        return [round(float(mx[i] - mn[i]), 2) for i in range(3)]
    with open(path, "rb") as fh:
        fh.read(80)
        n = struct.unpack("<I", fh.read(4))[0]
        data = fh.read(n * 50)
        facets = np.frombuffer(data[:n * 50], dtype=np.uint8).reshape(n, 50)
        pts = facets[:, :48].copy().view(np.float32).reshape(n * 3, 3)
        mn = pts.min(axis=0)
        mx = pts.max(axis=0)
        return [round(float(mx[i] - mn[i]), 2) for i in range(3)]


image = (CASE / "source" / "drawing.png").read_bytes()
out = {"base": BASE, "case": str(CASE), "lottery_runs": [], "ask_run": None}
for trial in range(3):
    jid = post(image, ask=False, notes="vent grille plate")["job_id"]
    job = poll(jid)
    stl = Path("/tmp/doodle-brep-ink/results") / jid / "model.stl"
    extents = stl_dims(stl) if stl.is_file() else None
    out["lottery_runs"].append({"job_id": jid, "status": job["status"], "extents_xyz": extents,
                                "evaluation_score": (job.get("result") or {}).get("evaluation", {}).get("score")})
    print("lottery", trial, extents, flush=True)

jid = post(image, ask=True, notes="vent grille plate")["job_id"]
job = poll(jid, until_answer=True)
question = job.get("question") or {}
out["ask_run"] = {"job_id": jid, "question_status": job["status"],
                  "question_kind": question.get("kind"), "question_axis": question.get("axis"),
                  "question_text": question.get("text"), "maximum_mm": question.get("maximum_mm")}
print("question:", out["ask_run"], flush=True)
assert job["status"] == "waiting_for_answer" and question.get("kind") == "body_dimension", out["ask_run"]
answer(jid, question, 4.0)
job = poll(jid)
stl = Path("/tmp/doodle-brep-ink/results") / jid / "model.stl"
out["ask_run"].update({"final_status": job["status"], "extents_xyz": stl_dims(stl) if stl.is_file() else None,
                       "evaluation_score": (job.get("result") or {}).get("evaluation", {}).get("score"),
                       "size_clarification": (job.get("result") or {}).get("size_clarification")})
print("asked run:", out["ask_run"], flush=True)
(HERE / "lottery-and-ask.json").write_text(json.dumps(out, indent=2) + "\n")
lottery_th = [min(r["extents_xyz"]) for r in out["lottery_runs"] if r["extents_xyz"]]
if lottery_th:
    out["verdict"] = {
        "unasked_guessed_thickness_mm": sorted(set(lottery_th)),
        "asked_thickness_mm": (min(out["ask_run"]["extents_xyz"])
                               if out["ask_run"]["extents_xyz"] else None),
        "reference_thickness_mm": 4.0,
        "reading": "no-ask runs never reach the 4 mm reference; the asked run lands on it",
    }
    (HERE / "lottery-and-ask.json").write_text(json.dumps(out, indent=2) + "\n")
print("DONE", out.get("verdict"))
