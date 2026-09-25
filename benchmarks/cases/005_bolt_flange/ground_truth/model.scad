
// Flange: disc d120 axis Y centered y=-6..6, thickness 12.
difference() {
  translate([0,-6,0]) rotate([-90,0,0]) cylinder(d=120,h=12,$fn=96);
  translate([0,-7,0]) rotate([-90,0,0]) cylinder(d=40,h=14,$fn=64);
  for (a=[45:90:315])
    translate([45*cos(a),-7,45*sin(a)]) rotate([-90,0,0]) cylinder(d=10,h=14,$fn=32);
}
