/* doodle-meta {"version":1,"parameters":{"width":{"label":"Overall width","description":"Changes the body width","unit":"mm","feature":"body_width"},"height":{"label":"Overall height","description":"Changes the body height","unit":"mm","feature":"body_height"},"depth":{"label":"Overall depth","description":"Changes the body depth","unit":"mm","feature":"body_depth"},"wall_thickness":{"label":"Wall thickness","description":"Thickness of the L-profile legs","unit":"mm","feature":"wall_thickness"},"top_cutout_width":{"label":"Top cutout width","description":"Width of the wide rectangular cutout","unit":"mm","feature":"top_cutout"},"top_cutout_height":{"label":"Top cutout height","description":"Height of the wide rectangular cutout","unit":"mm","feature":"top_cutout"},"slot_width":{"label":"Slot width","description":"Width of the vertical slots","unit":"mm","feature":"slots"},"slot_height":{"label":"Slot height","description":"Height of the vertical slots","unit":"mm","feature":"slots"}},"features":{"body_width":{"kind":"dimension","axis":"x","label":"Overall width"},"body_height":{"kind":"dimension","axis":"z","label":"Overall height"},"body_depth":{"kind":"dimension","axis":"y","label":"Overall depth"},"wall_thickness":{"kind":"region","label":"Wall thickness","min":[0,0,0],"max":[{"parameter":"wall_thickness","scale":1,"offset":0},{"parameter":"depth","scale":1,"offset":0},{"parameter":"height","scale":1,"offset":0}]},"top_cutout":{"kind":"region","label":"Top cutout","min":[{"parameter":"width","scale":0.123,"offset":0},{"parameter":"depth","scale":0,"offset":0},{"parameter":"height","scale":0.8032,"offset":0}],"max":[{"parameter":"width","scale":0.4218,"offset":0},{"parameter":"depth","scale":1,"offset":0},{"parameter":"height","scale":0.9017,"offset":0}]},"slots":{"kind":"region","label":"Vertical slots","min":[{"parameter":"width","scale":0.2403,"offset":0},{"parameter":"depth","scale":0,"offset":0},{"parameter":"height","scale":0.2014,"offset":0}],"max":[{"parameter":"width","scale":0.8157,"offset":0},{"parameter":"depth","scale":1,"offset":0},{"parameter":"height","scale":0.8041,"offset":0}]}}} */

// Top-level parameters (user-editable)
width = 80.18;
height = 100.0;
depth = 71.67;
wall_thickness = 12.0;

// Derived sizes (not user-editable)
base_thickness = wall_thickness;
vertical_leg_thickness = wall_thickness;

// Cutout parameters
top_cutout_width = 24.0;
top_cutout_height = 10.0;
top_cutout_center_x = 21.8;
top_cutout_center_z = 85.0;

slot_width = 14.0;
slot_height = 40.0;
slot_center_x_left = 26.2;
slot_center_x_center = 43.0;
slot_center_x_right = 60.0;
slot_center_z = 40.0;

// Implementation constants
eps = 0.01;

module l_profile() {
    // L-shaped profile in YZ plane
    // Vertical leg: Y from 0 to vertical_leg_thickness, Z from 0 to height
    // Horizontal base: Y from 0 to depth, Z from 0 to base_thickness
    union() {
        // Vertical leg
        translate([0, 0, 0])
            cube([vertical_leg_thickness, depth, height]);
        // Horizontal base
        translate([0, 0, 0])
            cube([depth, base_thickness, height]);
    }
}

module bookend_body() {
    // Extrude L-profile along X-axis
    linear_extrude(height=width)
        l_profile();
}

module top_cutout_cutter() {
    // Wide rectangular cutout in upper section of front face
    // Cuts through the vertical leg (along Y)
    translate([top_cutout_center_x - top_cutout_width/2, -eps, top_cutout_center_z - top_cutout_height/2])
        cube([top_cutout_width, vertical_leg_thickness + 2*eps, top_cutout_height]);
}

module slot_cutter(cx) {
    // Vertical rectangular slot
    // Cuts through the vertical leg (along Y)
    translate([cx - slot_width/2, -eps, slot_center_z - slot_height/2])
        cube([slot_width, vertical_leg_thickness + 2*eps, slot_height]);
}

// Main design
difference() {
    bookend_body();
    
    // Subtract cutouts
    top_cutout_cutter();
    slot_cutter(slot_center_x_left);
    slot_cutter(slot_center_x_center);
    slot_cutter(slot_center_x_right);
}
