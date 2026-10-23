/* doodle-meta {"version":1,"parameters":{"width":{"label":"Overall width","description":"Changes the body width","unit":"mm","feature":"body_width"},"height":{"label":"Overall height","description":"Changes the body height","unit":"mm","feature":"body_height"},"thickness":{"label":"Panel thickness","description":"Changes the depth of the grille panel","unit":"mm","feature":"body_thickness"},"headlight_diameter":{"label":"Headlight diameter","description":"Changes the diameter of the circular headlight cutouts","unit":"mm","feature":"headlights"},"slot_width":{"label":"Slot width","description":"Changes the width of the vertical grille slots","unit":"mm","feature":"grille_slots"},"slot_height":{"label":"Slot height","description":"Changes the height of the vertical grille slots","unit":"mm","feature":"grille_slots"},"slot_count":{"label":"Slot count","description":"Changes the number of vertical grille slots","unit":"count","feature":"grille_slots"}},"features":{"body_width":{"kind":"dimension","axis":"x","label":"Overall width"},"body_height":{"kind":"dimension","axis":"z","label":"Overall height"},"body_thickness":{"kind":"dimension","axis":"y","label":"Panel thickness"},"headlights":{"kind":"region","label":"Headlights","min":[{"parameter":"width","scale":0.0927,"offset":0},{"parameter":"thickness","scale":0,"offset":-1},{"parameter":"height","scale":0.4893,"offset":0}],"max":[{"parameter":"width","scale":0.2547,"offset":0},{"parameter":"thickness","scale":1,"offset":1},{"parameter":"height","scale":0.7509,"offset":0}]},"grille_slots":{"kind":"region","label":"Grille Slots","min":[{"parameter":"width","scale":0.2895,"offset":0},{"parameter":"thickness","scale":0,"offset":-1},{"parameter":"height","scale":0.1324,"offset":0}],"max":[{"parameter":"width","scale":0.7027,"offset":0},{"parameter":"thickness","scale":1,"offset":1},{"parameter":"height","scale":0.7385,"offset":0}]}}} */

// Parameters
width = 126.0;
height = 78.83;
thickness = 7.52;
headlight_diameter = 20.0;
slot_width = 5.0;
slot_height = 48.0;
slot_count = 7;

// Derived parameters
eps = 0.1;
slot_pitch = (width * 0.4132) / (slot_count - 1); // Approximate pitch based on measured span
slot_start_x = width * 0.3098; // Center of first slot in mm

// Modules
module grille_body() {
    // Create the main panel shape using a polygon extruded along Y
    // The polygon is defined in XZ plane (front view)
    // Coordinates are normalized [0,1] from measured outer profile, scaled to width/height
    // Note: v is down in view, so Z = (1-v)*height
    
    polygon_points = [
        [0.0097 * width, (1 - 0.5785) * height],
        [0.0521 * width, (1 - 0.9202) * height],
        [0.2027 * width, (1 - 0.9787) * height],
        [0.9267 * width, (1 - 0.9417) * height],
        [0.9865 * width, (1 - 0.7385) * height],
        [0.9768 * width, (1 - 0.5509) * height],
        [0.8359 * width, (1 - 0.3478) * height],
        [0.8243 * width, (1 - 0.0954) * height],
        [0.6524 * width, (1 - 0.0185) * height],
        [0.1833 * width, (1 - 0.0954) * height],
        [0.1622 * width, (1 - 0.3509) * height]
    ];
    
    linear_extrude(height = thickness, center = true) {
        polygon(polygon_points);
    }
}

module headlight_cutter() {
    // Cylinder axis along Y to cut through the front face
    // Positioned at center of headlight in XZ
    // Left headlight center: u=0.1747, v=0.6217 (from contour_4)
    // Right headlight center: u=0.8253, v=0.6263 (from contour_2)
    // Using average v for symmetry or specific positions. 
    // Intent says slot but description says circular. Description wins for "hole".
    // Let's use circular cutouts as per "hole" type in features.
    
    // Left
    translate([0.1747 * width, 0, (1 - 0.6217) * height]) {
        rotate([90, 0, 0]) {
            cylinder(h = thickness + 2*eps, d = headlight_diameter, center = true);
        }
    }
    
    // Right
    translate([0.8253 * width, 0, (1 - 0.6263) * height]) {
        rotate([90, 0, 0]) {
            cylinder(h = thickness + 2*eps, d = headlight_diameter, center = true);
        }
    }
}

module grille_slots_cutter() {
    // Seven vertical slots
    // Centers from measured internal profiles (contours 18, 16, 14, 12, 6, 10, 8)
    // u centers: 0.3098, 0.3736, 0.4353, 0.499, 0.5628, 0.6264, 0.6891
    // v center approx 0.437
    
    slot_centers_u = [0.3098, 0.3736, 0.4353, 0.499, 0.5628, 0.6264, 0.6891];
    slot_center_v = 0.437;
    
    for (i = [0 : slot_count - 1]) {
        translate([slot_centers_u[i] * width, 0, (1 - slot_center_v) * height]) {
            // Slot is a rounded rectangle (stadium) or just rectangle? 
            // Intent says "slot" -> stadium. But description says "rectangular slots".
            // Let's use a cube for simplicity as per "rectangular" description, 
            // but intent_refinements says "slot -> stadium". 
            // Given "rectangular" in description and "slot" in intent, 
            // and low confidence on shape, a simple rectangular cut is safer for "rectangular slots".
            // However, "slot" usually implies rounded ends. 
            // Let's stick to rectangular as per explicit description "rectangular slots".
            
            cube([slot_width, thickness + 2*eps, slot_height], center = true);
        }
    }
}

// Main Design
difference() {
    grille_body();
    headlight_cutter();
    grille_slots_cutter();
}
