
// Hex prism: across-flats 30 (R=17.32), length 70 along X, axis Y-rotated.
rotate([0,90,0])
  translate([0,0,-35])
    rotate([0,0,30])
      cylinder(h=70, r=17.32, $fn=6);
