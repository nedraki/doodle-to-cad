"""Deterministic backend comparison; no model required.

DOODLE_BREP_PYTHON=/path/to/worker/python .venv/bin/python scripts/evaluate_brep.py
"""
import json
from pathlib import Path
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from doodle_to_cad.brep import build_recipe
from doodle_to_cad.config import ROOT, settings
from doodle_to_cad.openscad import compile_stl_only, mesh_health

REFERENCES = {
    "bracket": '''difference(){union(){cube([60,40,5]);cube([60,5,80]);}
for(x=[10,35])for(z=[20,50])translate([x,-1,z])cube([10,7,15]);}''',
    "enclosure": '''$fn=96;difference(){hull(){for(x=[2,58])for(y=[2,38])
translate([x,y,0])cylinder(r=2,h=25);}translate([3,3,3])cube([54,34,25]);}''',
    "curved_pipe": '''$fn=128;translate([0,0,3])rotate_extrude(angle=90)
translate([20,0])circle(r=3);''',
}
EDITS = {"bracket": {"hole1_width": 12, "hole1_x": 12},
         "enclosure": {"wall": 4, "fillet": 3},
         "curved_pipe": {"bend_radius": 25, "tube_radius": 4}}


def main():
    rows = []
    output = ROOT / "results" / "brep-evaluation"
    output.mkdir(parents=True, exist_ok=True)
    for name, scad in REFERENCES.items():
        recipe = json.loads((ROOT / "benchmarks" / "brep" / f"{name}.json").read_text())
        out = output / name
        out.mkdir(exist_ok=True)
        start = time.monotonic()
        built = build_recipe(out, recipe)
        baseline_elapsed = time.monotonic()-start
        start = time.monotonic()
        edited = build_recipe(out, recipe, EDITS[name])
        edit_elapsed = time.monotonic()-start
        start = time.monotonic()
        url, error = compile_stl_only(out, scad, 'reference', settings.openscad_bin)
        scad_elapsed = time.monotonic()-start
        row = {"case": name, "brep": built['diagnostics'], "edit": edited['diagnostics'],
               "updates": EDITS[name], "brep_wall_seconds": round(baseline_elapsed,3),
               "edit_wall_seconds": round(edit_elapsed,3), "openscad_wall_seconds": round(scad_elapsed,3),
               "openscad": mesh_health(out / 'reference.stl') if url else {"error": error}}
        rows.append(row)
        print(name, row['brep_wall_seconds'], row['edit_wall_seconds'], row['openscad'])
    (ROOT / "docs" / "brep" / "evaluation.json").write_text(json.dumps(rows,indent=2)+'\n')


if __name__ == '__main__':
    main()
