/* doodle-meta {"version":1,"parameters":{"width":{"label":"Overall width","description":"Changes the body width","unit":"mm","feature":"body_width"},"depth":{"label":"Overall depth","description":"Changes the body depth","unit":"mm","feature":"body_depth"},"height":{"label":"Overall height","description":"Changes the body height","unit":"mm","feature":"body_height"},"thickness":{"label":"Wall thickness","description":"Thickness of the L-shape walls","unit":"mm","feature":"wall_thickness"}},"features":{"body_width":{"kind":"dimension","axis":"x","label":"Overall width"},"body_depth":{"kind":"dimension","axis":"y","label":"Overall depth"},"body_height":{"kind":"dimension","axis":"z","label":"Overall height"},"wall_thickness":{"kind":"dimension","axis":"z","label":"Wall thickness"}}} */

// Parameters
width = 73.11;
depth = 47.78;
height = 100.0;
thickness = 10.0; // Estimated from aspect ratio

// Derived dimensions
base_height = thickness;
backplate_width = thickness;
front_face_width = width;
front_face_height = height;

// Cutout parameters (derived from front view proportions)
// View 2 (Front) mapping: X = u * width, Z = (1-v) * height
// Outer profile bbox in view: [0.0242, 0.0111, 0.9483, 0.9778] -> Width ~0.924, Height ~0.967
// Let's normalize cutout positions relative to the outer profile bounds for robustness.
// Outer profile in view coords:
// u_min = 0.0242, u_max = 0.9665 (approx from polygon) -> span_u = 0.9423
// v_min = 0.0111, v_max = 0.9823 (approx from polygon) -> span_v = 0.9712
// Actual CAD width/height correspond to these spans.
// However, the spec says "measured ink spans x authoritative max dimension".
// The outer profile polygon vertices are roughly:
// (0.0302, 0.0133), (0.0302, 0.9823), (0.9634, 0.98), (0.9665, 0.0177)
// This is a rectangle covering almost the whole view.
// Let's assume the outer profile defines the full width and height of the front face.
// So u=0 maps to X=0, u=1 maps to X=width. v=0 maps to Z=height, v=1 maps to Z=0.

// Cutout 1 (contour_8): Top Left Square-ish
// Center: (0.2689, 0.1968)
// Size: (0.3069, 0.146)
// X_center = 0.2689 * width
// Z_center = (1 - 0.1968) * height
// w = 0.3069 * width
// h = 0.146 * height

// Cutout 2 (contour_10): Top Right Slot
// Center: (0.5577, 0.1968)
// Size: (0.1245, 0.3661)
// X_center = 0.5577 * width
// Z_center = (1 - 0.1968) * height
// w = 0.1245 * width
// h = 0.3661 * height

// Cutout 3 (contour_6): Bottom Right Slot
// Center: (0.7734, 0.7024)
// Size: (0.1245, 0.4447)
// X_center = 0.7734 * width
// Z_center = (1 - 0.7024) * height
// w = 0.1245 * width
// h = 0.4447 * height

// Cutout 4 (contour_4): Bottom Left Slot
// Center: (0.1822, 0.7024)
// Size: (0.1245, 0.3661)
// X_center = 0.1822 * width
// Z_center = (1 - 0.7024) * height
// w = 0.1245 * width
// h = 0.3661 * height

// Helper module for rectangular cutout through Y axis
module rect_cutout(x, z, w, h, depth_cut) {
    // Centered at x, z in XZ plane.
    // Cut along Y.
    // The backplate is at Y=0 to Y=thickness.
    // We need to cut through the backplate.
    // The cutout should be centered on the backplate thickness? 
    // Usually decorative cutouts go through the visible face.
    // The front face is at Y=0 (if we orient the L such that the vertical part is at Y=0..thickness).
    // Wait, let's define the L-shape orientation carefully.
    
    // Right View (View 1) shows the L-profile.
    // View 1 is Right View. u -> +Y, v -> -Z.
    // Polygon: (0.0462, 0.0157) -> (0.0462, 0.9822) -> (0.9394, 0.9866) -> (0.9441, 0.8594) -> (0.3024, 0.855) -> (0.3116, 0.0157)
    // This looks like an L-shape.
    // Let's map it to Y-Z.
    // u=0 is Y=0 (Front of part? No, Right view looks down X. u is Y. u=0 is left of view. 
    // Standard Right View: Looking from +X towards -X. 
    // The "left" of the right view corresponds to the FRONT of the object (Y=0) if we assume standard third angle?
    // Actually, in third angle projection, the Right View is placed to the right of the Front View.
    // The Right View shows the object from the right side.
    // The horizontal axis of the Right View is Depth (Y).
    // Usually, the left side of the Right View corresponds to the Front of the object (Y=0) and the right side to the Back (Y=depth).
    // Let's verify with the polygon.
    // The L-shape has a vertical backplate and a horizontal base.
    // The vertical part is usually at the back (Y=depth) or front?
    // A bookend usually has the vertical part at the back to support books, and the base extends forward.
    // So the vertical wall is at Y=depth-thickness to Y=depth? Or Y=0 to Y=thickness?
    // If the vertical wall is at the back, it's at high Y.
    // Let's look at the polygon in View 1 (Right View).
    // Points:
    // (0.0462, 0.0157) -> Top Left
    // (0.0462, 0.9822) -> Bottom Left
    // (0.9394, 0.9866) -> Bottom Right
    // (0.9441, 0.8594) -> Step Up on Right
    // (0.3024, 0.855) -> Step Left
    // (0.3116, 0.0157) -> Top Right (inner corner)
    
