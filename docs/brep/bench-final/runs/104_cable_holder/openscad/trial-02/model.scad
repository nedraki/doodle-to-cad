/* doodle-meta {"version":1,"parameters":{"width":{"label":"Overall width","description":"Changes the body width","unit":"mm","feature":"body_width"},"depth":{"label":"Overall depth","description":"Changes the body depth","unit":"mm","feature":"body_depth"},"height":{"label":"Overall height","description":"Changes the body height","unit":"mm","feature":"body_height"},"hole_diameter":{"label":"Mounting hole diameter","description":"Diameter of the central mounting hole","unit":"mm","feature":"mounting_hole"},"slot_width":{"label":"Slot width","description":"Width of each cable retention slot","unit":"mm","feature":"cable_slots"},"slot_height":{"label":"Slot height","description":"Height of each cable retention slot","unit":"mm","feature":"cable_slots"},"slot_count":{"label":"Slot count","description":"Number of cable retention slots","unit":"count","feature":"cable_slots"}},"features":{"body_width":{"kind":"dimension","axis":"x","label":"Overall width"},"body_depth":{"kind":"dimension","axis":"y","label":"Overall depth"},"body_height":{"kind":"dimension","axis":"z","label":"Overall height"},"mounting_hole":{"kind":"region","label":"Mounting hole","min":[{"parameter":"width","scale":0.5,"offset":0},{"parameter":"depth","scale":0.5,"offset":0},{"parameter":"height","scale":0.4481,"offset":0}],"max":[{"parameter":"width","scale":0.5,"offset":0},{"parameter":"depth","scale":0.5,"offset":0},{"parameter":"height","scale":0.6606,"offset":0}]},"cable_slots":{"kind":"region","label":"Cable slots","min":[{"parameter":"width","scale":0.5,"offset":0},{"parameter":"depth","scale":0.1708,"offset":0},{"parameter":"height","scale":0.8292,"offset":0}],"max":[{"parameter":"width","scale":0.5,"offset":0},{"parameter":"depth","scale":0.8203,"offset":0},{"parameter":"height","scale":0.1797,"offset":0}]}}} */

width = 12.08;
depth = 19.43;
height = 40.0;
hole_diameter = 4.0;
slot_width = 2.68;
slot_height = 3.59;
slot_count = 5;

eps = 0.01;

module body() {
    cube([width, depth, height], center=true);
}

module mounting_hole() {
    // Hole center in view_1 (top): u=0.4915, v=0.5519
    // X = (0.4915 - 0.5) * width = -0.0102 * width
    // Y = (0.5 - 0.5519) * depth = -0.0519 * depth
    // Z = (0.5 - 0.5519) * height = -0.0519 * height
    translate([
        (0.4915 - 0.5) * width,
        (0.5 - 0.5519) * depth,
        (0.5 - 0.5519) * height
    ])
    rotate([90, 0, 0])
    cylinder(d=hole_diameter, h=depth + 2*eps, center=true);
}

module cable_slots() {
    // Slots in view_2 (right): u maps to +Y, v maps to -Z
    // Centers (u, v):
    // 1: (0.3245, 0.1708) -> Y = (0.3245-0.5)*depth, Z = (0.5-0.1708)*height
    // 2: (0.5716, 0.3390) -> Y = (0.5716-0.5)*depth, Z = (0.5-0.3390)*height
    // 3: (0.3245, 0.5062) -> Y = (0.3245-0.5)*depth, Z = (0.5-0.5062)*height
    // 4: (0.5716, 0.6757) -> Y = (0.5716-0.5)*depth, Z = (0.5-0.6757)*height
    // 5: (0.3245, 0.8203) -> Y = (0.3245-0.5)*depth, Z = (0.5-0.8203)*height
    
    slot_y_positions = [
        (0.3245 - 0.5) * depth,
        (0.5716 - 0.5) * depth,
        (0.3245 - 0.5) * depth,
        (0.5716 - 0.5) * depth,
        (0.3245 - 0.5) * depth
    ];
    
    slot_z_positions = [
        (0.5 - 0.1708) * height,
        (0.5 - 0.3390) * height,
        (0.5 - 0.5062) * height,
        (0.5 - 0.6757) * height,
        (0.5 - 0.8203) * height
    ];
    
    for (i = [0 : slot_count - 1]) {
        translate([0, slot_y_positions[i], slot_z_positions[i]])
        rotate([0, 90, 0])
        cube([slot_height + 2*eps, slot_width, width + 2*eps], center=true);
    }
}

difference() {
    body();
    mounting_hole();
    cable_slots();
}
