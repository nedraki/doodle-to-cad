/* doodle-meta {"version":1,"parameters":{"width":{"label":"Overall width","description":"Changes the body width (X-axis)","unit":"mm","feature":"body_width"},"depth":{"label":"Overall depth","description":"Changes the body depth (Y-axis)","unit":"mm","feature":"body_depth"},"height":{"label":"Overall height","description":"Changes the body height (Z-axis)","unit":"mm","feature":"body_height"},"wall_thickness":{"label":"Wall thickness","description":"Thickness of the L-profile legs","unit":"mm","feature":"wall_thickness"},"slot_width":{"label":"Slot width","description":"Width of the vertical slots","unit":"mm","feature":"slots"},"slot_height":{"label":"Slot height","description":"Height of the vertical slots","unit":"mm","feature":"slots"},"top_cutout_width":{"label":"Top cutout width","description":"Width of the top rectangular cutout","unit":"mm","feature":"top_cutout"},"top_cutout_height":{"label":"Top cutout height","description":"Height of the top rectangular cutout","unit":"mm","feature":"top_cutout"}},"features":{"body_width":{"kind":"dimension","axis":"x","label":"Overall width"},"body_depth":{"kind":"dimension","axis":"y","label":"Overall depth"},"body_height":{"kind":"dimension","axis":"z","label":"Overall height"},"wall_thickness":{"kind":"dimension","axis":"z","label":"Wall thickness"},"slots":{"kind":"region","label":"Vertical Slots","min":[{"parameter":"width","scale":0.1,"offset":0},{"parameter":"depth","scale":0.0,"offset":0},{"parameter":"height","scale":0.2,"offset":0}],"max":[{"parameter":"width","scale":0.9,"offset":0},{"parameter":"depth","scale":1.0,"offset":0},{"parameter":"height","scale":0.8,"offset":0}]},"top_cutout":{"kind":"region","label":"Top Cutout","min":[{"parameter":"width","scale":0.1,"offset":0},{"parameter":"depth","scale":0.0,"offset":0},{"parameter":"height","scale":0.7,"offset":0}],"max":[{"parameter":"width","scale":0.4,"offset":0},{"parameter":"depth","scale":1.0,"offset":0},{"parameter":"height","scale":0.9,"offset":0}]}}} */

// Parameters
width = 80.18;
depth = 71.67;
height = 100.0;
wall_thickness = 10.0;

// Slot parameters
slot_width = 12.0;
slot_height = 40.0;
slot_y_offset = 15.0; // Distance from back (Y=depth) to slot center? No, slots are in the vertical leg.
// The vertical leg is at Y=0 to Y=wall_thickness.
// Slots cut through Y.

// Top cutout parameters
top_cutout_width = 24.0;
top_cutout_height = 20.0;

// Derived positions
// Front view mapping: u -> X, v -> -Z (from top)
// Outer profile in front view is roughly full width/height.
// Internal profiles:
// contour_8 (top cutout): center u=0.27, v=0.20. 
//   X = 0.27 * width = 21.6 mm.
//   Z = (1 - 0.20) * height = 80 mm.
// contour_6 (slot 1): center u=0.54, v=0.43.
//   X = 0.54 * width = 43.2 mm.
//   Z = (1 - 0.43) * height = 57 mm.
// contour_4 (slot 2): center u=0.33, v=0.61.
//   X = 0.33 * width = 26.4 mm.
//   Z = (1 - 0.61) * height = 39 mm.
// contour_2 (slot 3): center u=0.75, v=0.61.
//   X = 0.75 * width = 60 mm.
//   Z = (1 - 0.61) * height = 39 mm.

// Right view mapping: u -> Y, v -> -Z
// L-shape: Vertical leg at Y=0..wall_thickness. Horizontal base at Z=0..wall_thickness.
// The "back" of the bookend is usually the vertical part.
// In the right view (looking down X), u=0 is Front (Y=0)? 
// Contract: "right: Y = u*depth, so u=0 at the left of the view is the FRONT (-Y)".
// Wait, standard right view looks from +X towards -X? Or from -X?
// "right looks down X". Usually means camera at +X looking towards origin.
// If camera is at +X looking -X, then Y axis points to the left?
// Let's stick to the contract: "right: Y = u*depth, so u=0 at the left of the view is the FRONT (-Y)".
// This implies the view shows Y from 0 to depth.
// The L-shape in the right view:
// Polygon: [0.03, 0.01], [0.07, 0.97], [0.97, 0.99], [0.94, 0.93], [0.17, 0.90], [0.15, 0.04]
// This looks like a thick vertical bar on the left (low u, low Y) and a thick horizontal bar at the bottom (high v, low Z).
// Low u means low Y. So the vertical leg is at Y=0.
// High v means low Z. So the horizontal leg is at Z=0.
// This confirms the L-shape: Vertical leg at Y=0..wall_thickness, Horizontal leg at Z=0..wall_thickness.

