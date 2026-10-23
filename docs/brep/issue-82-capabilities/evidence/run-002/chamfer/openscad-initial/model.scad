$fn=96;
radius=3;
leg=radius/sqrt(2); hull(){translate([leg,leg,0]) cube([50-2*leg,40-2*leg,20]); translate([0,0,leg]) cube([50,40,20-2*leg]);}
