/* doodle-meta {"version":1,"parameters":{"width":{"label":"Overall width","description":"Changes the body width","unit":"mm","feature":"body_width"},"height":{"label":"Overall height","description":"Changes the body height","unit":"mm","feature":"body_height"},"thickness":{"label":"Plate thickness","description":"Changes the plate depth","unit":"mm","feature":"body_thickness"},"hole_diameter":{"label":"Mounting hole diameter","description":"Changes the diameter of the mounting holes","unit":"mm","feature":"holes"},"slot_length":{"label":"Slot length","description":"Changes the length of the central slot","unit":"mm","feature":"slot"},"slot_width":{"label":"Slot width","description":"Changes the width of the central slot","unit":"mm","feature":"slot"}},"features":{"body_width":{"kind":"dimension","axis":"x","label":"Overall width"},"body_height":{"kind":"dimension","axis":"z","label":"Overall height"},"body_thickness":{"kind":"dimension","axis":"y","label":"Plate thickness"},"holes":{"kind":"region","label":"Mounting Holes","min":[{"parameter":"width","scale":0.165,"offset":0},{"parameter":"thickness","scale":0,"offset":0},{"parameter":"height","scale":0.766,"offset":0}],"max":[{"parameter":"width","scale":0.83,"offset":0},{"parameter":"thickness","scale":1,"offset":0},{"parameter":"height","scale":0.274,"offset":0}]},"slot":{"kind":"region","label":"Central Slot","min":[{"parameter":"width","scale":0.35,"offset":0},{"parameter":"thickness","scale":0,"offset":0},{"parameter":"height","scale":0.419,"offset":0}],"max":[{"parameter":"width","scale":0.65,"offset":0},{"parameter":"thickness","scale":1,"offset":0},{"parameter":"height","scale":0.581,"offset":0}]}}} */

// Parameters
width = 100;
height = 62;
thickness = 10;
hole_diameter = 8;
slot_length = 30;
slot_width = 10;

// Derived constants (not editable)
eps = 0.1;

// Hole positions (from specification)
hole1_x = 16.5;
hole1_z = 47.5;
hole2_x = 83.0;
hole2_z = 17.0;

// Slot position (centered)
slot_x = width / 2;
slot_z = height / 2;

module plate_body() {
    cube([width, thickness, height], center=false);
}

module hole_cutter(d, x, z) {
    // Cylinder axis along Y (front-to-back)
    // rotate([90,0,0]) makes cylinder axis Y
    // center=true centers it along Y
    translate([x, thickness/2, z])
        rotate([90, 0, 0])
            cylinder(d=d, h=thickness + 2*eps, center=true);
}

module slot_cutter(l, w, x, z) {
    // Slot is horizontal (along X)
    // Stadium shape: two cylinders + connecting box
    // Cut along Y
    translate([x, thickness/2, z]) {
        // Left cylinder
        translate([-l/2 + w/2, 0, 0])
            rotate([90, 0, 0])
                cylinder(d=w, h=thickness + 2*eps, center=true);
        
        // Right cylinder
        translate([l/2 - w/2, 0, 0])
            rotate([90, 0, 0])
                cylinder(d=w, h=thickness + 2*eps, center=true);
        
        // Connecting box
        // Box spans from left cylinder center to right cylinder center in X
        // Width in X: l - w
        // Height in Z: w
        // Depth in Y: thickness + 2*eps
        translate([0, 0, 0])
            cube([l - w, thickness + 2*eps, w], center=true);
    }
}

// Main design
difference() {
    plate_body();
    
    // Cut mounting holes
    hole_cutter(hole_diameter, hole1_x, hole1_z);
    hole_cutter(hole_diameter, hole2_x, hole2_z);
    
    // Cut central slot
    slot_cutter(slot_length, slot_width, slot_x, slot_z);
}
