/* doodle-meta {"version":1,"parameters":{"width":{"label":"Overall width","description":"Changes the body width","unit":"mm","feature":"body_width"},"height":{"label":"Overall height","description":"Changes the body height","unit":"mm","feature":"body_height"},"depth":{"label":"Overall depth","description":"Changes the body depth","unit":"mm","feature":"body_depth"},"slot_count":{"label":"Grille slot count","description":"Number of vertical grille slots","unit":"count","feature":"grille_slots"},"slot_width":{"label":"Grille slot width","description":"Width of each vertical grille slot","unit":"mm","feature":"grille_slots"},"slot_height":{"label":"Grille slot height","description":"Height of each vertical grille slot","unit":"mm","feature":"grille_slots"},"headlight_diameter":{"label":"Headlight diameter","description":"Diameter of the circular headlight cutouts","unit":"mm","feature":"headlights"}},"features":{"body_width":{"kind":"dimension","axis":"x","label":"Overall width"},"body_height":{"kind":"dimension","axis":"z","label":"Overall height"},"body_depth":{"kind":"dimension","axis":"y","label":"Overall depth"},"grille_slots":{"kind":"region","label":"Grille slots","min":[{"parameter":"width","scale":0.2895},{"parameter":"depth","scale":0,"offset":0},{"parameter":"height","scale":0.1324}],"max":[{"parameter":"width","scale":0.7027},{"parameter":"depth","scale":1,"offset":0},{"parameter":"height","scale":0.7417}]},"headlights":{"kind":"region","label":"Headlights","min":[{"parameter":"width","scale":0.0927},{"parameter":"depth","scale":0,"offset":0},{"parameter":"height","scale":0.4893}],"max":[{"parameter":"width","scale":0.9035},{"parameter":"depth","scale":1,"offset":0},{"parameter":"height","scale":0.7509}]}}} */

// Parameters
width = 120.0;
height = 75.07;
depth = 7.16;
slot_count = 7;
slot_width = 4.86;
slot_height = 45.74;
headlight_diameter = 19.69;

// Derived constants
eps = 0.1;

// Front view outer profile polygon (normalized u, v)
// Mapped to CAD: X = u * width, Z = (1 - v) * height
front_profile_norm = [
    [0.0097, 0.5785],
    [0.0135, 0.757],
    [0.0521, 0.9202],
    [0.2027, 0.9787],
    [0.8127, 0.9693],
    [0.9267, 0.9417],
    [0.9575, 0.8863],
    [0.9865, 0.7385],
    [0.9768, 0.5509],
    [0.8359, 0.3478],
    [0.8243, 0.0954],
    [0.6524, 0.0185],
    [0.3609, 0.0185],
    [0.1833, 0.0954],
    [0.1601, 0.16],
    [0.1622, 0.3509],
    [0.0213, 0.5354]
];

// Convert normalized front profile to CAD coordinates (X, Z)
function front_profile_cad(p) = [p[0] * width, (1 - p[1]) * height];

// Generate CAD polygon points
front_poly_cad = [for (p = front_profile_norm) front_profile_cad(p)];

// Top view outer profile polygon (normalized u, v)
// Mapped to CAD: X = u * width, Y = (1 - v) * depth
top_profile_norm = [
    [0.0096, 0.2255],
    [0.0115, 0.7086],
    [0.8944, 0.8064],
    [0.9732, 0.7725],
    [0.9866, 0.5469],
    [0.9789, 0.2255],
    [0.9501, 0.1597]
];

// Convert normalized top profile to CAD coordinates (X, Y)
function top_profile_cad(p) = [p[0] * width, (1 - p[1]) * depth];

// Generate CAD polygon points for top view
top_poly_cad = [for (p = top_profile_norm) top_profile_cad(p)];

// Headlight centers in CAD coordinates
// Left headlight: center_view_normalized [0.1747, 0.437]
// X = 0.1747 * width, Z = (1 - 0.437) * height
headlight_left_x = 0.1747 * width;
headlight_left_z = (1 - 0.437) * height;

// Right headlight: center_view_normalized [0.8253, 0.437]
// X = 0.8253 * width, Z = (1 - 0.437) * height
headlight_right_x = 0.8253 * width;
headlight_right_z = (1 - 0.437) * height;

