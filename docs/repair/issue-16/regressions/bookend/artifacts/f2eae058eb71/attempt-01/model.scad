/* doodle-meta {"version":1,"parameters":{"width":{"label":"Overall width","description":"Changes the body width","unit":"mm","feature":"body_width"},"depth":{"label":"Overall depth","description":"Changes the body depth","unit":"mm","feature":"body_depth"},"height":{"label":"Overall height","description":"Changes the body height","unit":"mm","feature":"body_height"},"leg_thickness":{"label":"Leg thickness","description":"Thickness of the L-profile legs","unit":"mm","feature":"leg_thickness"},"cutout1_w":{"label":"Cutout 1 width","description":"Width of the upper-left cutout","unit":"mm","feature":"cutout_1"},"cutout1_h":{"label":"Cutout 1 height","description":"Height of the upper-left cutout","unit":"mm","feature":"cutout_1"},"cutout2_w":{"label":"Cutout 2 width","description":"Width of the lower-left slot","unit":"mm","feature":"cutout_2"},"cutout2_h":{"label":"Cutout 2 height","description":"Height of the lower-left slot","unit":"mm","feature":"cutout_2"},"cutout3_w":{"label":"Cutout 3 width","description":"Width of the center slot","unit":"mm","feature":"cutout_3"},"cutout3_h":{"label":"Cutout 3 height","description":"Height of the center slot","unit":"mm","feature":"cutout_3"},"cutout4_w":{"label":"Cutout 4 width","description":"Width of the lower-right slot","unit":"mm","feature":"cutout_4"},"cutout4_h":{"label":"Cutout 4 height","description":"Height of the lower-right slot","unit":"mm","feature":"cutout_4"}},"features":{"body_width":{"kind":"dimension","axis":"x","label":"Overall width"},"body_depth":{"kind":"dimension","axis":"y","label":"Overall depth"},"body_height":{"kind":"dimension","axis":"z","label":"Overall height"},"leg_thickness":{"kind":"dimension","axis":"z","label":"Leg thickness"},"cutout_1":{"kind":"region","label":"Upper-left cutout","min":[{"parameter":"cutout1_x","scale":1,"offset":0},{"parameter":"cutout1_y","scale":1,"offset":0},{"parameter":"cutout1_z","scale":1,"offset":0}],"max":[{"parameter":"cutout1_x","scale":1,"offset":0},{"parameter":"cutout1_y","scale":1,"offset":0},{"parameter":"cutout1_z","scale":1,"offset":0}]},"cutout_2":{"kind":"region","label":"Lower-left slot","min":[{"parameter":"cutout2_x","scale":1,"offset":0},{"parameter":"cutout2_y","scale":1,"offset":0},{"parameter":"cutout2_z","scale":1,"offset":0}],"max":[{"parameter":"cutout2_x","scale":1,"offset":0},{"parameter":"cutout2_y","scale":1,"offset":0},{"parameter":"cutout2_z","scale":1,"offset":0}]},"cutout_3":{"kind":"region","label":"Center slot","min":[{"parameter":"cutout3_x","scale":1,"offset":0},{"parameter":"cutout3_y","scale":1,"offset":0},{"parameter":"cutout3_z","scale":1,"offset":0}],"max":[{"parameter":"cutout3_x","scale":1,"offset":0},{"parameter":"cutout3_y","scale":1,"offset":0},{"parameter":"cutout3_z","scale":1,"offset":0}]},"cutout_4":{"kind":"region","label":"Lower-right slot","min":[{"parameter":"cutout4_x","scale":1,"offset":0},{"parameter":"cutout4_y","scale":1,"offset":0},{"parameter":"cutout4_z","scale":1,"offset":0}],"max":[{"parameter":"cutout4_x","scale":1,"offset":0},{"parameter":"cutout4_y","scale":1,"offset":0},{"parameter":"cutout4_z","scale":1,"offset":0}]}}} */

// Top-level editable parameters
width = 96.22;
depth = 86.0;
height = 120.0;
leg_thickness = 12.0;

// Cutout 1 (upper-left)
cutout1_w = 28.75;
cutout1_h = 23.62;
cutout1_x = 26.21;
cutout1_z = 96.38;

// Cutout 2 (lower-left)
cutout2_w = 16.66;
cutout2_h = 48.32;
cutout2_x = 31.44;
cutout2_z = 47.0;

// Cutout 3 (center)
cutout3_w = 11.28;
cutout3_h = 37.62;
cutout3_x = 51.58;
cutout3_z = 68.78;

// Cutout 4 (lower-right)
cutout4_w = 13.17;
cutout4_h = 46.69;
cutout4_x = 71.88;
cutout4_z = 46.96;

// Derived sizes (not editable)
eps = 0.01;
vertical_leg_h = height - leg_thickness;

// Modules
module l_bracket_body() {
    // Vertical leg (back)
    translate([0, depth - leg_thickness, 0])
        cube([width, leg_thickness, height]);
    // Horizontal leg (bottom)
    translate([0, 0, 0])
        cube([width, depth, leg_thickness]);
}

module cutout_cutter(w, h, x, z) {
    // Through-cut along Y (front view openings)
    translate([x - w/2, -eps, z - h/2])
        cube([w, depth + 2*eps, h]);
}

// Main design
difference() {
    l_bracket_body();
    
    // Cutout 1: upper-left
    cutout_cutter(cutout1_w, cutout1_h, cutout1_x, cutout1_z);
    
    // Cutout 2: lower-left
    cutout_cutter(cutout2_w, cutout2_h, cutout2_x, cutout2_z);
    
    // Cutout 3: center
    cutout_cutter(cutout3_w, cutout3_h, cutout3_x, cutout3_z);
    
    // Cutout 4: lower-right
    cutout_cutter(cutout4_w, cutout4_h, cutout4_x, cutout4_z);
}
