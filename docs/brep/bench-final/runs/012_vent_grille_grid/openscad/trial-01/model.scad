/* doodle-meta {"version":1,"parameters":{"plate_width":{"label":"Overall width","description":"Changes the body width","unit":"mm","feature":"body_width"},"plate_height":{"label":"Overall height","description":"Changes the body height","unit":"mm","feature":"body_height"},"plate_thickness":{"label":"Plate thickness","description":"Changes the plate thickness","unit":"mm","feature":"body_thickness"},"hole_diameter":{"label":"Hole diameter","description":"Changes the diameter of the vent holes","unit":"mm","feature":"vent_holes"},"hole_spacing":{"label":"Hole spacing","description":"Changes the center-to-center spacing of the vent holes","unit":"mm","feature":"vent_holes"}},"features":{"body_width":{"kind":"dimension","axis":"x","label":"Overall width"},"body_height":{"kind":"dimension","axis":"z","label":"Overall height"},"body_thickness":{"kind":"dimension","axis":"y","label":"Plate thickness"},"vent_holes":{"kind":"region","label":"Vent hole grid","min":[{"parameter":"hole_spacing","scale":0.5,"offset":0},{"parameter":"plate_thickness","scale":-1,"offset":0},{"parameter":"hole_spacing","scale":0.5,"offset":0}],"max":[{"parameter":"hole_spacing","scale":2.5,"offset":0},{"parameter":"plate_thickness","scale":2,"offset":0},{"parameter":"hole_spacing","scale":2.5,"offset":0}]}}} */

// Top-level parameters (user-editable)
plate_width = 100;
plate_height = 61.4;
plate_thickness = 5;
hole_diameter = 15;
hole_spacing = 25;

// Derived constants (not user-editable)
eps = 0.01;
grid_cols = 3;
grid_rows = 3;

// Module for a single through-hole cutter
// Cuts along Y axis (front-to-back)
module hole_cutter(x, z) {
    translate([x, -eps, z])
        rotate([90, 0, 0])
            cylinder(h = plate_thickness + 2 * eps, d = hole_diameter, center = true);
}

// Main design
difference() {
    // Positive body: rectangular plate
    // Sits on build plate (Z=0 to Z=plate_height)
    // Extends in X (0 to plate_width) and Y (0 to plate_thickness)
    translate([0, 0, 0])
        cube([plate_width, plate_thickness, plate_height]);

    // Subtractive cutters: 3x3 grid of holes
    // Holes are centered in the grid pattern
    // Grid centers are at x = spacing, 2*spacing, 3*spacing
    // Grid centers are at z = spacing, 2*spacing, 3*spacing
    for (i = [0 : grid_cols - 1]) {
        for (j = [0 : grid_rows - 1]) {
            hole_x = (i + 1) * hole_spacing;
            hole_z = (j + 1) * hole_spacing;
            hole_cutter(hole_x, hole_z);
        }
    }
}
