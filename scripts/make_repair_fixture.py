"""Broken-wheel fixture for the issue #16 targeted-repair demonstration.

Derives from benchmarks/brep-baseline/wheel/reference.scad but pulls the
spokes back (spoke_reach 34 instead of 40) so every spoke stops 5 mm short
of the rim's inner wall: hub+spokes and rim become two separate watertight
bodies. This is a controlled synthetic fixture, not a user doodle.

Usage: make_repair_fixture.py OUT_DIR
Writes wheel-broken.scad, compiles wheel-broken.stl through the repo build
contract and prints the measured diagnostics.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from doodle_to_cad import config  # noqa: F401  (loads .env so DOODLE_OPENSCAD_DOCKER is set)
from doodle_to_cad.build_contract import BuildInput, build
from doodle_to_cad.openscad import mesh_health

SCAD = '''$fn=128;
/* doodle-meta {"version":1,"parameters":{"outer_diameter":{"label":"Outer diameter","description":"Outer rim diameter","unit":"mm"},"hub_diameter":{"label":"Hub","description":"Hub diameter","unit":"mm"},"spoke_width":{"label":"Spoke width","description":"Spoke bar thickness","unit":"mm"}}} */
// Wheel lies in XZ. BROKEN: spokes stop 5 mm short of the rim inner wall.
outer_diameter = 120; // mm
rim_inner_diameter = 108; // mm
hub_diameter = 32; // mm
thickness = 8; // mm
spoke_count = 8; // count
spoke_width = 8; // mm
spoke_reach = 34; // mm from hub overlap start; stops short of the rim
translate([outer_diameter/2,thickness/2,outer_diameter/2]) rotate([90,0,0]) union(){
  difference(){cylinder(d=outer_diameter,h=thickness);translate([0,0,-1])cylinder(d=rim_inner_diameter,h=thickness+2);}
  cylinder(d=hub_diameter,h=thickness);
  for(a=[0:360/spoke_count:360-360/spoke_count])rotate([0,0,a])translate([hub_diameter/2-1,-thickness/2,0])cube([spoke_reach,thickness,thickness]);
}
'''

def main():
    out = Path(sys.argv[1]); out.mkdir(parents=True, exist_ok=True)
    (out / "wheel-broken.scad").write_text(SCAD)
    result = build(BuildInput("openscad", out / "wheel-broken.scad", out, render=False), "openscad")
    assert result.stl, result.log[-2000:]
    health = mesh_health(result.stl)
    (out / "wheel-broken.measurement.json").write_text(json.dumps(health, indent=2))
    print(json.dumps(health, indent=2))
    assert health["components"] == 2, "fixture must be disconnected into exactly 2 components"
    assert health["watertight"] is True
    print("fixture OK")

if __name__ == "__main__":
    main()
