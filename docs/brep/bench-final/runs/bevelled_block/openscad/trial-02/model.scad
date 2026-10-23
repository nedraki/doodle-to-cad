/* doodle-meta {"version":1,"parameters":{"width":{"label":"Overall width","description":"Changes the body width along X","unit":"mm","feature":"body_width"},"depth":{"label":"Overall depth","description":"Changes the body depth along Y","unit":"mm","feature":"body_depth"},"height":{"label":"Overall height","description":"Changes the body height along Z","unit":"mm","feature":"body_height"},"chamfer_size":{"label":"Chamfer size","description":"Size of the 45-degree chamfer on all edges","unit":"mm","feature":"chamfer"}},"features":{"body_width":{"kind":"dimension","axis":"x","label":"Overall width"},"body_depth":{"kind":"dimension","axis":"y","label":"Overall depth"},"body_height":{"kind":"dimension","axis":"z","label":"Overall height"},"chamfer":{"kind":"region","label":"Chamfered edges","min":[0,0,0],"max":[{"parameter":"width","scale":1,"offset":0},{"parameter":"depth","scale":1,"offset":0},{"parameter":"height","scale":1,"offset":0}]}}} */

// Parameters
width = 80.0;
depth = 43.09;
height = 5.69;
chamfer_size = 2.0;

// Derived constants
eps = 0.01;

// Module for the base block with chamfered vertical edges (XY profile extruded)
// The XY profile is a rectangle with chamfered corners.
module block_body() {
    // Create the 2D profile in XY plane
    // Rectangle from (0,0) to (width, depth)
    // Chamfer corners by chamfer_size
    
    // We can use hull or minkowski, but explicit polygon is cleaner for chamfers.
    // Points for the polygon (counter-clockwise):
    // Bottom-Left: (chamfer, 0) -> (0, chamfer)
    // Bottom-Right: (width-chamfer, 0) -> (width, chamfer)
    // Top-Right: (width, depth-chamfer) -> (width-chamfer, depth)
    // Top-Left: (chamfer, depth) -> (0, depth-chamfer)
    
    polygon([
        [chamfer_size, 0],
        [width - chamfer_size, 0],
        [width, chamfer_size],
        [width, depth - chamfer_size],
        [width - chamfer_size, depth],
        [chamfer_size, depth],
        [0, depth - chamfer_size],
        [0, chamfer_size]
    ]);
}

// Module for the chamfer cutters on top and bottom faces
// These are prisms that cut the horizontal edges.
// A 45-degree chamfer of size 'c' on a horizontal edge can be modeled as 
// subtracting a triangular prism from the corners.
// However, since we already chamfered the vertical edges, the "horizontal" edges 
// are the ones running along X (front/back) and Y (left/right) at Z=0 and Z=height.
// The intersection of vertical and horizontal chamfers creates complex corner geometry.
// A robust way to chamfer ALL edges of a box is to use a Minkowski difference 
// or a hull of scaled shapes, but for simple 45-degree chamfers on a rectangular block,
// we can subtract 4 prisms for the top edges and 4 for the bottom edges, 
// BUT the vertical chamfers already removed the corners.
// Actually, the standard way to chamfer all edges of a rectangular block is:
// 1. Start with a box.
// 2. Subtract 4 vertical prisms for the vertical edges (done in block_body).
// 3. Subtract 4 horizontal prisms for the top edges (along X and Y).
// 4. Subtract 4 horizontal prisms for the bottom edges (along X and Y).
// The vertical chamfers create new "edges" at the top and bottom of the vertical chamfers.
// The horizontal chamfers must intersect these.

// Let's define the cutters for the top and bottom horizontal edges.
// Top edges are at Z = height.
// Bottom edges are at Z = 0.

// Cutter for an edge along X at Y=0 (Front) and Z=height (Top)
// This is a triangular prism running along X.
// The triangle is in the YZ plane.
// Vertices of the triangle to remove: (0, height), (chamfer, height), (0, height-chamfer)
// Wait, the block body already has the vertical chamfer.
// The vertical chamfer at the front-left corner (X=0, Y=0) removes material near (0,0).
// The top-front edge runs along X at Y=0, Z=height.
// The chamfer on this edge removes a triangle in the YZ plane at each X.
// Triangle vertices: (Y=0, Z=height), (Y=chamfer, Z=height), (Y=0, Z=height-chamfer).
// This prism extends along X from 0 to width.

