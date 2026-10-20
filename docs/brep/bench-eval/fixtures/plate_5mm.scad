// fixture: known-correct baseline for the 004 plate family
// mirrors the GT reference: 100x60x5, two d6 holes + 24x10 center slot, genus 3
$fn = 64;
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
