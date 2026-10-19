/* doodle-meta {"version":1,"parameters":{"width":{"label":"Overall width","description":"Changes the body width","unit":"mm","feature":"body_width"},"depth":{"label":"Overall depth","description":"Changes the body depth","unit":"mm","feature":"body_depth"},"height":{"label":"Overall height","description":"Changes the body height","unit":"mm","feature":"body_height"},"hole_diameter":{"label":"Mounting hole diameter","description":"Diameter of the mounting holes","unit":"mm","feature":"mounting_holes"}},"features":{"body_width":{"kind":"dimension","axis":"x","label":"Overall width"},"body_depth":{"kind":"dimension","axis":"y","label":"Overall depth"},"body_height":{"kind":"dimension","axis":"z","label":"Overall height"},"mounting_holes":{"kind":"region","label":"Mounting holes","min":[{"parameter":"width","scale":0.15,"offset":0},{"parameter":"depth","scale":0.1,"offset":0},0],"max":[{"parameter":"width","scale":0.9,"offset":0},{"parameter":"depth","scale":0.9,"offset":0},{"parameter":"height","scale":1.0,"offset":0}]}}} */

// Parameters
width = 55.55;
depth = 60.0;
height = 27.5;
hole_diameter = 5.0;

// Derived parameters
eps = 0.01;
base_thickness = 5.0; // Inferred from right view height proportion

// Modules
module motor_holder_body() {
    // The body is defined by the front view (XZ plane) extruded along Y.
    // Front view polygon points (normalized u, v) -> (X, Z)
    // u maps to +X, v maps to -Z (so Z = (1-v)*height)
    
    // Points from view_3 (front):
    // [0.9597, 0.0737] -> X=0.9597*w, Z=(1-0.0737)*h
    // [0.7467, 0.0655] -> X=0.7467*w, Z=(1-0.0655)*h
    // [0.0522, 0.5287] -> X=0.0522*w, Z=(1-0.5287)*h
    // [0.0358, 0.9107] -> X=0.0358*w, Z=(1-0.9107)*h
    // [0.9396, 0.9026] -> X=0.9396*w, Z=(1-0.9026)*h
    
    // Note: The front view shows a profile that is roughly rectangular with an angled top.
    // The bottom is flat (Z=0). The left side is vertical. The right side is vertical.
    // The top slopes down from right to left? 
    // Let's re-evaluate the front view polygon.
    // It looks like a block with a slanted top surface.
    // The polygon vertices in view_3:
    // 1. (0.9597, 0.0737) -> Top Right
    // 2. (0.7467, 0.0655) -> Top Middle-Right
    // 3. (0.0522, 0.5287) -> Middle Left (Start of slope?)
    // 4. (0.0358, 0.9107) -> Bottom Left
    // 5. (0.9396, 0.9026) -> Bottom Right
    
    // This defines the X-Z profile. We extrude this along Y (depth).
    // However, the top view (view_1) shows an L-shape with a curved cutout.
    // The construction plan says "extrude L-shaped outline with curved cutout from top view".
    // But the front view defines the height profile.
    // Usually, for a motor holder, the base is flat and the top is angled.
    // Let's assume the base is a rectangular block of height 'base_thickness' and the top part is angled.
    // Or, simpler: The front view defines the silhouette. The top view defines the footprint.
    // If we extrude the front view along Y, we get a prism.
    // Then we subtract the curved cutout from the top view (which cuts along Z).
    
    // Let's construct the base prism from the front view.
    // The front view polygon is closed.
    // We need to map these to 3D coordinates.
    // The prism extends from Y=0 to Y=depth.
    
    polygon_points = [
        [0.9597 * width, (1 - 0.0737) * height],
        [0.7467 * width, (1 - 0.0655) * height],
        [0.0522 * width, (1 - 0.5287) * height],
        [0.0358 * width, (1 - 0.9107) * height],
        [0.9396 * width, (1 - 0.9026) * height]
    ];
    
    // Extrude the polygon along Y
    linear_extrude(height = depth) {
        polygon(polygon_points);
    }
}

module curved_cutout() {
    // The curved cutout is visible in the top view (view_1).
    // It is on the left side.
    // The top view shows an L-shape. The "curved cutout" is likely the inner corner of the L or a specific indentation.
    // Looking at view_1 outer profile:
    // It has a large indentation on the left.
    // The "curved cutout" feature description says "large curved indentation on the left side".
    // In the top view, the left side (low X) has a curve.
    // Let's approximate this with a cylinder subtracted from the left side.
    // The cutout seems to go through the entire height? Or just the top?
    // "Curved Cutout ... likely for motor clearance".
    // If it's for motor clearance, it might be a vertical cutout.
    // Let's assume it's a vertical cylinder cutout on the left side.
    // Center of the curve in top view:
    // The leftmost part of the outer profile is around u=0.03-0.05.
    // The curve seems to be centered around X=0, Y=depth/2?
    // Let's look at the "L-shape".
    // The top view outer profile has vertices that suggest an L.
    // Let's create a cylinder that cuts into the left side.
    // Radius estimated from the "curved" nature.
    // Let's place a cylinder at X=0, Y=depth/2 with a radius that creates the indentation.
    // From the top view, the indentation is significant.
    // Let's use a radius of 15mm.
    
    translate([0, depth/2, -eps]) {
        cylinder(h = height + 2*eps, r = 15, center = false);
    }
}

module mounting_holes() {
    // Two mounting holes.
    // From top view (view_1):
    // Hole 1 (contour_11): center (0.8259, 0.1367)
    // Hole 2 (contour_9): center (0.1581, 0.7412)
    
    // Mapping to CAD (X, Y):
    // X = u * width
    // Y = (1 - v) * depth
    
    // Hole 1:
    // X1 = 0.8259 * width
    // Y1 = (1 - 0.1367) * depth = 0.8633 * depth
    
    // Hole 2:
    // X2 = 0.1581 * width
    // Y2 = (1 - 0.7412) * depth = 0.2588 * depth
    
    // These holes go through the entire height (Z).
    
    // Hole 1
    translate([0.8259 * width, 0.8633 * depth, -eps]) {
        cylinder(h = height + 2*eps, d = hole_diameter, center = false);
    }
    
    // Hole 2
    translate([0.1581 * width, 0.2588 * depth, -eps]) {
        cylinder(h = height + 2*eps, d = hole_diameter, center = false);
    }
}

// Main Design
difference() {
    // 1. Base Body
    motor_holder_body();
    
    // 2. Subtract Curved Cutout
    curved_cutout();
    
    // 3. Subtract Mounting Holes
    mounting_holes();
}
