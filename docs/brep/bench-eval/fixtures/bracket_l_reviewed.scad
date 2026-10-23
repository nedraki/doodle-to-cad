// fixture: reviewed L-bracket for the 007 case (issue #81 EV-4).
// The notes say 'L angle bracket with three wall holes'; the ink shows two
// independent rectangles (one with 3 holes). This is the reviewed
// interpretation: base wall + upright wall with 3 through-holes, sized to
// the GT extents 80x40x50. Compared against the model's own archived
// plate scad through the SAME projection path the product used.
$fn = 64;
difference() {
  union() {
    cube([80, 40, 5]);                 // base wall
    translate([0, 0, 5]) cube([80, 5, 45]);   // upright wall (total z 50)
  }
  for (x = [20, 40, 60])
    translate([x, -1, 27.5]) rotate([-90, 0, 0]) cylinder(d = 8, h = 7);
}
