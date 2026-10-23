/* doodle-meta {"version":1,"parameters":{"width":{"label":"Overall width","description":"Changes the body width","unit":"mm","feature":"body_width"},"depth":{"label":"Overall depth","description":"Changes the body depth","unit":"mm","feature":"body_depth"},"height":{"label":"Overall height","description":"Changes the body height","unit":"mm","feature":"body_height"},"thickness":{"label":"Plate thickness","description":"Changes the thickness of the plate","unit":"mm","feature":"body_thickness"},"hole_diameter":{"label":"Central hole diameter","description":"Changes the diameter of the central hole","unit":"mm","feature":"central_hole"},"slot_width":{"label":"Slot width","description":"Changes the width of the mounting slots","unit":"mm","feature":"slot_row"},"slot_height":{"label":"Slot height","description":"Changes the height of the mounting slots","unit":"mm","feature":"slot_row"},"slot_count":{"label":"Slot count","description":"Changes the number of mounting slots","unit":"count","feature":"slot_row"}},"features":{"body_width":{"kind":"dimension","axis":"x","label":"Overall width"},"body_depth":{"kind":"dimension","axis":"y","label":"Overall depth"},"body_height":{"kind":"dimension","axis":"z","label":"Overall height"},"body_thickness":{"kind":"dimension","axis":"y","label":"Plate thickness"},"central_hole":{"kind":"region","label":"Central hole","min":[{"parameter":"width","scale":0.492,"offset":0},{"parameter":"depth","scale":0.5,"offset":0},{"parameter":"height","scale":0.443,"offset":0}],"max":[{"parameter":"width","scale":0.492,"offset":0},{"parameter":"depth","scale":0.5,"offset":0},{"parameter":"height","scale":0.557,"offset":0}]},"slot_row":{"kind":"region","label":"Slot row","min":[{"parameter":"width","scale":0.307,"offset":0},{"parameter":"depth","scale":0.5,"offset":0},{"parameter":"height","scale":0.159,"offset":0}],"max":[{"parameter":"width","scale":0.579,"offset":0},{"parameter":"depth","scale":0.5,"offset":0},{"parameter":"height","scale":0.831,"offset":0}]}}} */

// Parameters
width = 36.25;
depth = 58.28;
height = 120.0;
thickness = 6.0;
hole_diameter = 12.0;
slot_width = 8.0;
slot_height = 10.0;
slot_count = 5;

// Derived constants
eps = 0.1;

// Central hole position from top view centroid (u=0.492, v=0.557)
// Top view: u->X, v->Y (v=0 is back/+Y, v=1 is front/-Y)
// X = u * width = 0.492 * width
// Y = (1 - v) * depth = (1 - 0.557) * depth = 0.443 * depth
hole_x = 0.492 * width;
hole_y = (1 - 0.557) * depth;

// Slot positions from right view centroids
// Right view: u->Y (u=0 is front/-Y), v->Z (v=0 is bottom)
// But we need X positions for the slots. The right view shows Y-Z plane.
// The slots are at specific X positions (zig-zag) and Z positions.
// From the right view centroids, u gives Y position, v gives Z position.
// The X positions (zig-zag) come from the front view interpretation.
// Right view centroids: (u,v) = (0.307,0.831), (0.576,0.68), (0.31,0.507), (0.579,0.335), (0.307,0.159)
// u in right view maps to Y: Y = u * depth
// v in right view maps to Z: Z = v * height

// Slot Y positions (from right view u values)
slot_y_positions = [0.307, 0.576, 0.31, 0.579, 0.307];
// Slot Z positions (from right view v values)
slot_z_positions = [0.831, 0.68, 0.507, 0.335, 0.159];

// Slot X positions (zig-zag pattern, centered in width)
slot_x_offsets = [0.31, 0.58, 0.31, 0.58, 0.31];

// Scalloped bottom edge parameters
scallop_count = 5;
scallop_depth = 4.0;
scallop_radius = (width / scallop_count) / 2.0;
scallop_height = 8.0; // Only affect bottom portion

// Concave notch at top
notch_width = 12.0;
notch_depth = 5.0;
notch_height = 8.0; // Only affect top portion

difference() {
    // Base Plate - centered at origin
    translate([0, 0, 0])
        cube([width, depth, height], center=true);

    // Central Hole (Top View -> cuts along Y-axis through the plate)
    translate([hole_x - width/2, 0, hole_y - depth/2])
        rotate([90, 0, 0])
            cylinder(d=hole_diameter, h=depth+2*eps, center=true);

    // Slot Row (Right View -> cuts along Y-axis through the plate)
    for (i = [0 : slot_count - 1]) {
        translate([
            (slot_x_offsets[i] - 0.5) * width,
            (slot_y_positions[i] - 0.5) * depth,
            (slot_z_positions[i] - 0.5) * height
        ])
            rotate([90, 0, 0])
                cube([slot_width, slot_height, depth+2*eps], center=true);
    }

    // Concave notch at top edge (cuts into Y from back, limited Z height)
    translate([0, depth/2 - notch_depth/2, height/2 - notch_height/2])
        cube([notch_width, notch_depth+eps, notch_height], center=true);

    // Scalloped bottom edge (cuts into Y from front, limited Z height)
    for (i = [0 : scallop_count - 1]) {
        translate([
            (i + 0.5) * (width / scallop_count) - width/2,
            -depth/2 + scallop_depth/2,
            -height/2 + scallop_height/2
        ])
            cylinder(d=scallop_radius*2, h=scallop_height, center=true);
    }
}