// Grille slots parameters
// Slots are centered vertically in the front view.
// Center v = 0.437 -> Z_center = (1 - 0.437) * height
// Slot height is slot_height.
// Slot width is slot_width.
// Slots are distributed horizontally.
// The slots span from u=0.2895 to u=0.7027 roughly (based on bounding boxes of contours).
// Let's calculate the start and end X for the slot array.
// Leftmost slot center u ~ 0.3098, Rightmost slot center u ~ 0.6891.
// Spacing between centers: (0.6891 - 0.3098) / (7 - 1) = 0.3793 / 6 = 0.063216
// First slot center X = 0.3098 * width
// Last slot center X = 0.6891 * width

slot_start_u = 0.3098;
slot_end_u = 0.6891;
slot_pitch_u = (slot_end_u - slot_start_u) / (slot_count - 1);

// Module for the main body
module grille_body() {
    // Create the 3D body by extruding the front profile along Y
    // The front profile is in XZ plane. Extrude along Y.
    // We need to create a polygon in XZ and extrude it along Y.
    // However, OpenSCAD's linear_extrude works on XY plane by default.
    // So we create the polygon in XY (where X is width, Y is height), then rotate it to XZ.
    
    // Create polygon in XY plane (X=width, Y=height)
    // Points are (X, Z) from front_profile_cad
    // We need to map (X, Z) to (X, Y) for linear_extrude, then rotate.
    // Actually, simpler: define polygon in XZ directly by swapping Y/Z in the polygon definition?
    // No, polygon() takes 2D points.
    // Let's define the polygon in XZ coordinates as (x, z).
    // Then use linear_extrude with convexity and rotate the whole thing?
    // Or better: define polygon in XY where Y represents Z.
    // Then rotate([90, 0, 0]) to put it in XZ plane.
    
    // Points for polygon in XY (X, Y=Z)
    poly_pts = [for (p = front_poly_cad) [p[0], p[1]]];
    
    // Extrude along Z (which will become Y after rotation)
    // Wait, if I extrude along Z, the thickness is in Z.
    // I want thickness in Y.
    // So:
    // 1. Define polygon in XZ (x, z).
    // 2. linear_extrude along Y? No, linear_extrude is always along Z.
    // 3. So define polygon in XY (x, y=z).
    // 4. linear_extrude along Z (thickness).
    // 5. Rotate([90, 0, 0]) to swap Y and Z.
    //    Original: X=width, Y=height, Z=thickness.
    //    After rotate([90,0,0]): X=width, Y=-thickness, Z=height.
    //    This puts the face in XZ plane, thickness in Y.
    
    translate([0, 0, 0])
    rotate([90, 0, 0])
    linear_extrude(height = depth, convexity = 10)
    polygon(points = poly_pts);
}

// Module for headlight cutouts
module headlight_cutouts() {
    // Left headlight
    // Cylinder axis along Y.
    // Position: X = headlight_left_x, Z = headlight_left_z, Y = depth/2 (centered)
    // Rotate([90, 0, 0]) makes cylinder axis along Y.
    // Center the cylinder in Y.
    translate([headlight_left_x, depth/2, headlight_left_z])
    rotate([90, 0, 0])
    cylinder(h = depth + 2*eps, d = headlight_diameter, center = true);

    // Right headlight
    translate([headlight_right_x, depth/2, headlight_right_z])
    rotate([90, 0, 0])
    cylinder(h = depth + 2*eps, d = headlight_diameter, center = true);
}

// Module for grille slot cutouts
module grille_slot_cutouts() {
    // Slots are vertical rectangles in XZ plane, cut along Y.
    // Use cubes.
    // Cube dimensions: X=slot_width, Y=depth+2*eps, Z=slot_height.
    // Centered in Y.
    // Positioned at specific X and Z.
    
    // Z center for slots: (1 - 0.437) * height
    slot_z_center = (1 - 0.437) * height;
    
    for (i = [0 : slot_count - 1]) {
        // Calculate X center for each slot
        slot_u_center = slot_start_u + i * slot_pitch_u;
        slot_x_center = slot_u_center * width;
        
        translate([slot_x_center, depth/2, slot_z_center])
        cube([slot_width, depth + 2*eps, slot_height], center = true);
    }
}

// Main assembly
difference() {
    grille_body();
    headlight_cutouts();
    grille_slot_cutouts();
}
