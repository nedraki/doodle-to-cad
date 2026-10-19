/* doodle-meta {"version":1,"parameters":{"hex_width":{"label":"Hexagon Width","description":"Overall width of the hexagonal cross-section","unit":"mm","feature":"hex_width"},"hex_height":{"label":"Hexagon Height","description":"Overall height of the hexagonal cross-section","unit":"mm","feature":"hex_height"},"prism_depth":{"label":"Prism Depth","description":"Length of the prism along the Y-axis","unit":"mm","feature":"prism_depth"}},"features":{"hex_width":{"kind":"dimension","axis":"x","label":"Hexagon Width"},"hex_height":{"kind":"dimension","axis":"z","label":"Hexagon Height"},"prism_depth":{"kind":"dimension","axis":"y","label":"Prism Depth"}}} */

// Top-level parameters (user-editable)
hex_width = 70.0;
hex_height = 61.49;
prism_depth = 69.51;

// Derived parameters (not user-editable)
// For a flat-top regular hexagon:
// Width (across flats) = sqrt(3) * R
// Height (across points) = 2 * R
// We use the average radius derived from width and height to maintain regularity
// while respecting the measured dimensions as closely as possible.
// R_from_width = hex_width / sqrt(3)
// R_from_height = hex_height / 2
// Using R_from_height as primary for "pointy-top" orientation which matches the 
// "handle" description and typical hex prism orientations where height > width/1.15.
// However, the spec says "flat-top" is inferred. 
// Flat-top: Width = 2*R, Height = sqrt(3)*R.
// Let's check the measurements: Width 70, Height 61.49.
// If Flat-top: R = 35. Height should be 35*sqrt(3) = 60.62. Close to 61.49.
// If Pointy-top: R = 30.745. Width should be 30.745*sqrt(3) = 53.2. Far from 70.
// So it is definitely Flat-top.
// For Flat-top:
// R = hex_width / 2
// Check height: hex_height should be R * sqrt(3).
// We will use hex_width to define the radius R, and construct the hexagon.
// The height parameter is used for validation or if we wanted to stretch it, 
// but for a regular hexagon, width defines it. 
// To respect both measurements slightly better, we can scale the hexagon.
// Base hexagon with circumradius R=1.
// Flat-top vertices: (1,0), (0.5, sqrt(3)/2), (-0.5, sqrt(3)/2), (-1,0), (-0.5, -sqrt(3)/2), (0.5, -sqrt(3)/2)
// Width = 2. Height = sqrt(3).
// Scale X by hex_width/2. Scale Y (which becomes Z in our extrusion) by hex_height/sqrt(3).

module hex_prism() {
    // Define the hexagon in XZ plane (since we extrude along Y)
    // We create a polygon in 2D (X, Z) and extrude along Y.
    
    // Calculate scaling factors
    // Base hexagon points for unit circumradius R=1, flat-top
    // Angles: 0, 60, 120, 180, 240, 300 degrees
    // x = cos(theta), z = sin(theta)
    
    // To make it a regular hexagon matching the bounding box:
    // We want max X = hex_width/2, max Z = hex_height/2.
    // For a regular hexagon, if we align it flat-top:
    // Max X = R. Max Z = R * sqrt(3)/2.
    // So R = hex_width / 2.
    // Then Height = hex_width / 2 * sqrt(3).
    // The measured height is 61.49. 70/2 * 1.732 = 60.62.
    // The difference is small (~1.4%). We will use the width to define the shape 
    // as it is the authoritative max dimension, and scale Z slightly to match height 
    // if we want to be precise to the "measured" box, but "regular hexagon" implies 
    // strict proportions. The prompt says "regular_hexagon". 
    // I will use the width to define the circumradius and let the height fall where it may, 
    // OR scale the Z axis to match the height parameter exactly. 
    // Given "derived_sizes" provides specific height, I will scale the Z axis to match hex_height.
    
    scale_x = hex_width / 2.0;
    scale_z = hex_height / sqrt(3.0); // Because height of flat-top hex is sqrt(3)*R, so R = H/sqrt(3). 
                                      // Wait, if I use scale_x = W/2, then R=W/2. 
                                      // Then natural height is W/2 * sqrt(3).
                                      // If I want height H, I should scale Z by H / (W/2 * sqrt(3)).
    
    // Let's just define the points directly based on width and height to ensure 
    // the bounding box is exactly hex_width x hex_height.
    // This creates a slightly stretched hexagon if W/H != 2/sqrt(3), 
    // but respects the "measured" dimensions.
    
