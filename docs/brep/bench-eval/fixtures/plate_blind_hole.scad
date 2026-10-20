// fixture D3 (planted defect): the top-left through-hole made BLIND (4 mm
// of 5 mm depth — a 1 mm floor remains).
// declared detector: genus (3 -> 2: the tunnel closes)
// must remain stable: build_success, extents, volume (+113 mm3 = 0.4% < 2%)
$fn = 64;
difference() {
  cube([100, 60, 5]);
  translate([25, 45, 0]) cylinder(d = 6, h = 4);     // blind pocket
  translate([75, 15, -1]) cylinder(d = 6, h = 7);
  translate([50, 30, -1])
    linear_extrude(height = 7)
      hull() {
        translate([-(24 - 10) / 2, 0]) circle(d = 10);
        translate([(24 - 10) / 2, 0]) circle(d = 10);
      }
}
