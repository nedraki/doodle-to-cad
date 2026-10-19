/* doodle-meta {"version":1,"parameters":{"width":{"label":"Overall width","description":"Changes the body width","unit":"mm","feature":"body_width"},"height":{"label":"Overall height","description":"Changes the body height","unit":"mm","feature":"body_height"},"thickness":{"label":"Plate thickness","description":"Changes the plate thickness","unit":"mm","feature":"body_thickness"},"hole_diameter":{"label":"Hole diameter","description":"Changes the diameter of the mounting holes","unit":"mm","feature":"holes"},"slot_width":{"label":"Slot width","description":"Changes the width of the central slot","unit":"mm","feature":"slot"},"slot_length":{"label":"Slot length","description":"Changes the length of the central slot","unit":"mm","feature":"slot"}},"features":{"body_width":{"kind":"dimension","axis":"x","label":"Overall width"},"body_height":{"kind":"dimension","axis":"z","label":"Overall height"},"body_thickness":{"kind":"dimension","axis":"y","label":"Plate thickness"},"holes":{"kind":"region","label":"Mounting holes","min":[{"parameter":"width","scale":0.1233},{"parameter":"thickness","scale":0,"offset":0},{"parameter":"height","scale":0.2105}],"max":[{"parameter":"width","scale":0.8733},{"parameter":"thickness","scale":1,"offset":0},{"parameter":"height","scale":0.8614}]},"slot":{"kind":"region","label":"Central slot","min":[{"parameter":"width","scale":0.3412},{"parameter":"thickness","scale":0,"offset":0},{"parameter":"height","scale":0.4209}],"max":[{"parameter":"width","scale":0.6402},{"parameter":"thickness","scale":1,"offset":0},{"parameter":"height","scale":0.5904}]}}} */

// Top-level parameters (user-editable)
width = 100.0;
height = 61.98;
thickness = 9.65;
hole_diameter = 10.0;
slot_width = 10.0;
slot_length = 30.0;

// Derived constants (not editable)
eps = 0.01;

// Module for the main plate body
module plate_body() {
    cube([width, thickness, height], center=true);
}

// Module for a circular hole cutter (axis along Y)
module hole_cutter(d) {
    rotate([90, 0, 0])
        cylinder(d=d, h=thickness + 2*eps, center=true);
}

// Module for a slot cutter (stadium shape, axis along Y)
module slot_cutter(w, l) {
    // Slot is elongated along X, width along Z
    // Create a stadium shape in XZ plane, extruded along Y
    hull() {
        translate([-l/2 + w/2, 0, 0])
            rotate([90, 0, 0])
                cylinder(d=w, h=thickness + 2*eps, center=true);
        translate([l/2 - w/2, 0, 0])
            rotate([90, 0, 0])
                cylinder(d=w, h=thickness + 2*eps, center=true);
    }
    // Fill the middle with a box
    translate([0, 0, 0])
        cube([l - w, thickness + 2*eps, w], center=true);
}

// Main design
difference() {
    plate_body();
    
    // Hole left: center at (0.1647*width, 0.2775*height) in front view
    // Front view: u -> X, v -> -Z (v=0 is top, v=1 is bottom)
    // So Z = (1 - v) * height
    // X = u * width
    // Center X = 0.1647 * width
    // Center Z = (1 - 0.2775) * height = 0.7225 * height
    translate([0.1647 * width - width/2, 0, (1 - 0.2775) * height - height/2])
        hole_cutter(hole_diameter);
    
    // Hole right: center at (0.8302*width, 0.7295*height) in front view
    // Center X = 0.8302 * width
    // Center Z = (1 - 0.7295) * height = 0.2705 * height
    translate([0.8302 * width - width/2, 0, (1 - 0.7295) * height - height/2])
        hole_cutter(hole_diameter);
    
    // Center slot: center at (0.4907*width, 0.5055*height) in front view
    // Center X = 0.4907 * width
    // Center Z = (1 - 0.5055) * height = 0.4945 * height
    translate([0.4907 * width - width/2, 0, (1 - 0.5055) * height - height/2])
        slot_cutter(slot_width, slot_length);
}
