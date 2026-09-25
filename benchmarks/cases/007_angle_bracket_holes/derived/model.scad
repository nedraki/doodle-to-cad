
// Angle bracket: base 80x40x4 at z0..4, back wall 80x4x50 (y=36..40).
// Three d6 holes through the wall (axis Y) at x=20,40,60 z=30.
difference() {
  union() {
    cube([80,40,4]);
    translate([0,36,0]) cube([80,4,50]);
  }
  for (x=[20,40,60]) translate([x,35,30]) rotate([-90,0,0]) cylinder(d=6,h=10,$fn=32);
}
