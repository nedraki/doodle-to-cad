// fixture D2 (planted defect): one opening REMOVED (top-left hole gone).
// declared detector: genus (3 -> 2)
// must remain stable: build_success, extents, volume (hole volume is 0.2%)
$fn = 64;
difference() {
  cube([100, 60, 5]);
  translate([75, 15, -1]) cylinder(d = 6, h = 7);
  translate([50, 30, -1])
    linear_extrude(height = 7)
      hull() {
        translate([-(24 - 10) / 2, 0]) circle(d = 10);
        translate([(24 - 10) / 2, 0]) circle(d = 10);
      }
}
