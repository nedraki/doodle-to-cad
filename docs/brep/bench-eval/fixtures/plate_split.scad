// fixture D5 (planted defect): a body DISCONNECTED from the plate
// (a 10x10x5 tab standing 1 mm clear of the right edge).
// declared detector: build_success (components == 1 requirement)
// must remain stable: nothing else is evaluated (multi-component rows carry
// genus/volume as non-verdict fields)
$fn = 64;
union() {
  difference() {
    cube([100, 60, 5]);
    translate([25, 45, -1]) cylinder(d = 6, h = 7);
    translate([75, 15, -1]) cylinder(d = 6, h = 7);
    translate([50, 30, -1])
      linear_extrude(height = 7)
        hull() {
          translate([-(24 - 10) / 2, 0]) circle(d = 10);
          translate([(24 - 10) / 2, 0]) circle(d = 10);
        }
  }
  translate([111, 25, 0]) cube([10, 10, 5]);          // 1 mm gap -> two bodies
}
