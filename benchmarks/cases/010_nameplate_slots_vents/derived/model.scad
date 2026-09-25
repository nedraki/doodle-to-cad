
// Nameplate 140x3x24 (Y thickness 3). Two 12x6 slots near ends, five d5 vents.
difference() {
  cube([140,3,24]);
  translate([9,-1,9])  cube([12,5,6]);   // slot L (center x=15,z=12)
  translate([119,-1,9]) cube([12,5,6]);  // slot R (center x=125,z=12)
  for (x=[50,60,70,80,90]) translate([x,-1,12]) rotate([-90,0,0]) cylinder(d=5,h=5,$fn=24);
}
