// fixture D1 (planted defect): one opening MOVED 20 mm on x.
// declared detector: projection position fidelity (feature_position_fidelity)
// must remain stable: build_success, extents, genus, volume
$fn = 64;
difference() {
  cube([100, 60, 5]);
  translate([45, 45, -1]) cylinder(d = 6, h = 7);   // moved from x=25
  translate([75, 15, -1]) cylinder(d = 6, h = 7);
  translate([50, 30, -1])
    linear_extrude(height = 7)
      hull() {
        translate([-(24 - 10) / 2, 0]) circle(d = 10);
        translate([(24 - 10) / 2, 0]) circle(d = 10);
      }
}
