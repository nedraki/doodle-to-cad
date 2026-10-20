# Probe #81 M3: level-2 replay — saved usd recipe bytes through the worker,
# plus a capability variant proving the op set can express the U-handle.
import json, os, shutil, subprocess, sys
from pathlib import Path

WT = Path("/tmp/doodle-brep-81")
WORKER = "/home/sparkie/playground/doodle-to-cad/workers/brep/.venv/bin/python"
SRC = WT / "docs/brep/bench-final/runs/constant_radius_handle/usd-brep/trial-02/model.recipe.json"
OUT = Path(os.environ.get("TMPDIR", "/tmp")) / "replay81"
OUT.mkdir(exist_ok=True)

def run_build(recipe_path, out_dir):
    out_dir.mkdir(exist_ok=True)
    for f in out_dir.glob("*"):
        f.unlink()
    r = subprocess.run([WORKER, str(WT / "workers/brep/build.py"),
                        str(recipe_path), str(out_dir)],
                       capture_output=True, text=True, timeout=300)
    err = out_dir / "construction-error.json"
    return r.returncode, (json.loads(err.read_text()) if err.exists() else None), r.stderr[-300:]

# 1) exact saved bytes
rc1, err1, log1 = run_build(SRC, OUT / "saved")
print("saved recipe:", "OK" if rc1 == 0 else err1)
if rc1 == 0:
    print("  diagnostics extents:", json.loads((OUT/"saved"/"diagnostics.json").read_text())["extents_mm"])

# 2) capability variant: arc_pipe -> rotate 90 about x through (0,0,30) -> legs axis z
base = json.loads(SRC.read_text())
ops = [
  {"id": "arc", "kind": "arc_pipe", "origin": [0, 0, 0], "bend_radius": "bend_radius",
   "radius": "diameter/2", "angle": 180, "frame": "world", "depends_on": [], "evidence": ["e1"]},
  {"id": "arc_up", "kind": "rotate", "body": "arc", "origin": [0, 0, "leg_length"],
   "axis": "x", "angle": 90, "frame": "world", "depends_on": ["arc"], "evidence": ["e1"]},
  {"id": "leg_left", "kind": "cylinder", "origin": ["-bend_radius", "leg_length", 0],
   "radius": "diameter/2", "height": "leg_length", "axis": "z",
   "frame": "world", "depends_on": [], "evidence": ["e1"]},
  {"id": "leg_right", "kind": "cylinder", "origin": ["bend_radius", "leg_length", 0],
   "radius": "diameter/2", "height": "leg_length", "axis": "z",
   "frame": "world", "depends_on": [], "evidence": ["e1"]},
  {"id": "u1", "kind": "union", "left": "arc_up", "right": "leg_left",
   "frame": "world", "depends_on": ["arc_up", "leg_left"], "evidence": ["e1"]},
  {"id": "final_part", "kind": "union", "left": "u1", "right": "leg_right",
   "frame": "world", "depends_on": ["u1", "leg_right"], "evidence": ["e1"]},
]
variant = dict(base, operations=ops, output="final_part")
vp = OUT / "variant.recipe.json"
vp.write_text(json.dumps(variant, indent=1))
rc2, err2, log2 = run_build(vp, OUT / "variant")
print("capability variant:", "OK" if rc2 == 0 else err2)
if rc2 == 0:
    d = json.loads((OUT/"variant"/"diagnostics.json").read_text())
    print("  extents:", d["extents_mm"], "solid_volume_mm3:", round(d["solid_volume_mm3"],1),
          "GT volume 6170.5 ->", f"{(d['solid_volume_mm3']-6170.5)/6170.5*100:+.1f}%")
