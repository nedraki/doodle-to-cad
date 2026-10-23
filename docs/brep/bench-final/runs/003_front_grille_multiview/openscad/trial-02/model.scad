/* doodle-meta {"version":1,"parameters":{"width":{"label":"Overall width","description":"Changes the body width","unit":"mm","feature":"body_width"},"height":{"label":"Overall height","description":"Changes the body height","unit":"mm","feature":"body_height"},"thickness":{"label":"Plate thickness","description":"Changes the plate depth","unit":"mm","feature":"body_thickness"},"headlight_diameter":{"label":"Headlight diameter","description":"Changes the headlight opening size","unit":"mm","feature":"headlights"},"slot_width":{"label":"Slot width","description":"Changes the vertical slot width","unit":"mm","feature":"slots"},"slot_height":{"label":"Slot height","description":"Changes the vertical slot height","unit":"mm","feature":"slots"}},"features":{"body_width":{"kind":"dimension","axis":"x","label":"Overall width"},"body_height":{"kind":"dimension","axis":"z","label":"Overall height"},"body_thickness":{"kind":"dimension","axis":"y","label":"Plate thickness"},"headlights":{"kind":"region","label":"Headlights","min":[{"parameter":"width","scale":0.09},{"parameter":"thickness","scale":-0.1},{"parameter":"height","scale":0.49}],"max":[{"parameter":"width","scale":0.26},{"parameter":"thickness","scale":1.1},{"parameter":"height","scale":0.75}]},"slots":{"kind":"region","label":"Vertical Slots","min":[{"parameter":"width","scale":0.29},{"parameter":"thickness","scale":-0.1},{"parameter":"height","scale":0.13}],"max":[{"parameter":"width","scale":0.71},{"parameter":"thickness","scale":1.1},{"parameter":"height","scale":0.74}]}}} */

// Top-level parameters (user-editable allowlist)
width = 126.0;
height = 78.83;
thickness = 7.52;
headlight_diameter = 21.0;
slot_width = 5.1;
slot_height = 48.0;

// Derived constants (not editable)
eps = 0.1;
headlight_y = 0.6263 * height; // Z center
headlight_x_offset = 0.3253 * width; // Distance from center
slot_y_center = 0.437 * height; // Z center
slot_x_start = 0.3098 * width; // First slot center X
slot_pitch = 0.0632 * width; // Pitch between slots
num_slots = 7;

// Main design
difference() {
    // Positive body: extruded polygon in XZ plane, thickness along Y
    translate([0, 0, 0])
        linear_extrude(height=thickness, center=true)
            polygon(points=outer_profile_points(), paths=outer_profile_path());

    // Subtract headlight cutouts (through along Y)
    translate([width/2 - headlight_x_offset, 0, headlight_y])
        rotate([90, 0, 0])
            cylinder(d=headlight_diameter, h=thickness + 2*eps, center=true);
            
    translate([width/2 + headlight_x_offset, 0, headlight_y])
        rotate([90, 0, 0])
            cylinder(d=headlight_diameter, h=thickness + 2*eps, center=true);

    // Subtract vertical slots (through along Y)
    for (i = [0 : num_slots - 1]) {
        translate([slot_x_start + i * slot_pitch, 0, slot_y_center])
            cube([slot_width, thickness + 2*eps, slot_height], center=true);
    }
}

// Helper module for outer profile polygon
function outer_profile_points() = [
    [0.0097 * width, 0.5785 * height],
    [0.0521 * width, 0.0798 * height],
    [0.2027 * width, 0.0213 * height],
    [0.9267 * width, 0.0583 * height],
    [0.9865 * width, 0.2615 * height],
    [0.9768 * width, 0.4491 * height],
    [0.8359 * width, 0.6522 * height],
    [0.8243 * width, 0.9046 * height],
    [0.6524 * width, 0.9815 * height],
    [0.1833 * width, 0.9046 * height],
    [0.1622 * width, 0.6491 * height]
];

function outer_profile_path() = [
    [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
];
