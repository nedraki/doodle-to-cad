$fn=128;
translate([0,0,4]) union(){rotate_extrude(angle=180)translate([20,0])circle(r=4);
for(x=[-20,20])translate([x,0,0])rotate([90,0,0])cylinder(r=4,h=30);}
