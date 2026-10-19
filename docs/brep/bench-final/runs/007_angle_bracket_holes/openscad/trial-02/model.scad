/* doodle-meta {"version":1,"parameters":{"width":{"label":"Overall width","description":"Changes the body width","unit":"mm","feature":"body_width"},"depth":{"label":"Overall depth","description":"Changes the body depth","unit":"mm","feature":"body_depth"},"height":{"label":"Overall height","description":"Changes the body height","unit":"mm","feature":"body_height"},"wall_thickness":{"label":"Wall thickness","description":"Thickness of the L-bracket walls","unit":"mm","feature":"wall_thickness"},"hole_diameter":{"label":"Hole diameter","description":"Diameter of the three mounting holes","unit":"mm","feature":"holes"},"hole_spacing":{"label":"Hole spacing","description":"Center-to-center distance between holes","unit":"mm","feature":"holes"}},"features":{"body_width":{"kind":"dimension","axis":"x","label":"Overall width"},"body_depth":{"kind":"dimension","axis":"y","label":"Overall depth"},"body_height":{"kind":"dimension","axis":"z","label":"Overall height"},"wall_thickness":{"kind":"region","label":"Wall thickness","min":[0,0,0],"max":[{"parameter":"wall_thickness","scale":1,"offset":0},{"parameter":"depth","scale":1,"offset":0},{"parameter":"height","scale":1,"offset":0}]},"holes":{"kind":"region","label":"Mounting holes","min":[{"parameter":"width","scale":0.1,"offset":0},{"parameter":"depth","scale":0.5,"offset":0},{"parameter":"height","scale":0.3,"offset":0}],"max":[{"parameter":"width","scale":0.9,"offset":0},{"parameter":"depth","scale":0.5,"offset":0},{"parameter":"height","scale":0.7,"offset":0}]}}} */

// Top-level editable parameters
width = 80.0;
depth = 43.13;
height = 51.01;
wall_thickness = 6.0;
hole_diameter = 8.0;
hole_spacing = 25.0;

// Derived constants (not editable)
eps = 0.1;
hole_count = 3;
hole_z = height * 0.5842; // Derived from front view v=0.4158 -> Z = (1-0.4158)*height

module l_bracket_body() {
    // Vertical wall (back part of the L)
    // Occupies Y from (depth - wall_thickness) to depth
    // Occupies X from 0 to width
    // Occupies Z from 0 to height
    translate([0, depth - wall_thickness, 0])
        cube([width, wall_thickness, height]);

    // Horizontal base (bottom part of the L)
    // Occupies Y from 0 to depth
    // Occupies X from 0 to width
    // Occupies Z from 0 to wall_thickness
    translate([0, 0, 0])
        cube([width, depth, wall_thickness]);
}

module hole_cutter(x_pos) {
    // Cuts through the vertical wall along Y axis
    // The wall is at Y = [depth - wall_thickness, depth]
    // Cutter spans Y from (depth - wall_thickness - eps) to (depth + eps)
    // Centered at Y = depth - wall_thickness/2
    // Rotated 90 deg around X to align cylinder axis with Y
    translate([x_pos, depth - wall_thickness / 2, hole_z])
        rotate([90, 0, 0])
            cylinder(h = wall_thickness + 2 * eps, d = hole_diameter, center = true);
}

module bracket_with_holes() {
    difference() {
        l_bracket_body();
        
        // Generate 3 holes
        // Center hole at width/2
        // Left hole at width/2 - hole_spacing
        // Right hole at width/2 + hole_spacing
        for (i = [-1, 0, 1]) {
            hole_cutter(width / 2 + i * hole_spacing);
        }
    }
}

// Instantiate the design
bracket_with_holes();
