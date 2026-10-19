#!/usr/bin/env python3
"""Probe mutations of the proven wheel_spokes fixture for the second usd_brep
1.0.0 kernel defect signature 'kernel produced an invalid solid' (observed in
frozen #34 rows wheel/usd-brep trial-04/05; recipes not retained)."""
import copy, json, shutil, subprocess, sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
WORKER = REPO / "workers/brep/.venv/bin/python"
BUILD = REPO / "workers/brep/build.py"
BASE = json.loads((REPO / "docs/brep/bench-features/fixtures/wheel_spokes.json").read_text())

out = REPO / ".scratch/invalid-solid-probe"
out.mkdir(parents=True, exist_ok=True)

def run(name, rec):
    p = out / f"{name}.recipe.json"
    p.write_text(json.dumps(rec))
    d = out / name
    shutil.rmtree(d, ignore_errors=True)
    d.mkdir(parents=True)
    r = subprocess.run([str(WORKER), str(BUILD), str(p), str(d)],
                       capture_output=True, text=True, timeout=180)
    err = d / "construction-error.json"
    code, msg = "ok", ""
    if err.is_file():
        e = json.loads(err.read_text()); code, msg = e["code"], e["message"][:70]
    print(f"{name:22s} rc={r.returncode} code={code} {msg}", flush=True)
    return code, msg

def op(id, kind, **kw):
    d = {"id": id, "kind": kind, "origin": [0, 0, 0]}
    d.update(kw)
    return d

def mut(fn):
    rec = copy.deepcopy(BASE)
    fn(rec)
    return rec

cases = {
    "base_control": copy.deepcopy(BASE),
    "thin_spokes": mut(lambda r: r["operations"].__setitem__(
        4, op("seed", "box", origin=[6, -0.2, 0], size=[22, 0.4, 4]))),
    "long_spokes": mut(lambda r: r["operations"].__setitem__(
        4, op("seed", "box", origin=[6, -2, 0], size=[26, 4, 4]))),
    "spokes_out_of_plane": mut(lambda r: [
        o.update(axis="y") for o in r["operations"] if o["kind"] == "rotate"]),
    "rim_cap_crosser": mut(lambda r: r["operations"].extend([
        op("cap_cyl", "cylinder", origin=[0, 24, 4], radius=6, height=12, axis="z"),
        {"id": "final2", "kind": "union", "left": "wheel", "right": "cap_cyl"},
     ] + [r.__setitem__("output", "final2")][0:0])),
    "hub_bore_cap": mut(lambda r: r["operations"].extend([
        op("bore", "cylinder", origin=[0, 0, 2], radius=4, height=6, axis="z"),
        {"id": "final2", "kind": "difference", "left": "wheel", "right": "bore"},
     ] + [r.__setitem__("output", "final2")][0:0])),
    "hub_tall_coplanar": mut(lambda r: [o.update(height=8) for o in r["operations"] if o["id"] == "hub"]),
    "spokes_tilted": mut(lambda r: (r["operations"].append(
        {"id": "tiltfinal", "kind": "rotate", "body": "wheel",
         "origin": [0, 0, 0], "axis": "x", "angle": 20}),
        r.__setitem__("output", "tiltfinal"))),
}
for name, rec in cases.items():
    try:
        run(name, rec)
    except subprocess.TimeoutExpired:
        print(f"{name:22s} TIMEOUT", flush=True)
