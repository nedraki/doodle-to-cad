/* doodle-meta {"version":1,"parameters":{"width":{"label":"Overall width","description":"Changes the body width","unit":"mm","feature":"body_width"},"height":{"label":"Overall height","description":"Changes the body height","unit":"mm","feature":"body_height"},"depth":{"label":"Overall depth","description":"Changes the body depth","unit":"mm","feature":"body_depth"},"slot_width":{"label":"Slot width","description":"Changes the width of the grille slots","unit":"mm","feature":"grille_slots"},"slot_height":{"label":"Slot height","description":"Changes the height of the grille slots","unit":"mm","feature":"grille_slots"},"headlight_diameter":{"label":"Headlight diameter","description":"Changes the diameter of the headlight openings","unit":"mm","feature":"headlights"}},"features":{"body_width":{"kind":"dimension","axis":"x","label":"Overall width"},"body_height":{"kind":"dimension","axis":"z","label":"Overall height"},"body_depth":{"kind":"dimension","axis":"y","label":"Overall depth"},"grille_slots":{"kind":"region","label":"Grille Slots","min":[34.75,0,19.61],"max":[85.0,7.16,65.15]},"headlights":{"kind":"region","label":"Headlights","min":[11.11,0,18.12],"max":[108.89,7.16,38.68]}}} */

// Top-level parameters (user-editable)
width = 120.0;
height = 75.07;
depth = 7.16;
slot_width = 4.86;
slot_height = 45.51;
headlight_diameter = 19.69;

// Derived constants (not user-editable)
eps = 0.01;
slot_count = 7;
slot_pitch = 7.55;
slot_start_x = 37.18;
slot_center_z = 42.38;
headlight_left_x = 20.96;
headlight_right_x = 99.04;
headlight_center_z = 28.4;

// Outer profile polygon in XZ plane (front view)
// Coordinates from feature_placements_mm contour_0
module grille_body() {
    polygon([
        [1.16, 31.64],
        [1.62, 18.24],
        [6.25, 5.99],
        [24.32, 1.6],
        [97.52, 2.3],
        [111.2, 4.38],
        [114.9, 8.54],
        [118.38, 19.63],
        [117.22, 33.71],
        [100.31, 48.96],
        [98.92, 67.91],
        [78.29, 73.68],
        [43.31, 73.68],
        [22.0, 67.91],
        [19.21, 63.06],
        [19.46, 48.73],
        [2.56, 34.88]
    ]);
}

// Slot cutter: stadium shape (rectangle with half-round ends)
// Cut along Y axis (through the front face)
// Note: The body is rotated [90,0,0] then extruded along Z.
// This maps the 2D polygon (x, z) to 3D (x, -z, y_extrude).
// To cut through the body along Y, we need cutters that span the Y range of the body.
// The body spans Y from -height to 0 (due to rotation and extrusion).
// We define cutters in the same coordinate system as the body BEFORE rotation? 
// No, the difference() is applied to the rotated body.
// So cutters must be in the final world coordinates.
// World coords: X is width, Y is depth (0 to depth), Z is height (0 to height).
// Wait, let's re-verify the body transform.
// rotate([90,0,0]) linear_extrude(height=depth) polygon(x,z)
// Polygon point (px, pz) -> 3D (px, pz, 0) -> Extrude -> (px, pz, y) for y in [0, depth]
// Rotate 90 about X: (x, y, z) -> (x, -z, y)
// So (px, pz, y) -> (px, -y, pz)
// The body occupies X in [min_px, max_px], Y in [-depth, 0], Z in [min_pz, max_pz].
// The cutters need to span Y from -depth-eps to eps.
// And be positioned at correct X and Z.

module slot_cutter(x, z, w, h) {
    // Rectangle part
    translate([x - w/2, -depth - eps, z - h/2 + w/2])
        cube([w, depth + 2*eps, h - w]);
    // Top half-circle
    translate([x, -depth - eps, z + h/2 - w/2])
        rotate([90, 0, 0])
            cylinder(h = depth + 2*eps, r = w/2, center = true);
    // Bottom half-circle
    translate([x, -depth - eps, z - h/2 + w/2])
        rotate([90, 0, 0])
            cylinder(h = depth + 2*eps, r = w/2, center = true);
}

// Headlight cutter: cylinder cut along Y axis
module headlight_cutter(x, z, d) {
    translate([x, -depth - eps, z])
        rotate([90, 0, 0])
            cylinder(h = depth + 2*eps, d = d, center = true);
}

// Main design
difference() {
    // Positive body: extrude front profile along Y
    rotate([90, 0, 0])
        linear_extrude(height = depth)
            grille_body();
    
    // Subtract grille slots (7 vertical slots)
    for (i = [0:slot_count-1]) {
        slot_x = slot_start_x + i * slot_pitch;
        slot_cutter(slot_x, slot_center_z, slot_width, slot_height);
    }
    
    // Subtract left headlight
    headlight_cutter(headlight_left_x, headlight_center_z, headlight_diameter);
    
    // Subtract right headlight
    headlight_cutter(headlight_right_x, headlight_center_z, headlight_diameter);
}
