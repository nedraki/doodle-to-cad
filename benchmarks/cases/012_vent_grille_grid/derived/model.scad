
// Vent grille: 100x4x60 plate (Y thin), nine d10 holes on 25/15 grid.
difference() {
  cube([100,4,60]);
  for (x=[25,50,75], z=[15,30,45])
    translate([x,-1,z]) rotate([-90,0,0]) cylinder(d=10,h=6,$fn=32);
}
