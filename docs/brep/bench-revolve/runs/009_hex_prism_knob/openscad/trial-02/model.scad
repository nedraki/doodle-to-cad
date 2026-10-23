/* doodle-meta {"version":1,"parameters":{"hex_width":{"label":"Hexagon Width","description":"Distance across the flats of the hexagonal cross-section","unit":"mm","feature":"hex_width"},"prism_length":{"label":"Prism Length","description":"Length of the extruded hexagonal prism","unit":"mm","feature":"prism_length"}},"features":{"hex_width":{"kind":"dimension","axis":"x","label":"Hexagon Width"},"prism_length":{"kind":"dimension","axis":"y","label":"Prism Length"}}} */

// Parameters
hex_width = 60.62180652983459;
prism_length = 60.62180652983459;

// Derived parameters
// For a regular hexagon with distance across flats = hex_width,
// the circumradius (distance from center to vertex) is hex_width / sqrt(3)
hex_circumradius = hex_width / sqrt(3);

// Module for the hexagonal prism
module hex_prism() {
    // Create a regular hexagon in the XZ plane (front view)
    // The hexagon is centered at (0, 0) in XZ
    // Vertices are at angles 0, 60, 120, 180, 240, 300 degrees
    // We use rotate_extrude or polygon + linear_extrude
    
    // Define hexagon points in XZ plane (X is horizontal, Z is vertical)
    // Center at (0,0) in XZ
    // Radius is hex_circumradius
    // Points: (r*cos(theta), r*sin(theta)) in XZ where theta = 0, 60, ...
    // Note: In OpenSCAD polygon, points are [x, y]. We will map X->X, Z->Y for the polygon definition,
    // then rotate the extrusion.
    
    // Let's define the polygon in the XY plane first, then rotate it to XZ.
    // Or simpler: define points in XZ directly and use linear_extrude with convexity.
    
    // Hexagon vertices in XZ plane (centered at origin):
    // Angle 0: (r, 0) -> X=r, Z=0
    // Angle 60: (r*cos60, r*sin60) -> X=r/2, Z=r*sqrt(3)/2
    // Angle 120: (-r/2, r*sqrt(3)/2)
    // Angle 180: (-r, 0)
    // Angle 240: (-r/2, -r*sqrt(3)/2)
    // Angle 300: (r/2, -r*sqrt(3)/2)
    
    r = hex_circumradius;
    h = r * sqrt(3) / 2; // This is half the distance across flats? No.
    // Distance across flats = 2 * apothem. Apothem = r * cos(30) = r * sqrt(3)/2.
    // So width = 2 * r * sqrt(3)/2 = r * sqrt(3).
    // We set width = hex_width, so r = hex_width / sqrt(3). Correct.
    
    // Points in XZ plane:
    // We need to create a polygon in the XZ plane.
    // OpenSCAD polygon() takes [x, y] pairs. We will treat the second coordinate as Z.
    // Then we extrude along Y.
    
    points = [
        [r, 0],
        [r/2, h],
        [-r/2, h],
        [-r, 0],
        [-r/2, -h],
        [r/2, -h]
    ];
    
    // The polygon is defined in the XY plane by default.
    // We want it in the XZ plane.
    // So we rotate the polygon 90 degrees around X axis? 
    // No, if we define points [x, z], and extrude along Y, we need to rotate the polygon so its "normal" is Y.
    // Default polygon is in XY, normal Z. Extrude along Z.
    // We want normal Y. So rotate -90 around X? 
    // If we rotate -90 around X: Y becomes -Z, Z becomes Y.
    // Let's just define the polygon in XY and rotate the whole object.
    
    // Strategy:
    // 1. Create hexagon in XY plane (centered at 0,0).
    // 2. Extrude along Z by prism_length.
    // 3. Rotate 90 degrees around X to align extrusion axis with Y.
    // 4. Translate to sit on Z=0.
    
    // Hexagon in XY plane:
    // Vertices at angles 0, 60...
    // [r, 0], [r/2, r*sqrt(3)/2], ...
    
    hex_points = [
        [r, 0],
        [r/2, r*sqrt(3)/2],
        [-r/2, r*sqrt(3)/2],
        [-r, 0],
        [-r/2, -r*sqrt(3)/2],
        [r/2, -r*sqrt(3)/2]
    ];
    
