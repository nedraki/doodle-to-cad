
// Mounting plate: width 100 (X), thickness 5 (Y), height 60 (Z).
// Two d6 through-holes (axis Y) at (15,45) and (85,15); 30x8 slot centered.
difference() {
  cube([100,5,60]);
  translate([15,-1,45])  rotate([-90,0,0]) cylinder(d=6,h=7,$fn=32);
  translate([85,-1,15])  rotate([-90,0,0]) cylinder(d=6,h=7,$fn=32);
  translate([35,-1,26])  cube([30,7,8]);
}
