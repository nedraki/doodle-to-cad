/* doodle-meta {"version":1,"parameters":{"width":{"label":"Overall width","description":"Changes the body width along X","unit":"mm","feature":"body_width"},"depth":{"label":"Overall depth","description":"Changes the body depth along Y","unit":"mm","feature":"body_depth"},"height":{"label":"Overall height","description":"Changes the wedge height along Z","unit":"mm","feature":"body_height"}},"features":{"body_width":{"kind":"dimension","axis":"x","label":"Overall width"},"body_depth":{"kind":"dimension","axis":"y","label":"Overall depth"},"body_height":{"kind":"dimension","axis":"z","label":"Overall height"}}} */

// Top-level parameters (user-editable)
width = 100.0;
depth = 62.62;
height = 32.58;

// Derived constants (not editable)
eps = 0.01;

// Module for the wedge body
module wedge_body() {
    // The wedge is defined by a triangular profile in the XZ plane, extruded along Y.
    // Front view (XZ): Right-angled triangle.
    // Based on the front view polygon:
    // Points in normalized view coords (u, v):
    // (0.0163, 0.0392) -> Top-Left (High Back)
    // (0.0199, 0.9225) -> Bottom-Left (Low Front/Back base)
    // (0.9819, 0.9279) -> Bottom-Right (Low Front/Back base)
    
    // Mapping to CAD (X, Z):
    // u -> X (0 to width)
    // v -> Z (1 to 0, since v=0 is top/high Z, v=1 is bottom/low Z)
    
    // Vertex 1 (Top-Left): u~0, v~0.04 -> X~0, Z~height*(1-0.04) ~ height
    // Vertex 2 (Bottom-Left): u~0, v~0.92 -> X~0, Z~height*(1-0.92) ~ 0
    // Vertex 3 (Bottom-Right): u~1, v~0.93 -> X~width, Z~height*(1-0.93) ~ 0
    
    // This creates a triangle with:
    // - Vertical edge at X=0 (Back Wall) from Z=0 to Z=height
    // - Horizontal edge at Z=0 (Base) from X=0 to X=width
    // - Sloped edge from (0, height) to (width, 0) (Ramp Surface)
    
    // Note: The "Back" is at X=0, "Front" is at X=width.
    // The ramp slopes down from Back (X=0) to Front (X=width).
    
    polygon([
        [0, 0],          // Bottom-Left (Back-Bottom)
        [width, 0],      // Bottom-Right (Front-Bottom)
        [0, height]      // Top-Left (Back-Top)
    ]);
}

// Main design instantiation
// Extrude the triangular profile along the Y-axis (depth)
// The profile is in XZ, so we rotate it to lie in XY for linear_extrude, 
// or use rotate_extrude? No, linear_extrude extrudes along Z by default.
// To extrude along Y, we can rotate the profile 90 degrees around X, 
// then extrude along Z, then rotate back? 
// Simpler: Define polygon in XY plane directly? 
// The polygon function takes 2D points. If we define points as (x, y) and extrude along Z, 
// we get a prism along Z. 
// We want a prism along Y. 
// Strategy: 
// 1. Create the triangle in the XZ plane (as defined above).
// 2. Rotate it -90 degrees around X so it lies in XY plane? 
//    Original: (x, z). Rotate -90 about X: (x, -z, 0) -> (x, 0, -z)? No.
//    Let's just define the polygon in the XY plane such that extrusion along Z creates the shape?
//    No, the shape is constant along Y. 
//    So we define the cross-section in XZ, and extrude along Y.
//    linear_extrude extrudes along Z. 
//    So we need to rotate the object so the extrusion direction aligns with Z.
//    If we rotate the final object 90 degrees around X, the Y-axis becomes Z-axis.
//    So: 
//    1. Define polygon in XZ (x, z).
//    2. linear_extrude(height=depth) -> creates prism along Z.
//    3. Rotate -90 around X -> Y becomes Z? 
//       Rotation -90 about X: Y -> -Z, Z -> Y.
//       So extrusion along Z becomes extrusion along Y.
//       The XZ plane (where polygon was) becomes XY plane? 
//       Point (x, 0, z) -> (x, -z, 0)? No.
//       Let's stick to standard: 
//       Define polygon in XY. Extrude along Z. 
//       We want the triangle in XZ. 
//       So define polygon in XY where Y represents Z? 
//       Polygon points: (x, z). 
//       linear_extrude(height=depth) along Z. 
//       This creates a prism with cross-section in XY (where Y is actually Z) and length along Z (which is actually Y).
//       Then rotate -90 about X to align axes correctly.
//       Original: X=width, Y=height (in polygon), Z=depth (extrusion).
//       Rotate -90 about X: 
//       X stays X.
//       Y (height) -> -Z.
//       Z (depth) -> Y.
//       So we get X=width, Y=depth, Z=-height.
//       Translate Z by height to sit on plate.

