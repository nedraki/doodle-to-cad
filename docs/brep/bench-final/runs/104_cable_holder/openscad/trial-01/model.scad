/* doodle-meta {"version":1,"parameters":{"width":{"label":"Overall width","description":"Changes the body width (X)","unit":"mm","feature":"body_width"},"depth":{"label":"Overall depth","description":"Changes the body depth (Y)","unit":"mm","feature":"body_depth"},"height":{"label":"Overall height","description":"Changes the body height (Z)","unit":"mm","feature":"body_height"},"slot_width":{"label":"Slot width","description":"Width of each cable retention slot","unit":"mm","feature":"cable_slots"},"slot_height":{"label":"Slot height","description":"Height of each cable retention slot","unit":"mm","feature":"cable_slots"},"slot_count":{"label":"Slot count","description":"Number of cable retention slots","unit":"count","feature":"cable_slots"}},"features":{"body_width":{"kind":"dimension","axis":"x","label":"Overall width"},"body_depth":{"kind":"dimension","axis":"y","label":"Overall depth"},"body_height":{"kind":"dimension","axis":"z","label":"Overall height"},"cable_slots":{"kind":"region","label":"Cable retention slots","min":[{"parameter":"width","scale":0.25,"offset":0},{"parameter":"depth","scale":0.1,"offset":0},{"parameter":"height","scale":0.05,"offset":0}],"max":[{"parameter":"width","scale":0.75,"offset":0},{"parameter":"depth","scale":0.9,"offset":0},{"parameter":"height","scale":0.95,"offset":0}]}}} */

// Top-level editable parameters (allowlist)
width = 12.08;
depth = 19.43;
height = 40.0;
slot_width = 2.7;
slot_height = 3.6;
slot_count = 5;

// Derived (not editable)
eps = 0.01;
slot_pitch = (height - 2 * slot_height) / (slot_count - 1);
slot_x_left = width * 0.3245;
slot_x_right = width * 0.5716;
slot_y = depth * 0.5;

module cable_holder() {
    // Positive body: rectangular plate on build plate
    cube([width, depth, height]);

    // Subtractive cutters
    difference() {
        // (handled by outer difference below)
    }
}

// Single top-level design instantiation
difference() {
    cable_holder();

    // Mounting hole: circular through-hole in top flange, cut along Z (top view)
    translate([width * 0.4915, depth * (1 - 0.5519), -eps])
        cylinder(h = height + 2 * eps, d = width * 0.3223, center = false);

    // Cable retention slots: staggered vertical array, cut along X (right view)
    for (i = [0 : slot_count - 1]) {
        slot_z = slot_height / 2 + i * slot_pitch;
        slot_x = (i % 2 == 0) ? slot_x_left : slot_x_right;
        translate([slot_x, slot_y, slot_z])
            rotate([0, 90, 0])
                cylinder(h = width + 2 * eps, d = slot_width, center = true);
    }
}