    // Points for a hexagon centered at 0,0 in XZ plane
    // Flat-top orientation:
    // Vertices at angles 0, 60, 120, 180, 240, 300 relative to X axis?
    // No, flat-top means flat edges are horizontal (parallel to X).
    // So vertices are at 30, 90, 150, 210, 270, 330 degrees?
    // Let's check:
    // If vertices are at 0, 60... -> Pointy-top (vertex at right).
    // If vertices are at 30, 90... -> Flat-top (edge between 30 and 90 is vertical? No.)
    
    // Standard Flat-Top Hexagon:
    // Top and Bottom edges are horizontal.
    // Vertices:
    // (W/2, H/4) ? No.
    // Let's use the standard definition:
    // Circumradius R.
    // Flat-top: Vertices at angles 0, 60, 120, 180, 240, 300? 
    // Angle 0 is (R, 0). Angle 60 is (R/2, R*sqrt(3)/2).
    // This has a vertex at the right (X=R). This is "Pointy-Side".
    // "Flat-Top" usually means the top edge is flat.
    // So vertices are at 30, 90, 150, 210, 270, 330.
    // Angle 90 is (0, R). Top vertex.
    // Angle 30 is (R*sqrt(3)/2, R/2).
    // This shape has a vertex at the top. This is "Pointy-Top".
    
    // Let's re-read the uncertainty: "Orientation ... inferred ... as flat-top".
    // In CAD terms, "Flat-Top" often means the top face is a flat edge, not a vertex.
    // If the top is a flat edge, the vertices are at 0, 60, 120... rotated by 30 degrees?
    // If vertices are at 0, 60... -> Vertex at (R,0) and (R/2, H/2). Top is vertex? No, (R/2, H/2) is a vertex.
    // Let's look at the polygon points from the view.
    // View 1 (Front):
    // [0.24, 0.04], [0.03, 0.48], [0.22, 0.95], [0.73, 0.97], [0.97, 0.52], [0.74, 0.06]
    // Normalized 0-1.
    // Top-left (0.24, 0.04) and Top-right (0.74, 0.06). These are close in Y (0.04 vs 0.06).
    // This suggests a flat top edge between these two points.
    // Bottom-left (0.22, 0.95) and Bottom-right (0.73, 0.97). Flat bottom edge.
    // Left-most (0.03, 0.48) and Right-most (0.97, 0.52). These are vertices.
    // So the hexagon has vertices at Left and Right, and flat edges at Top and Bottom.
    // This is "Flat-Top" (and Flat-Bottom).
    // Orientation: Vertices at 0 and 180 degrees (along X axis).
    // So the vertices are at angles 0, 60, 120, 180, 240, 300?
    // If vertex at 0 (Right), vertex at 60 (Top-Right), vertex at 120 (Top-Left)...
    // Wait, if vertex at 0 and 180, then the edge between 60 and 120 is the top edge.
    // Angle 60: (R/2, R*sqrt(3)/2). Angle 120: (-R/2, R*sqrt(3)/2).
    // Yes, this forms a flat top edge at Z = R*sqrt(3)/2.
    // So the circumradius R is aligned with the X-axis.
    // Width (X) = 2 * R.
    // Height (Z) = 2 * (R * sqrt(3)/2) = R * sqrt(3).
    
    // So:
    // R = hex_width / 2.
    // Height = (hex_width / 2) * sqrt(3).
    // We will scale the Z coordinate to match hex_height exactly.
    
    r = hex_width / 2.0;
    z_scale = hex_height / (r * sqrt(3.0));
    
    // Generate points
    // Angles: 0, 60, 120, 180, 240, 300
    // x = r * cos(a)
    // z = r * sin(a) * z_scale
    
    points = [
        [ r * cos(0),   r * sin(0) * z_scale ],
        [ r * cos(60),  r * sin(60) * z_scale ],
        [ r * cos(120), r * sin(120) * z_scale ],
        [ r * cos(180), r * sin(180) * z_scale ],
        [ r * cos(240), r * sin(240) * z_scale ],
        [ r * cos(300), r * sin(300) * z_scale ]
    ];
    
    // Extrude along Y
    // The prism should be centered on Y? 
    // "sit on the build plate: lowest geometry at Z=0"
    // The hexagon is centered at Z=0 in the points above.
    // We need to shift it up by hex_height/2.
    
    translate([0, 0, hex_height/2]) {
        linear_extrude(height = prism_depth, center = true) {
            polygon(points = points);
        }
    }
}

// Instantiate the design
hex_prism();
