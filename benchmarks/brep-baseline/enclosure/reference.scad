
// Enclosure: 120x80x40, wall 3, open top; 60x24 window through front wall (y=0..3).
difference() {
  difference() {
    cube([120,80,40]);
    translate([3,3,3]) cube([114,74,40]);   // open-top cavity
  }
  translate([30,-1,8]) cube([60,5,24]);     // front window
}