    // Extrude along Z
    // Then rotate to align with Y axis (front view is XZ, so extrusion is along Y)
    // Rotate 90 deg around X: Z axis becomes Y axis.
    // Original Z (height) becomes Y (depth).
    // Original Y (width) becomes -Z (height).
    // Original X (width) stays X.
    
    // Wait, if we rotate 90 around X:
    // (x, y, z) -> (x, -z, y)
    // So the extrusion (originally along Z) is now along Y.
    // The hexagon (originally in XY) is now in XZ plane (since Y became -Z).
    // This matches the front view (XZ).
    
    // After rotation, the object is centered at origin.
    // We need to shift it so it sits on Z=0.
    // The hexagon has height (in Z direction after rotation) equal to the distance across flats?
    // Let's check.
    // Original hexagon in XY:
    // Y range: [-r*sqrt(3)/2, r*sqrt(3)/2].
    // After rotation (x, y, z) -> (x, -z, y):
    // New Z coordinate is old Y.
    // So Z range is [-r*sqrt(3)/2, r*sqrt(3)/2].
    // Height = r*sqrt(3) = hex_width.
    // So the hexagon spans Z from -hex_width/2 to +hex_width/2.
    // To sit on Z=0, we translate by +hex_width/2 in Z.
    
    // The extrusion length is along Y.
    // Original Z range: [0, prism_length] (if we start extrusion at 0).
    // After rotation, Y range is [0, prism_length].
    // So we don't need to translate in Y if we want it to start at Y=0?
    // The problem says "front geometry lies in XZ".
    // Usually, we center the object or place it conveniently.
    // "The part must sit on the build plate: lowest geometry at Z=0".
    // "Front geometry lies in XZ".
    
    // Let's center the hexagon in X and Z (before translation).
    // Then translate Z by hex_width/2.
    // For Y, let's center it or start at 0?
    // "front through-features cut along Y".
    // If we center the prism in Y, it goes from -prism_length/2 to +prism_length/2.
    // If we start at 0, it goes 0 to prism_length.
    // The spec doesn't strictly say where in Y it should be, but "front geometry lies in XZ" implies the face is at Y=0?
    // Or just that the view is XZ.
    // Let's center it in Y for symmetry, or place it at Y=0 to Y=prism_length.
    // Given "front view", usually the front face is at Y=0 or Y=-depth/2.
    // Let's center it in Y as well, then translate Y by prism_length/2?
    // Actually, let's just center the whole object at (0,0,0) then translate Z.
    
    // Step 1: Create hexagon in XY, extrude along Z.
    // Step 2: Rotate 90 around X.
    // Step 3: Translate to sit on Z=0.
    
    // Let's refine the rotation.
    // If I rotate 90 around X, the "top" of the hexagon (positive Y in XY) goes to negative Z.
    // So the hexagon is upside down?
    // Hexagon is symmetric, so it doesn't matter for shape, but for orientation.
    // The vertices are at 0, 60, 120...
    // Vertex at (r, 0) -> (r, 0, 0).
    // Vertex at (r/2, r*sqrt(3)/2) -> (r/2, -r*sqrt(3)/2, 0) in rotated coords?
    // Wait, rotation matrix for 90 deg around X:
    // x' = x
    // y' = -z
    // z' = y
    // So (x, y, z) -> (x, -z, y).
    // Point (r, 0, 0) -> (r, 0, 0).
    // Point (r/2, r*sqrt(3)/2, 0) -> (r/2, 0, r*sqrt(3)/2).
    // So the vertex that was at "top" (positive Y) is now at positive Z.
    // This is good.
    
    // The extrusion was along Z (0 to prism_length).
    // So z' = y (original).
    // Original z was 0 to prism_length.
    // So new y is 0 to prism_length.
    // So the prism extends from Y=0 to Y=prism_length.
    
    // The hexagon is in XZ plane.
    // X range: [-r, r].
    // Z range: [-r*sqrt(3)/2, r*sqrt(3)/2].
    // We want Z to start at 0.
    // So translate Z by +r*sqrt(3)/2.
    
    // Let's implement this.
    
    translate([0, 0, hex_width/2]) {
        rotate([90, 0, 0]) {
            linear_extrude(height=prism_length) {
                polygon(points=hex_points);
            }
        }
    }
}

// Instantiate the design
hex_prism();
