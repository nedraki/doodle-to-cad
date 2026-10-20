$fn=96;
selected_pocket_depth=3;
difference(){cube([60,40,20]); translate([8,8,20-selected_pocket_depth]) cube([12,12,selected_pocket_depth+1]); translate([40,8,18]) cube([12,12,3]); translate([8,24,15]) cube([12,12,6]);}
