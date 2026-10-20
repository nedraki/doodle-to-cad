$fn=96;
radius=25;
linear_extrude(8) union(){translate([0,0]) square([6,15.01]); translate([2*radius,0]) square([6,15.01]); intersection(){translate([radius+3,15]) difference(){circle(r=radius+3);circle(r=radius-3);} translate([-1,15]) square([2*radius+8,radius+4]);}}
