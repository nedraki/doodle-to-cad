
// Wall hook: L profile in XZ (60 toe, 55 back), 10 thick along Y, flat back on bed.
translate([0,10,0]) rotate([90,0,0])
  linear_extrude(height=10) {
    polygon([[0,0],[60,0],[60,12],[14,12],[14,55],[0,55]]);
  }
