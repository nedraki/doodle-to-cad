/* doodle-meta {"version":1,"parameters":{"width":{"label":"Overall width","description":"Changes the body width","unit":"mm","feature":"body_width"},"height":{"label":"Overall height","description":"Changes the body height","unit":"mm","feature":"body_height"},"thickness":{"label":"Plate thickness","description":"Changes the plate thickness (Y-axis)","unit":"mm","feature":"body_thickness"},"hole_left_d":{"label":"Left hole diameter","description":"Diameter of the top-left hole","unit":"mm","feature":"hole_left"},"hole_right_d":{"label":"Right hole diameter","description":"Diameter of the bottom-right hole","unit":"mm","feature":"hole_right"},"slot_length":{"label":"Slot length","description":"Length of the central slot","unit":"mm","feature":"center_slot"},"slot_width":{"label":"Slot width","description":"Width of the central slot","unit":"mm","feature":"center_slot"}},"features":{"body_width":{"kind":"dimension","axis":"x","label":"Overall width"},"body_height":{"kind":"dimension","axis":"z","label":"Overall height"},"body_thickness":{"kind":"dimension","axis":"y","label":"Plate thickness"},"hole_left":{"kind":"region","label":"Left hole","min":[{"parameter":"hole_left_x","scale":1,"offset":-4.15},{"parameter":"thickness","scale":0,"offset":0},{"parameter":"hole_left_z","scale":1,"offset":-4.15}],"max":[{"parameter":"hole_left_x","scale":1,"offset":4.15},{"parameter":"thickness","scale":1,"offset":0},{"parameter":"hole_left_z","scale":1,"offset":4.15}]},"hole_right":{"kind":"region","label":"Right hole","min":[{"parameter":"hole_right_x","scale":1,"offset":-4.3},{"parameter":"thickness","scale":0,"offset":0},{"parameter":"hole_right_z","scale":1,"offset":-4.3}],"max":[{"parameter":"hole_right_x","scale":1,"offset":4.3},{"parameter":"thickness","scale":1,"offset":0},{"parameter":"hole_right_z","scale":1,"offset":4.3}]},"center_slot":{"kind":"region","label":"Center slot","min":[{"parameter":"slot_center_x","scale":1,"offset":-15},{"parameter":"thickness","scale":0,"offset":0},{"parameter":"slot_center_z","scale":1,"offset":-5.2}],"max":[{"parameter":"slot_center_x","scale":1,"offset":15},{"parameter":"thickness","scale":1,"offset":0},{"parameter":"slot_center_z","scale":1,"offset":5.2}]}}} */

// Top-level parameters (user-editable)
width = 100.0;
height = 61.98;
thickness = 9.65;

// Feature positions (derived from measured view geometry, not user-editable)
hole_left_x = 16.5;
hole_left_z = 44.9;
hole_left_d = 8.3;

hole_right_x = 83.0;
hole_right_z = 16.7;
hole_right_d = 8.6;

slot_center_x = 49.1;
slot_center_z = 30.4;
slot_length = 30.0;
slot_width = 10.4;

// Implementation constants
eps = 0.01;

// Main design
difference() {
    // Positive body: rectangular plate
    cube([width, thickness, height]);
    
    // Subtract left hole (through along Y)
    translate([hole_left_x, thickness/2, hole_left_z])
        rotate([90, 0, 0])
            cylinder(d=hole_left_d, h=thickness+2*eps, center=true);
    
    // Subtract right hole (through along Y)
    translate([hole_right_x, thickness/2, hole_right_z])
        rotate([90, 0, 0])
            cylinder(d=hole_right_d, h=thickness+2*eps, center=true);
    
    // Subtract center slot (through along Y)
    translate([slot_center_x, thickness/2, slot_center_z])
        rotate([90, 0, 0])
            slot_cutter(slot_length, slot_width, thickness+2*eps);
}

// Module for slot cutter (stadium shape)
module slot_cutter(length, width, height) {
    // Slot is oriented along X in the cutter's local frame (after rotation)
    // The slot's long axis is along X, short axis along Z (in front view)
    // After rotate([90,0,0]), the cylinder axis is along Y (through the plate)
    // We need to create a stadium shape in the XZ plane of the cutter's local frame
    // which becomes XY after rotation... wait, let's think carefully.
    
    // The cutter is rotated [90,0,0] so its local Z becomes global Y.
    // In the cutter's local frame (before rotation), we want the slot profile in XY.
    // The slot's long axis should be along global X, which is local X after rotation.
    // The slot's short axis should be along global Z, which is local Y after rotation.
    
    // So in the cutter's local frame, we create a stadium in XY:
    // - Long axis along local X (length)
    // - Short axis along local Y (width)
    
    // Stadium = rectangle + two semicircles at ends
    // Rectangle part: from -length/2 to length/2 in X, -width/2 to width/2 in Y
    // But we need to account for the semicircular ends properly.
    
    // Actually, for a slot of total length L and width W:
    // The straight part has length L - W, and two semicircles of radius W/2 at each end.
    // Total length = (L - W) + 2*(W/2) = L. Correct.
    
    // In local frame (XY plane, extruded along Z):
    // Rectangle: x from -(L-W)/2 to (L-W)/2, y from -W/2 to W/2
    // Left semicircle: center at (-(L-W)/2, 0), radius W/2
    // Right semicircle: center at ((L-W)/2, 0), radius W/2
    
    straight_len = length - width;
    r = width / 2;
    
    // Rectangle part
    translate([0, 0, 0])
        cube([straight_len, width, height], center=true);
    
    // Left semicircle (full cylinder, will be clipped by union with rectangle)
    translate([-(straight_len/2), 0, 0])
        cylinder(r=r, h=height, center=true);
    
    // Right semicircle
    translate([straight_len/2, 0, 0])
        cylinder(r=r, h=height, center=true);
}
