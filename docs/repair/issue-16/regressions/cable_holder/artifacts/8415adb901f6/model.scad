/* doodle-meta {"version":1,"parameters":{"width":{"label":"Overall width","description":"Changes the body width","unit":"mm","feature":"body_width"},"depth":{"label":"Overall depth","description":"Changes the body depth","unit":"mm","feature":"body_depth"},"height":{"label":"Overall height","description":"Changes the body height","unit":"mm","feature":"body_height"},"thickness":{"label":"Plate thickness","description":"Changes the thickness of the plate","unit":"mm","feature":"body_thickness"},"hole_diameter":{"label":"Central hole diameter","description":"Changes the diameter of the central hole","unit":"mm","feature":"central_hole"},"slot_width":{"label":"Slot width","description":"Changes the width of the mounting slots","unit":"mm","feature":"slot_row"},"slot_height":{"label":"Slot height","description":"Changes the height of the mounting slots","unit":"mm","feature":"slot_row"},"slot_count":{"label":"Slot count","description":"Changes the number of mounting slots","unit":"count","feature":"slot_row"}},"features":{"body_width":{"kind":"dimension","axis":"x","label":"Overall width"},"body_depth":{"kind":"dimension","axis":"y","label":"Overall depth"},"body_height":{"kind":"dimension","axis":"z","label":"Overall height"},"body_thickness":{"kind":"dimension","axis":"y","label":"Plate thickness"},"central_hole":{"kind":"region","label":"Central hole","min":[{"parameter":"width","scale":0.5,"offset":0},{"parameter":"depth","scale":0.5,"offset":0},{"parameter":"height","scale":0.8,"offset":0}],"max":[{"parameter":"width","scale":0.5,"offset":0},{"parameter":"depth","scale":0.5,"offset":0},{"parameter":"height","scale":0.9,"offset":0}]},"slot_row":{"kind":"region","label":"Slot row","min":[{"parameter":"width","scale":0.5,"offset":0},{"parameter":"depth","scale":0.5,"offset":0},{"parameter":"height","scale":0.1,"offset":0}],"max":[{"parameter":"width","scale":0.5,"offset":0},{"parameter":"depth","scale":0.5,"offset":0},{"parameter":"height","scale":0.7,"offset":0}]}}} */

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
slot_end_z = height * 0.65;
slot_pitch = (slot_end_z - slot_start_z) / (slot_count - 1);

// Main Body
difference() {
    // Base Plate
    translate([0, 0, 0])
        cube([width, depth, height], center=true);

    // Central Hole (Top View -> cuts along Z)
    translate([0, 0, hole_z])
        cylinder(d=hole_diameter, h=height+2*eps, center=true);

    // Slot Row (Right View -> cuts along X)
    for (i = [0 : slot_count - 1]) {
        translate([0, 0, slot_start_z + i * slot_pitch])
            cube([width+2*eps, slot_width, slot_height], center=true);
    }
}
