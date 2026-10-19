/* doodle-meta {"version":1,"parameters":{"width":{"label":"Overall width","description":"Changes the body width","unit":"mm","feature":"body_width"},"height":{"label":"Overall height","description":"Changes the body height","unit":"mm","feature":"body_height"},"depth":{"label":"Overall depth","description":"Changes the body depth","unit":"mm","feature":"body_depth"},"leg_thickness":{"label":"Leg thickness","description":"Changes the thickness of the L-shape legs","unit":"mm","feature":"leg_thickness"}},"features":{"body_width":{"kind":"dimension","axis":"x","label":"Overall width"},"body_height":{"kind":"dimension","axis":"z","label":"Overall height"},"body_depth":{"kind":"dimension","axis":"y","label":"Overall depth"},"leg_thickness":{"kind":"region","label":"Leg thickness","min":[0,0,0],"max":[{"parameter":"leg_thickness","scale":1,"offset":0},{"parameter":"depth","scale":1,"offset":0},{"parameter":"height","scale":1,"offset":0}]}}} */

// Parameters
width = 60.0;
height = 54.42;
depth = 13.6;
leg_thickness = 14.0;

// Derived dimensions
arm_length = width - leg_thickness;
arm_height = height - leg_thickness;

// Main body construction
// The L-shape is formed by the union of a vertical leg and a horizontal arm.
// Vertical leg: spans full height, located at X=0 to leg_thickness.
// Horizontal arm: spans remaining width, located at Z=0 to arm_height.

union() {
    // Vertical Leg (Mounting Face)
    // Extends from X=0 to leg_thickness, Y=0 to depth, Z=0 to height
    translate([0, 0, 0])
        cube([leg_thickness, depth, height]);
        
    // Horizontal Arm (Hook)
    // Extends from X=leg_thickness to width, Y=0 to depth, Z=0 to arm_height
    translate([leg_thickness, 0, 0])
        cube([arm_length, depth, arm_height]);
}
