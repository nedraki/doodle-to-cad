/* doodle-meta {"version":1,"parameters":{"width":{"label":"Overall width","description":"Changes the body width","unit":"mm","feature":"body_width"},"depth":{"label":"Overall depth","description":"Changes the body depth","unit":"mm","feature":"body_depth"},"height":{"label":"Overall height","description":"Changes the body height","unit":"mm","feature":"body_height"},"wall_thickness":{"label":"Wall thickness","description":"Changes the thickness of the vertical walls","unit":"mm","feature":"wall_thickness"},"base_thickness":{"label":"Base thickness","description":"Changes the thickness of the base flange","unit":"mm","feature":"base_thickness"},"hole_diameter":{"label":"Mounting hole diameter","description":"Changes the diameter of the mounting holes","unit":"mm","feature":"mounting_holes"},"slot_width":{"label":"Slot width","description":"Changes the width of the central slot","unit":"mm","feature":"central_slot"},"slot_length":{"label":"Slot length","description":"Changes the length of the central slot","unit":"mm","feature":"central_slot"}},"features":{"body_width":{"kind":"dimension","axis":"x","label":"Overall width"},"body_depth":{"kind":"dimension","axis":"y","label":"Overall depth"},"body_height":{"kind":"dimension","axis":"z","label":"Overall height"},"wall_thickness":{"kind":"dimension","axis":"y","label":"Wall thickness"},"base_thickness":{"kind":"dimension","axis":"z","label":"Base thickness"},"mounting_holes":{"kind":"region","label":"Mounting holes","min":[{"parameter":"width","scale":0.15,"offset":0},{"parameter":"depth","scale":0.1,"offset":0},0],"max":[{"parameter":"width","scale":0.85,"offset":0},{"parameter":"depth","scale":0.9,"offset":0},{"parameter":"height","scale":1.0,"offset":0}]},"central_slot":{"kind":"region","label":"Central slot","min":[{"parameter":"width","scale":0.4,"offset":0},{"parameter":"depth","scale":0.4,"offset":0},0],"max":[{"parameter":"width","scale":0.6,"offset":0},{"parameter":"depth","scale":0.6,"offset":0},{"parameter":"height","scale":1.0,"offset":0}]}}} */

// Top-level size parameters (authoritative measured spans)
width = 43.22;
depth = 60.0;
height = 45.52;
wall_thickness = 4.0;
base_thickness = 4.0;
hole_diameter = 4.0;
slot_width = 8.0;
slot_length = 14.0;

// Derived (not user-editable)
eps = 0.5;
chamfer_size = 10.0;
hole_x_pos = width * 0.651;
hole_top_z = height * (1 - 0.155);
hole_bot_z = height * (1 - 0.846);
slot_x_pos = width * 0.251;
slot_z_pos = height * (1 - 0.493);

// U-channel cross-section in XY plane (two vertical walls + base)
module u_channel() {
    linear_extrude(height = height) {
        union() {
            // Base flange
            square([width, base_thickness]);
            // Front wall (near Y=0)
            square([width, wall_thickness]);
            // Back wall (near Y=depth)
            translate([0, depth - wall_thickness]) {
                square([width, wall_thickness]);
            }
        }
    }
}

// Chamfer cutter for top-right corner of the front wall (front-view silhouette)
module chamfer_cutter() {
    translate([width - chamfer_size, -eps, height - chamfer_size]) {
        cube([chamfer_size + eps, wall_thickness + 2 * eps, chamfer_size + eps]);
    }
}

// Circular mounting hole through the front wall (axis along Y)
module hole_cutter(zpos) {
    translate([hole_x_pos, -eps, zpos]) {
        rotate([90, 0, 0]) {
            cylinder(h = wall_thickness + 2 * eps, d = hole_diameter, center = true);
        }
    }
}

// Central rectangular slot through the front wall (axis along Y)
module slot_cutter() {
    translate([slot_x_pos, -eps, slot_z_pos]) {
        cube([slot_length, wall_thickness + 2 * eps, slot_width], center = true);
    }
}

// Main design
difference() {
    u_channel();
    chamfer_cutter();
    hole_cutter(hole_top_z);
    hole_cutter(hole_bot_z);
    slot_cutter();
}
