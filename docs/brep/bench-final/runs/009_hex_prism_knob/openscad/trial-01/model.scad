/* doodle-meta {"version":1,"parameters":{"circumradius":{"label":"Hexagon Circumradius","description":"Radius of the hexagon's circumscribed circle","unit":"mm","feature":"hex_size"},"extrusion_length":{"label":"Extrusion Length","description":"Length of the prism along the Y axis","unit":"mm","feature":"prism_length"}},"features":{"hex_size":{"kind":"dimension","axis":"x","label":"Hexagon Width"},"prism_length":{"kind":"dimension","axis":"y","label":"Prism Length"}}} */

// Parameters
circumradius = 35;
extrusion_length = 70;

// Derived dimensions for a regular hexagon with point-up orientation (vertices at 90, 150, 210, 270, 330, 30 degrees)
// Width (X) = 2 * R * cos(30) = R * sqrt(3)
// Height (Z) = 2 * R
// The measured width is 70mm, which matches 2 * circumradius if the hexagon is flat-top? 
// Let's check the polygon vertices from the front view.
// Front view polygon (normalized):
// [0.24, 0.04], [0.03, 0.48], [0.22, 0.95], [0.73, 0.97], [0.97, 0.52], [0.74, 0.06]
// This looks like a "point-up" hexagon where the top and bottom are points? 
// No, looking at the coordinates:
// Top edge is between (0.24, 0.04) and (0.74, 0.06) -> roughly flat top?
// Bottom edge is between (0.22, 0.95) and (0.73, 0.97) -> roughly flat bottom?
// Left point is (0.03, 0.48)
// Right point is (0.97, 0.52)
// This is a "flat-top" hexagon (vertices at 0, 60, 120, 180, 240, 300 degrees relative to center, or rather vertices at 0, 60... wait).
// Standard flat-top hexagon has vertices at 0, 60, 120, 180, 240, 300 degrees.
// Width = 2 * R. Height = sqrt(3) * R.
// If Width = 70, then R = 35. Height = 35 * 1.732 = 60.62.
// The derived height is 61.49, which is close to 60.62.
// The derived width is 70.0.
// So the hexagon is flat-top (vertices at 0, 60, 120, 180, 240, 300 degrees in XZ plane).
// Vertices in XZ plane (centered at 0,0):
// (R, 0), (R/2, R*sqrt(3)/2), (-R/2, R*sqrt(3)/2), (-R, 0), (-R/2, -R*sqrt(3)/2), (R/2, -R*sqrt(3)/2)
// Wait, standard angle 0 is +X.
// Vertex 0: (R, 0) -> Right point
// Vertex 1: (R/2, R*sqrt(3)/2) -> Top Right
// Vertex 2: (-R/2, R*sqrt(3)/2) -> Top Left
// Vertex 3: (-R, 0) -> Left point
// Vertex 4: (-R/2, -R*sqrt(3)/2) -> Bottom Left
// Vertex 5: (R/2, -R*sqrt(3)/2) -> Bottom Right
// This matches the "flat-top" description where the top and bottom are flat edges? 
// No, if vertices are at 0, 60, 120... the edges are between them.
// Edge between 60 and 120 is horizontal at top. Yes, flat-top.
// Width (X extent) = 2 * R = 70.
// Height (Z extent) = sqrt(3) * R = 60.62.
// The spec says max_width 70, max_height 61.49. This is consistent.

// The prism is extruded along Y.
// The object sits on the build plate (Z=0).
// So we need to shift the hexagon up by Height/2.

module hex_prism_handle() {
    // Calculate hexagon height
    hex_height = circumradius * sqrt(3);
    
    // Define the hexagon polygon in XZ plane (Y=0)
    // Vertices for a flat-top hexagon centered at (0,0) in XZ
    // Angles: 0, 60, 120, 180, 240, 300
    // x = R * cos(theta), z = R * sin(theta)
    
    // We will create the polygon in the XZ plane and extrude along Y.
    // However, OpenSCAD's linear_extrude extrudes along Z by default.
    // To extrude along Y, we can rotate the polygon or use rotate_extrude? 
    // No, linear_extrude is for 2D polygons. 
    // Strategy: Create the hexagon in the XY plane (standard for linear_extrude), 
    // extrude along Z, then rotate the whole thing so the extrusion axis is Y.
    
    // Hexagon in XY plane (flat-top relative to X axis? No, let's stick to the shape).
    // If we define the hexagon in XY such that its "width" is along X and "height" along Y,
    // and extrude along Z, then rotate 90 deg around X to make Z->Y.
    
    // Let's define the hexagon in the XY plane first.
    // We want the final object to have:
    // X: Width (70mm)
    // Y: Depth (70mm) - this is the extrusion length
    // Z: Height (60.62mm)
    
    // If we extrude along Z, the "height" of the prism is the extrusion length.
    // So we want the extrusion length to be along Y.
    // So we should define the hexagon in the XZ plane? No, linear_extrude takes a 2D polygon in XY.
    
    // Approach:
    // 1. Define hexagon in XY plane.
    //    Let's say the hexagon's "width" (2R) is along X.
    //    The hexagon's "height" (sqrt(3)R) is along Y.
    // 2. Extrude along Z by extrusion_length.
    // 3. Rotate the result so that the Z-axis (extrusion direction) becomes the Y-axis.
    //    Rotate -90 degrees around X axis: Z -> Y, Y -> -Z.
    //    This would put the extrusion along Y.
    //    The original Y (hexagon height) becomes -Z.
    //    The original X (hexagon width) stays X.
    
    // Let's verify the orientation.
    // Original Hexagon in XY:
    // Vertices at angles 0, 60, 120, 180, 240, 300.
    // (R, 0), (R/2, R*sqrt(3)/2), ...
    // Width along X: 2R. Height along Y: sqrt(3)R.
    
    // After Rotate(-90, X):
    // X stays X.
    // Y becomes -Z.
    // Z becomes Y.
    
    // So the extrusion (originally Z) is now along Y. Correct.
    // The hexagon height (originally Y) is now along -Z.
    // The hexagon width (originally X) is along X.
    
    // We need the object to sit on Z=0.
    // The hexagon in XY is centered at (0,0).
    // After rotation, the hexagon is centered at (0,0,0) in XZ? 
    // The original Y range was [-sqrt(3)R/2, sqrt(3)R/2].
    // After rotation, this becomes Z range [-sqrt(3)R/2, sqrt(3)R/2] (with sign flip).
    // So the object is centered at Z=0.
    // We need to translate it up by sqrt(3)R/2 to sit on Z=0.
    
    // Let's build it.
    
    translate([0, 0, hex_height / 2]) {
        rotate([-90, 0, 0]) {
            linear_extrude(height = extrusion_length, center = true) {
                hexagon_polygon(circumradius);
            }
        }
    }
}

module hexagon_polygon(r) {
    // Flat-top hexagon in XY plane
    // Vertices at 0, 60, 120, 180, 240, 300 degrees
    polygon(
        points = [
            [r, 0],
            [r/2, r*sqrt(3)/2],
            [-r/2, r*sqrt(3)/2],
            [-r, 0],
            [-r/2, -r*sqrt(3)/2],
            [r/2, -r*sqrt(3)/2]
        ]
    );
}

hex_prism_handle();
