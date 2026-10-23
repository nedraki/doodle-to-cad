/* doodle-meta {"version":1,"parameters":{"hex_width":{"label":"Hexagon Width","description":"Distance between opposite flat sides of the hexagonal cross-section","unit":"mm","feature":"hex_profile"},"prism_depth":{"label":"Prism Depth","description":"Length of the hexagonal prism along the Y axis","unit":"mm","feature":"prism_depth"}},"features":{"hex_profile":{"kind":"dimension","axis":"x","label":"Hexagon Width"},"prism_depth":{"kind":"dimension","axis":"y","label":"Prism Depth"}}} */

// User-editable parameters
hex_width = 60.62180652983459;
prism_depth = 60.19745388412576;

// Derived parameters
// For a regular hexagon with flat-to-flat distance 'hex_width', the circumradius (center to vertex) is:
// R = hex_width / sqrt(3)
hex_circumradius = hex_width / sqrt(3);

// The height of the hexagon (vertex-to-vertex) is 2 * R
hex_height = 2 * hex_circumradius;

// Module to create a regular hexagon centered at origin in XY plane
// r is the circumradius (center to vertex)
module regular_hexagon(r) {
    polygon(
        points = [
            [r, 0],
            [r * cos(60), r * sin(60)],
            [r * cos(120), r * sin(120)],
            [r * cos(180), r * sin(180)],
            [r * cos(240), r * sin(240)],
            [r * cos(300), r * sin(300)]
        ]
    );
}

// Main design
// The hexagon is defined in the XZ plane (front view) and extruded along Y.
// To achieve this with standard OpenSCAD primitives:
// 1. Create the hexagon in the XY plane (standard polygon orientation).
// 2. Rotate it so it lies in the XZ plane (rotate around X by 90 degrees).
// 3. Extrude it along the Y axis.

// Step 1 & 2: Create hexagon in XZ plane
// The polygon is created in XY. Rotating 90 deg around X maps Y->Z and Z->-Y.
// So the polygon lies in the XZ plane.
// We need to center it vertically. The hexagon has height 'hex_height'.
// The polygon is centered at (0,0) in its local XY. After rotation, it is centered at (0,0,0) in XZ.
// We want the bottom of the part to be at Z=0.
// The hexagon vertices range from -R to +R in the local Y (which becomes Z).
// So we need to shift it up by R (hex_circumradius) to sit on the build plate.

translate([0, 0, hex_circumradius]) {
    rotate([90, 0, 0]) {
        // Extrude along the local Z axis (which is now global Y after rotation? No.)
        // Let's trace axes carefully.
        // Polygon is in XY.
        // rotate([90,0,0]) maps:
        //   Local X -> Global X
        //   Local Y -> Global Z
        //   Local Z -> Global -Y
        // So the polygon lies in the Global XZ plane.
        // linear_extrude extrudes along the local Z axis of the object being extruded.
        // The object being extruded is the rotated polygon. Its local Z is Global -Y.
        // So linear_extrude(height=prism_depth) will extrude along Global -Y.
        // We want it centered or starting from Y=0?
        // The prompt says "sit on the build plate: lowest geometry at Z=0".
        // It doesn't specify Y centering, but usually handles are centered or start at 0.
        // Let's center it in Y for symmetry, or start at 0.
        // "front geometry lies in XZ... cuts along Y".
        // Let's center the prism in Y for a balanced handle.
        
        linear_extrude(height = prism_depth, center = true) {
            regular_hexagon(hex_circumradius);
        }
    }
}
