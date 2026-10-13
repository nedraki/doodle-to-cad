$fn=128;
// Wheel lies in XZ. Spokes overlap the hub and rim by 1 mm.
translate([60,8,60]) rotate([90,0,0]) union(){
difference(){cylinder(d=120,h=8);translate([0,0,-1])cylinder(d=108,h=10);}
cylinder(d=32,h=8);
for(a=[0:45:315])rotate([0,0,a])translate([15,-4,0])cube([40,8,8]);}
