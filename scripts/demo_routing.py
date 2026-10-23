#!/usr/bin/env python3
"""Live routing demo for issue #60: two drawings through backend=auto on the
running app, asserting the rule each one triggers and saving routing evidence."""
import io, json, subprocess, sys, time
import httpx
from PIL import Image, ImageDraw

BASE = "http://127.0.0.1:8141"
import pathlib
OUT = pathlib.Path("/tmp/doodle-brep-60/docs/brep/issue-60-routing/data/live")

def sheet_single_view():
    img = Image.new("RGB", (400, 400), "white")
    d = ImageDraw.Draw(img)
    d.rectangle([120, 140, 280, 260], outline="black", width=4)  # one box outline
    return img

def sheet_multi_view():
    img = Image.new("RGB", (800, 400), "white")
    d = ImageDraw.Draw(img)
    d.rectangle([80, 120, 300, 280], outline="black", width=4)
    d.ellipse([150, 160, 230, 240], outline="black", width=4)
    d.rectangle([480, 120, 700, 280], outline="black", width=4)  # second view group
    for x in (540, 600, 660):
        d.ellipse([x-20, 170, x+20, 210], outline="black", width=4)
    return img

def post(name, img, notes, dimension):
    buf = io.BytesIO(); img.save(buf, "PNG")
    files = {"image": ("in.png", buf.getvalue(), "image/png")}
    data = {"notes": notes, "dimension": dimension, "backend": "auto",
            "object_type": "", "method": "3D print", "primary_view": "front",
            "projection_standard": "third-angle", "strict_watertight": "true",
            "view_directions": "[]", "refine_mode": "regularize"}
    r = httpx.post(f"{BASE}/api/generate", files=files, data=data, timeout=60)
    r.raise_for_status()
    job_id = r.json()["job_id"]
    while True:
        s = httpx.get(f"{BASE}/api/generate/{job_id}", timeout=60).json()
        if s.get("status") in {"done", "error", "cancelled"}:
            break
        time.sleep(5)
    res = s.get("result") or {}
    row = {"name": name, "job_id": job_id, "status": s.get("status"),
           "routing": s.get("routing") or res.get("routing"),
           "backend_in_result": res.get("backend"),
           "success": res.get("success"),
           "error": s.get("error")}
    print(json.dumps(row, indent=2), flush=True)
    (OUT / f"{name}.json").write_text(json.dumps(row, indent=2))
    return row

if __name__ == "__main__":
    import pathlib; pathlib.Path(OUT).mkdir(parents=True, exist_ok=True)
    a = post("single_view_box", sheet_single_view(), "", "80")
    b = post("multi_view_grid", sheet_multi_view(), "grille plate with holes", "120")
    ok = (a["routing"] or {}).get("rule") == "D" and (b["routing"] or {}).get("rule") in {"V", "C"}
    print("DEMO", "PASS" if ok else "FAIL")
    sys.exit(0 if ok else 1)
