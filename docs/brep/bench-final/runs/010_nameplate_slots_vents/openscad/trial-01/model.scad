/* doodle-meta {"version":1,"parameters":{"width":{"label":"Overall width","description":"Changes the body width","unit":"mm","feature":"body_width"},"height":{"label":"Overall height","description":"Changes the body height","unit":"mm","feature":"body_height"},"thickness":{"label":"Plate thickness","description":"Changes the plate depth","unit":"mm","feature":"body_thickness"},"corner_radius":{"label":"Corner radius","description":"Changes the outer corner rounding","unit":"mm","feature":"body_corner"}},"features":{"body_width":{"kind":"dimension","axis":"x","label":"Overall width"},"body_height":{"kind":"dimension","axis":"z","label":"Overall height"},"body_thickness":{"kind":"dimension","axis":"y","label":"Plate thickness"},"body_corner":{"kind":"region","label":"Outer corner","min":[0,0,0],"max":[{"parameter":"corner_radius","scale":1,"offset":0},{"parameter":"thickness","scale":1,"offset":0},{"parameter":"corner_radius","scale":1,"offset":0}]}}} */

// --- Parameters ---
width = 140;
height = 29.47;
thickness = 5;
corner_radius = 3;

// Derived dimensions
slot_width = 13.16;
slot_height = 7.37;
slot_radius = 3.68;
slot_x_offset = 16.52;

vent_diameter = 7.37;
vent_count = 5;
vent_pitch = 15.75;

eps = 0.01;

// --- Modules ---

module rounded_rect_2d(w, h, r) {
    // Creates a rounded rectangle centered at (0,0) in XY plane
    // w is X, h is Y
    hull() {
        translate([-w/2 + r, -h/2 + r]) circle(r=r);
        translate([w/2 - r, -h/2 + r]) circle(r=r);
        translate([-w/2 + r, h/2 - r]) circle(r=r);
        translate([w/2 - r, h/2 - r]) circle(r=r);
    }
}

module plate_body() {
    // Extrude the rounded rectangle profile along Y
    // The profile is in XZ, so we create it in XY and rotate
    rotate([90, 0, 0]) {
        linear_extrude(height=thickness, center=true) {
            rounded_rect_2d(width, height, corner_radius);
        }
    }
}

module slot_cutter() {
    // Slot cutter centered at origin, axis along Y
    // Width (X) = slot_width, Height (Z) = slot_height
    // We create a stadium shape in XZ and extrude along Y
    // Stadium: two circles connected by a rectangle
    // Total width = slot_width, Total height = slot_height
    // Radius = slot_height / 2
    // Straight length = slot_width - slot_height
    
    r = slot_height / 2;
    straight_len = slot_width - slot_height;
    
    // Create in XY plane (X is width, Y is height of slot) then rotate to XZ
    // Actually, let's build directly in XZ using hull of cylinders rotated to Y axis?
    // Easier: Build in XY, extrude along Z, then rotate to align with Y.
    
    // Let's build the slot profile in XY (X=slot_width, Y=slot_height)
    // Then extrude along Z (thickness), then rotate to align extrusion with Y.
    
    // Wait, the slot is a through cut along Y.
    // So the profile is in XZ.
    // Let's make a module that creates the slot shape in XZ and extrudes along Y.
    
    // Shape in XZ:
    // Centered at 0,0.
    // X range: -slot_width/2 to slot_width/2
    // Z range: -slot_height/2 to slot_height/2
    // Rounded corners in XZ plane.
    
    // We can use hull of 4 cylinders with axis along Y.
    // Cylinders at (±(slot_width/2 - r), ±(slot_height/2 - r))
    
    r = slot_height / 2;
    x_off = slot_width / 2 - r;
    z_off = slot_height / 2 - r;
    
    hull() {
        translate([-x_off, 0, -z_off]) rotate([90,0,0]) cylinder(h=thickness+2*eps, r=r, center=true);
        translate([ x_off, 0, -z_off]) rotate([90,0,0]) cylinder(h=thickness+2*eps, r=r, center=true);
        translate([-x_off, 0,  z_off]) rotate([90,0,0]) cylinder(h=thickness+2*eps, r=r, center=true);
        translate([ x_off, 0,  z_off]) rotate([90,0,0]) cylinder(h=thickness+2*eps, r=r, center=true);
    }
}

module vent_hole_cutter() {
    // Circular hole, axis along Y
    rotate([90, 0, 0]) {
        cylinder(h=thickness+2*eps, d=vent_diameter, center=true);
    }
}

// --- Main Design ---

difference() {
    // 1. Base Body
    plate_body();
    
    // 2. Left Slot
    // Center X = -width/2 + slot_x_offset
    // Center Z = 0 (vertical center)
    translate([-width/2 + slot_x_offset, 0, 0]) {
        slot_cutter();
    }
    
    // 3. Right Slot
    // Center X = width/2 - slot_x_offset
    translate([width/2 - slot_x_offset, 0, 0]) {
        slot_cutter();
    }
    
    // 4. Vent Holes
    // 5 holes, evenly distributed horizontally
    // Pitch = vent_pitch
    // Total span = (vent_count - 1) * vent_pitch
    // Start X = -total_span / 2
    total_span = (vent_count - 1) * vent_pitch;
    start_x = -total_span / 2;
    
    for (i = [0 : vent_count - 1]) {
        translate([start_x + i * vent_pitch, 0, 0]) {
            vent_hole_cutter();
        }
    }
}
