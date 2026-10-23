$fn=96;
radius=3;
difference(){linear_extrude(20) offset(r=radius) translate([radius,radius]) square([60-2*radius,40-2*radius]); translate([30,20,-1]) cylinder(h=22,r=4);}
