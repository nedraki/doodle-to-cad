$fn=128;
// A convex-hull reference; this does not specify a unique loft surface.
hull(){translate([-30,-20,0])cube([60,40,0.01]);translate([0,0,59.99])cylinder(d=30,h=0.01);}
