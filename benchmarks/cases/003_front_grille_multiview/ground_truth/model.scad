// Parametric Front Grille CAD Model
// Units: mm (default scale: 1 grid unit = 10mm)
// Double-check: Symmetrical 7-slot design with circular headlights.

// --- Parametric Variables ---
export_mode = "3D";         // "3D" for extruding solid, "2D" for flat profile (DXF)

thickness = 3;              // 3D extrusion thickness (mm)
grid_unit = 10;             // Scaling factor (mm per grid unit)

// Proportional dimensions (in grid units)
width_units = 13.0;         // Overall width
height_units = 8.0;         // Overall height

// Calculated dimensions (in mm)
total_width = width_units * grid_unit;   // 130 mm
total_height = height_units * grid_unit; // 80 mm

// Headlight Parameters
headlight_diameter = 2.0 * grid_unit;     // 20 mm (2 units)
headlight_radius = headlight_diameter / 2; // 10 mm
headlight_center_x = 4.2 * grid_unit;     // 42 mm from center
headlight_center_y = 1.0 * grid_unit;     // 10 mm above horizontal center line

// Slot Parameters
num_slots = 7;                             // 7 slots (user-specified)
slot_width = 0.35 * grid_unit;             // 3.5 mm (0.35 units)
slot_height = 4.8 * grid_unit;            // 48 mm (4.8 units)
slot_spacing = 0.82 * grid_unit;           // 8.2 mm center-to-center spacing
slot_corner_radius = 0.8;                  // Fillet radius for slot corners
slot_center_y = -0.5 * grid_unit;          // Centered slightly lower than headlights

// Outer Contour Parameters
corner_radius = 5.0;                       // Fillet radius for outer corners

// --- 2D Profile Module ---
module grille_2d() {
    difference() {
        // Main Outer Contour with filleted corners
        offset(r = corner_radius, $fn = 100) {
            offset(delta = -corner_radius) {
                polygon(points = [
                    [0, 38],
                    [40, 38],
                    [58, 35],
                    [63, 20],
                    [63, 5],
                    [43, -12],
                    [43, -32],
                    [20, -38],
                    [0, -38],
                    [-20, -38],
                    [-43, -32],
                    [-43, -12],
                    [-63, 5],
                    [-63, 20],
                    [-58, 35],
                    [-40, 38]
                ]);
            }
        }
        
        // Left Headlight
        translate([-headlight_center_x, headlight_center_y])
            circle(r = headlight_radius, $fn = 100);
            
        // Right Headlight
        translate([headlight_center_x, headlight_center_y])
            circle(r = headlight_radius, $fn = 100);
            
        // 7 Vertical Slots
        for (i = [0 : num_slots - 1]) {
            translate([(i - (num_slots - 1) / 2) * slot_spacing, slot_center_y]) {
                offset(r = slot_corner_radius, $fn = 30) {
                    square([slot_width - 2 * slot_corner_radius, slot_height - 2 * slot_corner_radius], center = true);
                }
            }
        }
    }
}

// --- Main Extrusion Logic ---
if (export_mode == "3D") {
    linear_extrude(height = thickness, center = true, convexity = 10)
        grille_2d();
} else {
    grille_2d();
}
