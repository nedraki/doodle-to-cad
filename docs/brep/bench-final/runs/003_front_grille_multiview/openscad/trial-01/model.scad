/* doodle-meta {"version":1,"parameters":{"width":{"label":"Overall width","description":"Changes the body width","unit":"mm","feature":"body_width"},"height":{"label":"Overall height","description":"Changes the body height","unit":"mm","feature":"body_height"},"depth":{"label":"Plate thickness","description":"Changes the plate thickness","unit":"mm","feature":"body_depth"},"slot_count":{"label":"Slot count","description":"Number of vertical slots","unit":"count","feature":"slots"},"slot_width":{"label":"Slot width","description":"Width of each vertical slot","unit":"mm","feature":"slots"},"slot_height":{"label":"Slot height","description":"Height of each vertical slot","unit":"mm","feature":"slots"},"slot_pitch":{"label":"Slot pitch","description":"Center-to-center distance between slots","unit":"mm","feature":"slots"},"headlight_diameter":{"label":"Headlight diameter","description":"Diameter of circular headlight cutouts","unit":"mm","feature":"headlights"},"headlight_x_offset":{"label":"Headlight X offset","description":"Horizontal distance of headlights from center","unit":"mm","feature":"headlights"},"headlight_z_offset":{"label":"Headlight Z offset","description":"Vertical distance of headlights from center","unit":"mm","feature":"headlights"}},"features":{"body_width":{"kind":"dimension","axis":"x","label":"Overall width"},"body_height":{"kind":"dimension","axis":"z","label":"Overall height"},"body_depth":{"kind":"dimension","axis":"y","label":"Plate thickness"},"slots":{"kind":"region","label":"Vertical Slots","min":[{"parameter":"width","scale":0.25,"offset":0},{"parameter":"depth","scale":-0.1,"offset":0},{"parameter":"height","scale":0.13,"offset":0}],"max":[{"parameter":"width","scale":0.75,"offset":0},{"parameter":"depth","scale":1.1,"offset":0},{"parameter":"height","scale":0.74,"offset":0}]},"headlights":{"kind":"region","label":"Headlights","min":[{"parameter":"width","scale":0.09,"offset":0},{"parameter":"depth","scale":-0.1,"offset":0},{"parameter":"height","scale":0.49,"offset":0}],"max":[{"parameter":"width","scale":0.91,"offset":0},{"parameter":"depth","scale":1.1,"offset":0},{"parameter":"height","scale":0.75,"offset":0}]}}} */

// Top-level parameters (allowlist)
width = 126.0;
height = 78.83;
depth = 7.52;
slot_count = 7;
slot_width = 5.1;
slot_height = 48.0;
slot_pitch = 10.0;
headlight_diameter = 20.0;
headlight_x_offset = 41.0;
headlight_z_offset = 10.0;

// Derived constants (not editable)
eps = 0.01;

// Outer profile polygon in XZ plane (normalized from measured view_2)
// Mapped: X = u * width, Z = (1 - v) * height
outer_profile_pts = [
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

module grille_plate() {
    // Positive body: extrude outer profile along Y
    // The polygon is defined in XZ. linear_extrude extrudes along Z by default.
    // We need to extrude along Y.
    // Strategy: Define polygon in XY (where X is width, Y is height), extrude along Z (depth), then rotate to align Z->Y.
    // Or simpler: Define polygon in XZ, rotate the whole object so that the extrusion direction (Z) becomes Y.
    
    // Let's define the polygon in the XY plane (X=width, Y=height) and extrude along Z (depth).
    // Then rotate the result so that the Z-axis (depth) aligns with the Y-axis.
    // Rotation: Rotate -90 degrees around X axis. 
    // Original: X=width, Y=height, Z=depth.
    // After rotate([-90,0,0]): X=width, Y=depth, Z=height.
    // This matches the requirement: Front view is XZ (width x height), Top view is XY (width x depth).
    
    linear_extrude(height = depth) {
        polygon(outer_profile_pts);
    }
}

module slot_cutter(x_center, z_center) {
    // Vertical slot cutter: axis along Y (through the plate)
    // In the rotated frame (after the main body rotation), the plate lies in XZ plane with thickness along Y.
    // Wait, the main body is rotated. The cutters must be in the same coordinate system as the final object.
    // Final object: X=width, Y=depth, Z=height.
    // Slot is a rectangular prism.
    // Dimensions: Width (X) = slot_width, Height (Z) = slot_height, Depth (Y) = depth + 2*eps.
    // Position: Centered at x_center, z_center.
    
    translate([x_center, -eps, z_center]) {
        cube([slot_width, depth + 2*eps, slot_height], center = true);
    }
}

module headlight_cutter(x_center, z_center) {
    // Circular cutter: axis along Y
    // Cylinder axis is Z by default. Rotate 90 deg about X to align with Y.
    translate([x_center, -eps, z_center]) {
        rotate([90, 0, 0]) {
            cylinder(h = depth + 2*eps, d = headlight_diameter, center = true);
        }
    }
}

module grille_assembly() {
    difference() {
        // Positive body
        // Define polygon in XY (X=width, Y=height), extrude along Z (depth), then rotate to align Z->Y.
        // Polygon points are (x, z) from original definition. We treat them as (x, y) for the extrusion.
        // So we use the same points list, but interpret the second coordinate as Y (height) for the polygon definition.
        // Then rotate the extruded solid.
        
        rotate([-90, 0, 0]) {
            linear_extrude(height = depth) {
                polygon(outer_profile_pts);
            }
        }
        
        // Subtract 7 vertical slots
        // Slots are centered vertically in the main body area.
        // The "center" of the slot group in Z is roughly height/2.
        // The slots are arranged along X.
        for (i = [0 : slot_count - 1]) {
            // Center the group of slots horizontally
            // Total width of slots group = (slot_count - 1) * slot_pitch
            // Start X = width/2 - (slot_count - 1) * slot_pitch / 2
            x_pos = width/2 - (slot_count - 1) * slot_pitch / 2 + i * slot_pitch;
            // Z position: centered in the plate height
            z_pos = height / 2;
            slot_cutter(x_pos, z_pos);
        }
        
        // Subtract 2 circular headlights
        // Left headlight
        headlight_cutter(width/2 - headlight_x_offset, height/2 - headlight_z_offset);
        // Right headlight
        headlight_cutter(width/2 + headlight_x_offset, height/2 - headlight_z_offset);
    }
}

// Instantiate the design
grille_assembly();