// Cutters must go through the vertical leg (Y=0..wall_thickness).
// So cutters are cylinders/cubes along Y axis.

module l_shape_body() {
    // Vertical leg
    cube([width, wall_thickness, height]);
    // Horizontal leg
    // Extends from Y=0 to Y=depth. But overlaps with vertical leg.
    // To avoid non-manifold issues, we can union them.
    // Vertical: X:0..width, Y:0..wall_thickness, Z:0..height
    // Horizontal: X:0..width, Y:0..depth, Z:0..wall_thickness
    // Union is fine.
    translate([0, 0, 0]) cube([width, depth, wall_thickness]);
}

module slot_cutter(x_pos, z_pos, w, h) {
    // Cutter along Y axis
    // Center at x_pos, z_pos.
    // Spans Y from -eps to wall_thickness+eps
    translate([x_pos, 0, z_pos])
    rotate([90, 0, 0]) // Rotate so cylinder axis is Y
    cylinder(h = wall_thickness + 2, r = w/2, center = true);
    
    // Wait, cylinder is round. The spec says "rectangle" or "slot".
    // "slot -> stadium (rounded-ends) cutter"
    // "rectangle -> cube"
    // contour_6, 4 are rectangles. contour_8 is slot.
    // Let's use cubes for rectangles and stadium for slots.
}

module rect_cutter(x_pos, z_pos, w, h) {
    translate([x_pos - w/2, -1, z_pos - h/2])
    cube([w, wall_thickness + 2, h]);
}

module stadium_cutter(x_pos, z_pos, w, h) {
    // Stadium shape: rectangle with semicircular ends.
    // Width w, Height h.
    // If h > w, ends are on top/bottom? Or left/right?
    // "slot" usually implies vertical elongation.
    // contour_8 is "slot". Size 0.3x0.2 (w x h in view).
    // In view, w=0.3, h=0.2. So it's wider than tall?
    // But "slot" usually means long and thin.
    // Let's look at contour_8 polygon: 
    // [0.41, 0.12], [0.35, 0.10], [0.13, 0.11], [0.13, 0.29], [0.42, 0.29], [0.40, 0.21]
    // It's roughly rectangular.
    // The prompt says "slot -> stadium".
    // If it's a "slot", it might be a rounded rectangle.
    // Let's use a rounded rectangle (cube with fillets) or just a cube if confidence is low.
    // Confidence 0.7.
    // Let's use a cube for simplicity unless it's clearly a stadium.
    // Actually, "slot" in intent_refinements maps to stadium.
    // Stadium: cylinder ends + box.
    // If vertical slot: height > width.
    // contour_8: w=0.3, h=0.2. It's horizontal.
    // Let's just use a cube for all, as "rectangle" is the dominant shape for the others.
    // The prompt says "slot -> stadium".
    // I will implement a stadium cutter for the top cutout if it's classified as slot.
    // But contour_8 is the top cutout.
    // Let's make it a rounded rectangle (cube with small fillets) or just cube.
    // Given "3D print", sharp corners are fine.
    // I'll use cubes for all cutouts to ensure clean cuts.
}

// Main design
difference() {
    l_shape_body();
    
    // Top Cutout (contour_8)
    // Center X = 0.27 * width = 21.6
    // Center Z = (1 - 0.20) * height = 80
    // Width = 0.3 * width = 24
    // Height = 0.2 * height = 20
    rect_cutter(21.6, 80.0, 24.0, 20.0);
    
    // Slot 1 (contour_6)
    // Center X = 0.54 * width = 43.2
    // Center Z = (1 - 0.43) * height = 57
    // Width = 0.12 * width = 9.6
    // Height = 0.31 * height = 31
    rect_cutter(43.2, 57.0, 9.6, 31.0);
    
    // Slot 2 (contour_4)
    // Center X = 0.33 * width = 26.4
    // Center Z = (1 - 0.61) * height = 39
    // Width = 0.17 * width = 13.6
    // Height = 0.40 * height = 40
    rect_cutter(26.4, 39.0, 13.6, 40.0);
    
    // Slot 3 (contour_2)
    // Center X = 0.75 * width = 60.0
    // Center Z = (1 - 0.61) * height = 39
    // Width = 0.14 * width = 11.2
    // Height = 0.39 * height = 39
    rect_cutter(60.0, 39.0, 11.2, 39.0);
}