// Let's refine the polygon definition for linear_extrude along Z.
// We want the final shape to have:
// X: 0 to width
// Y: 0 to depth
// Z: 0 to height (at X=0), 0 (at X=width)

// If we define polygon in XY plane:
// Points (x, y_poly). 
// Extrude along Z (which will become Y after rotation).
// So y_poly corresponds to the height dimension? No.
// Let's use the rotation method carefully.

// Step 1: Define triangle in XZ plane (x, z).
// Points: (0,0), (width,0), (0,height).
// Step 2: linear_extrude(height=depth). 
// This creates a solid with:
// X: 0..width
// Y: 0..depth (extrusion direction)
// Z: 0..height (from polygon y-coord? No, polygon is 2D (x,y). 
// If I pass (x, z) to polygon(), it treats them as (x, y).
// So the "height" of the triangle in the polygon is along the Y-axis of the polygon space.
// Extrusion is along Z.
// So the solid is:
// X: 0..width
// Y: 0..height (from polygon)
// Z: 0..depth (from extrusion)
// This is a wedge lying on its side. 
// We want:
// X: 0..width
// Y: 0..depth
// Z: 0..height

// So we need to swap Y and Z.
// Rotate 90 degrees around X? 
// Rotation 90 about X: Y -> Z, Z -> -Y.
// So Y(height) -> Z(height). Z(depth) -> -Y(depth).
// This gives Z=height, Y=-depth.
// Translate Y by depth to move to 0..depth.

// Let's verify the triangle orientation.
// Polygon: (0,0), (width,0), (0,height).
// In polygon space (X, Y_poly):
// (0,0) is bottom-left.
// (width,0) is bottom-right.
// (0,height) is top-left.
// This forms a triangle with vertical edge at X=0, horizontal at Y_poly=0.
// After extrusion along Z (which becomes -Y after rotation):
// The "vertical" edge of the triangle (along Y_poly) becomes the vertical edge along Z.
// The "horizontal" edge (along X) stays along X.
// The hypotenuse connects (0, height) to (width, 0).
// So at X=0, Z goes from 0 to height.
// At X=width, Z is 0.
// This matches the requirement: High at Back (X=0), Low at Front (X=width).

// Final transformation:
// 1. linear_extrude(height=depth)
// 2. rotate([90, 0, 0]) -> Y becomes Z, Z becomes -Y.
//    Original Y (0..height) -> Z (0..height).
//    Original Z (0..depth) -> Y (-depth..0).
// 3. translate([0, depth, 0]) -> Y becomes (0..depth).

// Check "Back Wall" at X=0.
// At X=0, the polygon has points (0,0) and (0,height).
// This edge is along the Y_poly axis.
// After rotation, this edge is along the Z axis.
// So the back wall is vertical at X=0. Correct.

// Check "Base" at Z=0.
// The polygon has edge (0,0) to (width,0) along X axis.
// After rotation, this edge is at Z=0 (since Y_poly=0 -> Z=0).
// So the base is flat on the build plate. Correct.

// Check "Ramp".
// Connects (0, height) to (width, 0) in polygon space.
// After rotation, connects (0, 0, height) to (width, 0, 0) in CAD space?
// Wait, Y_poly=height -> Z=height. Y_poly=0 -> Z=0.
// So (0, height) in poly -> (0, ?, height) in CAD.
// (width, 0) in poly -> (width, ?, 0) in CAD.
// The Y coordinate comes from the extrusion direction (original Z).
// So the ramp surface is defined by the line in XZ plane, extruded along Y.
// This is correct.

// One detail: The front view shows the triangle.
// The "Back" is the vertical edge.
// In the front view (looking down Y), we see the XZ plane.
// The vertical edge is at X=0.
// The sloped edge goes from (0, height) to (width, 0).
// This matches the polygon definition.

// Construct the object
rotate([90, 0, 0])
translate([0, 0, -depth]) // Adjust to ensure Y starts at 0 after rotation?
// Let's re-evaluate the rotation and translation.
// linear_extrude creates geometry in Z: 0 to depth.
// rotate([90,0,0]):
// (x, y, z) -> (x, -z, y)
// So Z (0..depth) -> Y (-depth..0).
// Y (0..height) -> Z (0..height).
// So we have Y in [-depth, 0].
// We want Y in [0, depth].
// So translate([0, depth, 0]).

// Let's combine:
translate([0, depth, 0])
rotate([90, 0, 0])
linear_extrude(height=depth)
polygon([
    [0, 0],
    [width, 0],
    [0, height]
]);