module top_front_chamfer_cutter() {
    translate([0, 0, height])
    rotate([0, 0, 0]) // Axis along X
    // Create a triangular prism along X
    // The triangle is in YZ. 
    // We need to cut the corner at Y=0, Z=height.
    // The cut is defined by the plane Y + Z = height + chamfer? No.
    // The chamfer connects (0, height-chamfer) to (chamfer, height).
    // So we remove the triangle with vertices (0, height), (chamfer, height), (0, height-chamfer).
    // This triangle is in the YZ plane.
    // Extrude along X.
    polygon([
        [0, 0], // Relative to (Y=0, Z=height) -> (0,0) is (0, height)
        [chamfer_size, 0], // (chamfer, height)
        [0, -chamfer_size] // (0, height-chamfer)
    ]);
    // Extrude along X
    // We need to rotate the polygon so it lies in YZ and extrudes along X.
    // polygon() creates in XY. 
    // So we create in XY, then rotate to YZ.
    // XY points: (0,0), (c,0), (0,-c).
    // Rotate -90 around X? No.
    // Let's just use a cube and rotate it, or define the polygon carefully.
    // Polygon in XY: (0,0), (c,0), (0,-c).
    // Rotate 90 deg around Y to put it in ZY? 
    // Let's use a simpler approach: subtract a rotated cube.
    // A 45 deg chamfer is a cube rotated 45 deg around the edge axis.
    // Edge along X. Rotate around X.
    // Cube centered at (0, 0, height) with size (width, c*sqrt(2), c*sqrt(2))?
    // No, standard chamfer cutter:
    // Cube of size (width, chamfer, chamfer) at corner (0,0,height).
    // Rotate 45 deg around X axis.
    // This cuts the corner.
    translate([0, 0, height])
    rotate([45, 0, 0])
    translate([-eps, -eps, -eps])
    cube([width + 2*eps, chamfer_size + eps, chamfer_size + eps]);
}

module top_back_chamfer_cutter() {
    translate([0, depth, height])
    rotate([45, 0, 0])
    translate([-eps, -eps, -eps])
    cube([width + 2*eps, chamfer_size + eps, chamfer_size + eps]);
}

module top_left_chamfer_cutter() {
    // Edge along Y at X=0, Z=height
    translate([0, 0, height])
    rotate([0, 45, 0])
    translate([-eps, -eps, -eps])
    cube([chamfer_size + eps, depth + 2*eps, chamfer_size + eps]);
}

module top_right_chamfer_cutter() {
    // Edge along Y at X=width, Z=height
    translate([width, 0, height])
    rotate([0, 45, 0])
    translate([-eps, -eps, -eps])
    cube([chamfer_size + eps, depth + 2*eps, chamfer_size + eps]);
}

module bottom_front_chamfer_cutter() {
    translate([0, 0, 0])
    rotate([-45, 0, 0])
    translate([-eps, -eps, -eps])
    cube([width + 2*eps, chamfer_size + eps, chamfer_size + eps]);
}

module bottom_back_chamfer_cutter() {
    translate([0, depth, 0])
    rotate([-45, 0, 0])
    translate([-eps, -eps, -eps])
    cube([width + 2*eps, chamfer_size + eps, chamfer_size + eps]);
}

module bottom_left_chamfer_cutter() {
    translate([0, 0, 0])
    rotate([0, -45, 0])
    translate([-eps, -eps, -eps])
    cube([chamfer_size + eps, depth + 2*eps, chamfer_size + eps]);
}

module bottom_right_chamfer_cutter() {
    translate([width, 0, 0])
    rotate([0, -45, 0])
    translate([-eps, -eps, -eps])
    cube([chamfer_size + eps, depth + 2*eps, chamfer_size + eps]);
}

// Main design
difference() {
    // 1. Base body with vertical chamfers
    linear_extrude(height)
    block_body();
    
    // 2. Subtract horizontal chamfers (Top)
    top_front_chamfer_cutter();
    top_back_chamfer_cutter();
    top_left_chamfer_cutter();
    top_right_chamfer_cutter();
    
    // 3. Subtract horizontal chamfers (Bottom)
    bottom_front_chamfer_cutter();
    bottom_back_chamfer_cutter();
    bottom_left_chamfer_cutter();
    bottom_right_chamfer_cutter();
}