    // This shape is an inverted L? Or standard L?
    // Left side (u~0.05) goes from v~0.01 to v~0.98. This is a tall vertical bar on the LEFT of the view.
    // Bottom side (v~0.98) goes from u~0.05 to u~0.94. This is a wide horizontal bar at the BOTTOM.
    // The "cutout" of the L is at the top right.
    // So the material is on the Left and Bottom of the Right View.
    // If Left of Right View = Front (Y=0), then the vertical wall is at the FRONT (Y=0..thickness).
    // And the base extends to the BACK (Y=0..depth).
    // This is a "front-facing" bookend? Or maybe the view is mirrored?
    // Let's re-read standard mapping.
    // Right View: u maps to +Y.
    // If u=0 is Y=0, then the vertical wall is at Y=0.
    // This means the vertical wall is at the FRONT.
    // The base extends from Y=0 to Y=depth.
    // This is a valid L-shape.
    
    // Now, where are the cutouts?
    // The cutouts are on the "Front Face".
    // If the vertical wall is at Y=0..thickness, the "Front Face" visible from the front (looking down Y) is the face at Y=0?
    // Or is the "Front Face" the large vertical surface?
    // The Front View (View 2) shows the cutouts.
    // The Front View looks down Y.
    // If the vertical wall is at Y=0..thickness, looking from -Y (Front) we see the face at Y=0.
    // So the cutouts go through the wall at Y=0..thickness.
    
    // Let's construct the L-shape:
    // Vertical part: X=0..width, Y=0..thickness, Z=0..height.
    // Horizontal part: X=0..width, Y=0..depth, Z=0..thickness.
    // This forms an L with the corner at (0,0,0).
    // The vertical wall is at the front (Y=0).
    // The base extends backward (Y>0).
    
    // Cutouts are in the vertical wall (Y=0..thickness).
    // They are through-holes along Y.
    
    translate([x, -1, z]) 
        cube([w, depth_cut, h], center=true);
}

// Main Body
difference() {
    // Union of L-shape
    union() {
        // Vertical Backplate (actually Front Plate based on Right View analysis)
        // X: 0 to width
        // Y: 0 to thickness
        // Z: 0 to height
        cube([width, thickness, height]);
        
        // Horizontal Base
        // X: 0 to width
        // Y: 0 to depth
        // Z: 0 to thickness
        // Note: The vertical part already covers Y:0..thickness, Z:0..thickness.
        // So we just add the rest of the base.
        // To avoid overlap issues in CSG (though union handles it), we can just union the two boxes.
        cube([width, depth, thickness]);
    }
    
    // Cutouts
    // All cutouts go through the vertical wall (Y=0..thickness).
    // We need to cut along Y.
    // The cutters should span Y from -eps to thickness+eps.
    
    // Cutout 1: Top Left
    // Center X = 0.2689 * width
    // Center Z = (1 - 0.1968) * height
    // Width = 0.3069 * width
    // Height = 0.146 * height
    c1_x = 0.2689 * width;
    c1_z = (1 - 0.1968) * height;
    c1_w = 0.3069 * width;
    c1_h = 0.146 * height;
    
    translate([c1_x, thickness/2, c1_z])
        cube([c1_w, thickness + 2, c1_h], center=true);
        
    // Cutout 2: Top Right Slot
    // Center X = 0.5577 * width
    // Center Z = (1 - 0.1968) * height
    // Width = 0.1245 * width
    // Height = 0.3661 * height
    c2_x = 0.5577 * width;
    c2_z = (1 - 0.1968) * height;
    c2_w = 0.1245 * width;
    c2_h = 0.3661 * height;
    
    translate([c2_x, thickness/2, c2_z])
        cube([c2_w, thickness + 2, c2_h], center=true);
        
    // Cutout 3: Bottom Right Slot
    // Center X = 0.7734 * width
    // Center Z = (1 - 0.7024) * height
    // Width = 0.1245 * width
    // Height = 0.4447 * height
    c3_x = 0.7734 * width;
    c3_z = (1 - 0.7024) * height;
    c3_w = 0.1245 * width;
    c3_h = 0.4447 * height;
    
    translate([c3_x, thickness/2, c3_z])
        cube([c3_w, thickness + 2, c3_h], center=true);
        
    // Cutout 4: Bottom Left Slot
    // Center X = 0.1822 * width
    // Center Z = (1 - 0.7024) * height
    // Width = 0.1245 * width
    // Height = 0.3661 * height
    c4_x = 0.1822 * width;
    c4_z = (1 - 0.7024) * height;
    c4_w = 0.1245 * width;
    c4_h = 0.3661 * height;
    
    translate([c4_x, thickness/2, c4_z])
        cube([c4_w, thickness + 2, c4_h], center=true);
}
