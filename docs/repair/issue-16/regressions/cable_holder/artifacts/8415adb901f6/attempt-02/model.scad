/* doodle-meta {"version":1,"parameters":{"width":{"label":"Overall width","description":"Changes the body width","unit":"mm","feature":"body_width"},"depth":{"label":"Overall depth","description":"Changes the body depth","unit":"mm","feature":"body_depth"},"height":{"label":"Overall height","description":"Changes the body height","unit":"mm","feature":"body_height"},"thickness":{"label":"Plate thickness","description":"Changes the thickness of the plate","unit":"mm","feature":"body_thickness"},"hole_diameter":{"label":"Central hole diameter","description":"Changes the diameter of the central hole","unit":"mm","feature":"central_hole"},"slot_width":{"label":"Slot width","description":"Changes the width of the mounting slots","unit":"mm","feature":"slot_row"},"slot_height":{"label":"Slot height","description":"Changes the height of the mounting slots","unit":"mm","feature":"slot_row"},"slot_count":{"label":"Slot count","description":"Changes the number of mounting slots","unit":"count","feature":"slot_row"}},"features":{"body_width":{"kind":"dimension","axis":"x","label":"Overall width"},"body_depth":{"kind":"dimension","axis":"y","label":"Overall depth"},"body_height":{"kind":"dimension","axis":"z","label":"Overall height"},"body_thickness":{"kind":"dimension","axis":"y","label":"Plate thickness"},"central_hole":{"kind":"region","label":"Central hole","min":[{"parameter":"width","scale":0.5,"offset":0},{"parameter":"depth","scale":0.5,"offset":0},{"parameter":"height","scale":0.8,"offset":0}],"max":[{"parameter":"width","scale":0.5,"offset":0},{"parameter":"depth","scale":0.5,"offset":0},{"parameter":"height","scale":0.9,"offset":0}]},"slot_row":{"kind":"region","label":"Slot row","min":[{"parameter":"width","scale":0.2,"offset":0},{"parameter":"depth","scale":0.5,"offset":0},{"parameter":"height","scale":0.1,"offset":0}],"max":[{"parameter":"width","scale":0.8,"offset":0},{"parameter":"depth","scale":0.5,"offset":0},{"parameter":"height","scale":0.9,"offset":0}]}}} */

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
hole_z = height * 0.85;
slot_start_z = height * 0.15;
slot_end_z = height * 0.85;
slot_pitch = (slot_end_z - slot_start_z) / (slot_count - 1);

// Zig-zag offsets in X (normalized 0-1, mapped to width)
// Right view centroids: u=0.31 (left), u=0.58 (right) alternating
// u=0 is left edge, u=1 is right edge of the plate in right view
// In CAD: X goes from 0 to width. u=0.31 -> X=0.31*width, u=0.58 -> X=0.58*width
slot_x_offsets = [0.31, 0.58, 0.31, 0.58, 0.31];

// Scalloped bottom edge parameters
scallop_count = 5;
scallop_depth = 4.0;
scallop_radius = (width / scallop_count) / 2.0;

// Concave notch at top
notch_width = 12.0;
notch_depth = 5.0;

difference() {
    // Base Plate
    translate([0, 0, 0])
        cube([width, depth, height], center=true);

    // Central Hole (Top View -> cuts along Z)
    translate([0, 0, hole_z])
        cylinder(d=hole_diameter, h=height+2*eps, center=true);

    // Slot Row (Right View -> cuts along X)
    for (i = [0 : slot_count - 1]) {
        translate([
            (slot_x_offsets[i] - 0.5) * width,
            0,
            slot_start_z + i * slot_pitch
        ])
            cube([width+2*eps, slot_width, slot_height], center=true);
    }

    // Concave notch at top edge (cuts into Y from back)
    translate([0, depth/2 - notch_depth/2, height/2])
        cube([notch_width, notch_depth+eps, height+2*eps], center=true);

    // Scalloped bottom edge (cuts into Y from front)
    for (i = [0 : scallop_count - 1]) {
        translate([
            (i + 0.5) * (width / scallop_count) - width/2,
            -depth/2 + scallop_depth/2,
            0
        ])
            cylinder(d=scallop_radius*2, h=height+2*eps, center=true);
    }
}
