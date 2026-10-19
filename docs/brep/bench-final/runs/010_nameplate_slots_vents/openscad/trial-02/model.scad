/* doodle-meta {"version":1,"parameters":{"plate_width":{"label":"Overall width","description":"Changes the body width","unit":"mm","feature":"body_width"},"plate_height":{"label":"Overall height","description":"Changes the body height","unit":"mm","feature":"body_height"},"plate_thickness":{"label":"Plate thickness","description":"Changes the plate thickness","unit":"mm","feature":"body_thickness"}},"features":{"body_width":{"kind":"dimension","axis":"x","label":"Overall width"},"body_height":{"kind":"dimension","axis":"z","label":"Overall height"},"body_thickness":{"kind":"dimension","axis":"y","label":"Plate thickness"}}} */

// Top-level editable parameters
plate_width = 140.0;
plate_height = 29.47;
plate_thickness = 3.0;

// Derived constants (not editable)
eps = 0.01;

// Helper module for a horizontal slot (stadium shape) in XZ plane, extruded along Y
module slot_cutter(w, h) {
    // w = width along X, h = height along Z
    // Stadium: rectangle with semicircular ends along X
    r = h / 2;
    // Build in XY plane then rotate to XZ, extrude along Y
    // Actually, build directly: use hull of two circles in XZ, extrude along Y
    // We'll create the 2D profile in XY (local), then rotate([90,0,0]) to put it in XZ,
    // and extrude along local Z which becomes global Y after rotation.
    // To avoid center issues, we extrude from -eps to plate_thickness+eps in local Z
    // after rotation. Simpler: build the profile in XZ directly using rotate_extrude? No.
    // Best approach: create 2D shape in XY, linear_extrude along Z, then rotate([90,0,0]).
    // The extrusion height must span the full plate thickness in Y after rotation.
    // After rotate([90,0,0]), local Z -> global -Y. So we need extrusion from 
    // -(plate_thickness/2 + eps) to +(plate_thickness/2 + eps) in local Z, centered.
    // Using center=true should work if the profile is centered at origin.
    linear_extrude(height = plate_thickness + 2*eps, center = true) {
        hull() {
            circle(r = r);
            translate([w - h, 0]) circle(r = r);
        }
    }
}

// Helper module for a vertical vent hole (stadium shape) in XZ plane, extruded along Y
module vent_cutter(w, h) {
    // w = width along X, h = height along Z
    // Stadium: rectangle with semicircular ends along Z (vertical)
    r = w / 2;
    linear_extrude(height = plate_thickness + 2*eps, center = true) {
        hull() {
            circle(r = r);
            translate([0, h - w]) circle(r = r);
        }
    }
}

// Main design
difference() {
    // Base plate: centered in X, Y from -thickness/2 to +thickness/2, Z from 0 to height
    translate([0, 0, plate_height/2])
    cube([plate_width, plate_thickness, plate_height], center = true);

    // Left End Slot (feat_1)
    // Center view normalized: [0.118, 0.511]
    // X_center = (0.118 - 0.5) * plate_width = -53.48
    // Z_center = (0.5 - 0.511) * plate_height + plate_height/2 = 14.41
    // Slot Width (X) = 13.16, Slot Height (Z) = 7.37
    translate([-53.48, 0, 14.41])
    rotate([90, 0, 0])
    slot_cutter(13.16, 7.37);

    // Right End Slot (feat_2)
    // Center view normalized: [0.8752, 0.511]
    // X_center = (0.8752 - 0.5) * 140 = 52.53
    // Z_center = 14.41
    translate([52.53, 0, 14.41])
    rotate([90, 0, 0])
    slot_cutter(13.16, 7.37);

    // Vent Hole 1 (feat_3)
    // Center view normalized: [0.3564, 0.511]
    // X_center = (0.3564 - 0.5) * 140 = -20.104
    // Z_center = 14.41
    // Width (X) = 7.154, Height (Z) = 7.37
    translate([-20.104, 0, 14.41])
    rotate([90, 0, 0])
    vent_cutter(7.154, 7.37);

    // Vent Hole 2 (feat_4)
    // Center view normalized: [0.4286, 0.511]
    // X_center = (0.4286 - 0.5) * 140 = -9.996
    translate([-9.996, 0, 14.41])
    rotate([90, 0, 0])
    vent_cutter(7.154, 7.37);

    // Vent Hole 3 (feat_5)
    // Center view normalized: [0.497, 0.511]
    // X_center = (0.497 - 0.5) * 140 = -0.42
    translate([-0.42, 0, 14.41])
    rotate([90, 0, 0])
    vent_cutter(7.154, 7.37);

    // Vent Hole 4 (feat_6)
    // Center view normalized: [0.5669, 0.511]
    // X_center = (0.5669 - 0.5) * 140 = 9.366
    translate([9.366, 0, 14.41])
    rotate([90, 0, 0])
    vent_cutter(7.154, 7.37);

    // Vent Hole 5 (feat_7)
    // Center view normalized: [0.6376, 0.511]
    // X_center = (0.6376 - 0.5) * 140 = 19.264
    translate([19.264, 0, 14.41])
    rotate([90, 0, 0])
    vent_cutter(7.154, 7.37);
}
