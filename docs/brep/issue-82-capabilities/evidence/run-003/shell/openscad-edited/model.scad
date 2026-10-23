$fn=96;
thickness=4;
module rr(w,d,r){translate([r,r]) offset(r=r) square([w-2*r,d-2*r]);} difference(){linear_extrude(30) rr(80,60,8); translate([thickness,thickness,thickness]) linear_extrude(31) rr(80-2*thickness,60-2*thickness,8-thickness);}
