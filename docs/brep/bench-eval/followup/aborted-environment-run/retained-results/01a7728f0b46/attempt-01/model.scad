/* doodle-meta {"version":1,"parameters":{"width":{"label":"Overall width","description":"Changes the body width","unit":"mm","feature":"body_width"},"height":{"label":"Overall height","description":"Changes the body height","unit":"mm","feature":"body_height"},"thickness":{"label":"Plate thickness","description":"Changes the depth of the grille plate","unit":"mm","feature":"body_thickness"},"slot_count":{"label":"Slot count","description":"Number of vertical slots","unit":"count","feature":"slot_pattern"},"slot_width":{"label":"Slot width","description":"Width of each vertical slot","unit":"mm","feature":"slot_pattern"},"slot_height":{"label":"Slot height","description":"Height of each vertical slot","unit":"mm","feature":"slot_pattern"},"headlight_diameter":{"label":"Headlight diameter","description":"Diameter of the circular headlight openings","unit":"mm","feature":"headlight_openings"}},"features":{"body_width":{"kind":"dimension","axis":"x","label":"Overall width"},"body_height":{"kind":"dimension","axis":"z","label":"Overall height"},"body_thickness":{"kind":"dimension","axis":"y","label":"Plate thickness"},"slot_pattern":{"kind":"region","label":"Vertical Slots","min":[36.5,0,10.0],"max":[89.5,7.52,68.0]},"headlight_openings":{"kind":"region","label":"Headlights","min":[10.0,0,15.0],"max":[116.0,7.52,45.0]}}} */

// Parameters
width = 126.0;
height = 78.83;
thickness = 7.52;
slot_count = 7;
slot_width = 5.0;
slot_height = 58.0;
headlight_diameter = 20.0;

// Derived constants
eps = 0.1;
slot_pitch = 8.0;
slot_start_x = (width - (slot_count - 1) * slot_pitch) / 2;
slot_center_z = height * 0.55; // Approx 43mm from bottom
headlight_center_z = height * 0.38; // Approx 30mm from bottom
headlight_offset_x = width * 0.33; // Approx 41.5mm from center

// Main Body Profile (Front View XZ plane)
// Constructed from measured polygon points scaled to mm
module grille_body() {
    // Define points in XZ (X from left, Z from bottom)
    // Normalized u -> X = u * width
    // Normalized v -> Z = (1 - v) * height
    
    // Points from measured_view_geometry view_2 outer_profile
    // [u, v] -> [X, Z]
    // 0.0097, 0.5785 -> 1.22, 33.23
    // 0.0521, 0.9202 -> 6.56, 6.30
    // 0.2027, 0.9787 -> 25.54, 1.68
    // 0.9267, 0.9417 -> 116.76, 4.59
    // 0.9865, 0.7385 -> 124.30, 20.61
    // 0.9768, 0.5509 -> 123.08, 35.40
    // 0.8359, 0.3478 -> 105.33, 51.42
    // 0.8243, 0.0954 -> 103.87, 71.31
    // 0.6524, 0.0185 -> 82.20, 77.37
    // 0.1833, 0.0954 -> 23.10, 71.31
    // 0.1622, 0.3509 -> 20.44, 51.18
    
    polygon_points = [
        [1.22, 33.23],
        [6.56, 6.30],
        [25.54, 1.68],
        [116.76, 4.59],
        [124.30, 20.61],
        [123.08, 35.40],
        [105.33, 51.42],
        [103.87, 71.31],
        [82.20, 77.37],
        [23.10, 71.31],
        [20.44, 51.18]
    ];
    
    // Extrude along Y
    linear_extrude(height = thickness, center = false) {
        polygon(polygon_points);
    }
}

// Vertical Slots
module vertical_slots() {
    for (i = [0 : slot_count - 1]) {
        translate([slot_start_x + i * slot_pitch, -eps, slot_center_z - slot_height/2]) {
            cube([slot_width, thickness + 2*eps, slot_height], center = false);
        }
    }
}

// Headlight Openings
module headlight_openings() {
    // Left Headlight
    translate([width/2 - headlight_offset_x, -eps, headlight_center_z]) {
        rotate([90, 0, 0]) {
            cylinder(h = thickness + 2*eps, d = headlight_diameter, center = true);
        }
    }
    // Right Headlight
    translate([width/2 + headlight_offset_x, -eps, headlight_center_z]) {
        rotate([90, 0, 0]) {
            cylinder(h = thickness + 2*eps, d = headlight_diameter, center = true);
        }
    }
}

// Final Assembly
difference() {
    grille_body();
    vertical_slots();
    headlight_openings();
}
