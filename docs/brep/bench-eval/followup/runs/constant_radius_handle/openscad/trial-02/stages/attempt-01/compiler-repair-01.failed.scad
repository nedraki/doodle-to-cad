/* doodle-meta {"version":1,"parameters":{"rod_diameter":{"label":"Rod Diameter","description":"Diameter of the circular cross-section of the handle","unit":"mm","feature":"rod_profile"},"arch_radius":{"label":"Arch Radius","description":"Radius of the semi-circular bend (centerline)","unit":"mm","feature":"arch"},"leg_length":{"label":"Leg Length","description":"Length of the straight vertical legs","unit":"mm","feature":"legs"}},"features":{"rod_profile":{"kind":"region","label":"Rod Cross-section","min":[0,0,0],"max":[0,0,0]},"arch":{"kind":"region","label":"Arch","min":[0,0,0],"max":[0,0,0]},"legs":{"kind":"region","label":"Legs","min":[0,0,0],"max":[0,0,0]}}} */

// Parameters
rod_diameter = 8;
arch_radius = 20;
leg_length = 30;

// Derived dimensions
// The handle is oriented such that the U-shape lies in the XZ plane (Front view).
// The rod extends along Y (Depth).
// Total Height = arch_radius + leg_length + rod_diameter/2 (approx, depending on exact tangent definition)
// Based on spec: max_height 46.24, max_depth 54.0, max_width 28.6.
// Let's align the geometry to the build plate (Z=0).

// The U-shape consists of:
// 1. Two vertical legs of length 'leg_length'.
// 2. A semi-circular arch of radius 'arch_radius' connecting them.
// The legs are tangent to the arch.

// Coordinate System:
// X: Width (left-right)
// Y: Depth (front-back) - The rod runs along Y
// Z: Height (up-down)

// To fit on the build plate (Z=0), we need to position the lowest point of the handle at Z=0.
// The lowest points are the ends of the legs.
// Let's define the path in the XZ plane.
// Center of the arch circle: (0, 0, arch_radius + leg_length) ? 
// No, let's place the center of the arch at (0, 0, arch_radius).
// Then the legs go down from the tangent points.
// Tangent points are at x = +/- arch_radius, z = arch_radius.
// The legs extend downwards from z = arch_radius to z = arch_radius - leg_length.
// To put the bottom at Z=0, we shift everything up by (leg_length - arch_radius) if leg_length > arch_radius?
// Actually, simpler:
// Let the bottom of the legs be at Z = 0.
// The legs go from Z=0 to Z=leg_length.
// The arch connects the tops of the legs.
// The center of the arch is at Z = leg_length.
// The arch goes from ( -arch_radius, leg_length ) to ( arch_radius, leg_length ) via (0, leg_length + arch_radius).
// Wait, the legs are tangent to the arch.
// If the legs are vertical, the tangent points are at the "equator" of the circle.
// So the center of the circle is at (0, 0, leg_length).
// The arch is the upper half of the circle (Z >= leg_length).
// The legs are cylinders from Z=0 to Z=leg_length at X = +/- arch_radius.

// Total Height = leg_length + arch_radius + rod_diameter/2 (top of arch)
// Total Width = 2 * arch_radius + rod_diameter
// Total Depth = rod_diameter (since it's a rod along Y)

// Let's check against derived sizes:
// max_width = 28.6. 2*20 + 8 = 48. This is too wide.
// The spec says "max_width": 28.6.
// If width is 28.6, and rod is 8, then 2*R + 8 = 28.6 => 2R = 20.6 => R = 10.3.
// But the spec explicitly says "bend radius (R20)".
// There is a conflict between the "R20" text and the "max_width 28.6" derived size.
// The "derived_sizes" section says "width_mm": 28.6.
// The "specification" section says "bend radius (R20)".
// Usually, explicit dimensions in the text (R20) override measured ink spans if the measurement is ambiguous or if the "max_width" refers to something else.
// However, looking at the views:
// View 5 (Left) has aspect ratio ~1. It shows the U-shape.
// View 3 (Top) is a circle.
// If the handle is rotated 90 degrees?
// "Front view ... Defines the overall U-shape profile ... in the XY plane." -> This is confusing. Front view is XZ.
// Let's re-read carefully: "Defines the overall U-shape profile (arch and legs) and the bend radius (R20) in the XY plane."
// If the U-shape is in the XY plane, then the "height" of the U is along Y or X?
// Standard convention: Front view is XZ. Top is XY.
// If the U-shape is in the XY plane, it would be seen in the Top view.
// But View 3 (Top) is a circle.
// View 5 (Left) shows the U-shape. Left view is YZ.
// So the U-shape is in the YZ plane?
// If the U-shape is in the YZ plane:
// Width (X) is the rod diameter (8mm).
// Depth (Y) and Height (Z) define the U.
// Derived sizes: width 28.6, depth 54.0, height 46.24.
// If Width is 28.6, but rod is 8, this doesn't match a simple rod along X.
// Maybe the "Width" in derived sizes corresponds to the span of the U?
// If the U is in the XZ plane (Front), Width = 2*R + d.
// If R=20, d=8, Width = 48.
// If the U is in the YZ plane (Left), Depth = 2*R + d = 48. Height = L + R + d/2.
// Derived Depth is 54.0. This is close to 48 + some margin? Or maybe R is different?
// Let's look at the "authoritative_max_dimension_mm": 54.
// This matches derived_depth.
// If the U-shape is in the YZ plane (Left view), then the span is along Y.
// Span = 2*R + d. If Span = 54, then 2R + 8 = 54 => 2R = 46 => R = 23.
// But the text says R20.
// If R=20, Span = 48.
// Maybe the "max_depth" 54 includes the rod diameter on both sides? No, that's what I did.
// Let's trust the explicit "R20" and "diameter 8mm" from the text description over the potentially noisy "derived_sizes" which are based on ink spans. The ink spans might be distorted or include annotation lines.
// However, the prompt says: "derived_sizes ... override your own pixel estimates".
// But it also says "preserve functional parts... R20".
// Let's look at the "uncertainties": "The 'diameter 8 mm' annotation ... is interpreted as the rod diameter."
// Let's assume the text "R20" is the design intent.
// If R=20, d=8.
// Width (X) = 8 (rod diameter).
// Depth (Y) = 2*20 + 8 = 48.
// Height (Z) = Leg + R + d/2.
// If Height is 46.24.
// Leg + 20 + 4 = 46.24 => Leg = 22.24.
// This seems plausible.
// But the derived_width is 28.6. This is very different from 8.
// Is it possible the handle is not a simple rod?
// "Single continuous curved rod".
// Maybe the orientation is different.
// If the U-shape is in the XZ plane (Front), Width = 48. Height = 46.24. Depth = 8.
// Derived Width 28.6 vs 48.
// Derived Depth 54 vs 8.
// Derived Height 46.24 vs 46.24.
// The Height matches perfectly if the U is in XZ or YZ.
// The mismatch in Width/Depth suggests the "derived_sizes" might be mapping axes differently or the object is rotated.
// If the object is rotated 90 degrees around Z?
// If U is in YZ plane:
// X (Width) = 8.
// Y (Depth) = 48.
// Z (Height) = 46.24.
// Derived: W=28.6, D=54, H=46.24.
// None of the horizontal dimensions match well (8 vs 28.6, 48 vs 54).
// However, 54 is the "authoritative max dimension".
// If we scale the whole thing so the max dimension is 54?
// If we assume the "R20" is the *nominal* radius but the *measured* max dimension is 54.
// If the max dimension is the span of the U (Depth), then 2R + d = 54.
// With d=8, 2R = 46, R = 23.
// If we use R=23, d=8.
// Height = Leg + 23 + 4 = Leg + 27.
// If Height is 46.24, Leg = 19.24.
// Width = 8.
// This fits the "authoritative max dimension" constraint better than R=20 (which gives 48).
// The prompt says: "derived_sizes ... override your own pixel estimates ... user_supplied_axes are user-stated absolute sizes: reproduce that extent exactly".
// The "authoritative_max_dimension_mm" is 54.
// The derived_depth is 54.0.
// So the Depth (Y) should be 54.
// If the U-shape is in the YZ plane (Left view), the span is along Y.
// So Span_Y = 54.
// Span_Y = 2*R + d.
// 54 = 2*R + 8 => R = 23.
// This contradicts the text "R20".
// Which takes precedence? "derived_sizes ... override ... user_supplied_axes ... reproduce that extent exactly".
// The "authoritative_max_dimension_mm" is 54.
// I will prioritize the authoritative max dimension of 54mm for the largest extent.
// I will assume the U-shape lies in the YZ plane (as seen in Left view, which is often the profile view for handles).
// Wait, View 5 is "left". Left view looks down X. Plane is YZ.
// View 5 shows the U-shape.
// So the U-shape is in the YZ plane.
// X is the rod diameter.
// Y is the span.
// Z is the height.
// Derived Width (X) = 28.6. This is huge for a rod diameter if the rod is 8mm.
// Maybe the "rod" is not a circle? "cross-section ... as a circle (diameter 8mm)".
// If X is 28.6, and the rod is 8mm, maybe there are multiple rods? No, "Single continuous".
// Maybe the "Width" in derived_sizes is actually the span, and "Depth" is the rod?
// Let's check the view mappings.
// View 3 (Top) is a circle. Top view looks down Z. Plane XY.
// If Top view is a circle, the object is cylindrical along Z?
// No, "Top view ... Defines the cross-section ... as a circle".
// This implies the cross-section perpendicular to the path is a circle.
// If the path is in YZ, the cross-section is in X (and perpendicular to tangent).
// If the Top view (XY) is a circle, it means the projection onto XY is a circle.
// This happens if the rod is vertical (along Z)? No, it's a U-handle.
// If the U is in YZ, the Top view (XY) would show the legs as rectangles (width d, length leg) and the arch as a rectangle (width d, length span).
// It would NOT be a circle.
// UNLESS the "Top view" in the drawing is actually the view looking down the axis of the rod?
// No, standard third angle: Top is XY.
// If View 3 is a circle, and it's the Top view, then the object must be a cylinder standing up?
// But it's a U-handle.
// Perhaps the "Top view" label in the JSON is misleading, or the "circle" is the cross-section shown in detail?
// "view_3 ... Defines the cross-section ... as a circle".
// This is likely a detail view or the orientation is such that we are looking down the rod?
// But the "construction_plan" says "profile_plane: path_normal".
// Let's stick to the most robust interpretation:
// 1. It is a U-handle.
// 2. Rod diameter = 8mm.
// 3. Max dimension = 54mm.
// 4. The U-shape is the dominant feature.
// 5. I will orient the U-shape in the XZ plane (Front) or YZ plane (Left).
//    If I put it in XZ (Front):
//    Width (X) = Span. Height (Z) = Height. Depth (Y) = Rod Diameter.
//    If Span = 54 (Max Dim), then 2R + 8 = 54 => R = 23.
//    Height = 46.24.
//    Depth = 8.
//    This matches "authoritative max dimension" = 54 (Width).
//    The derived_width is 28.6. This is the only mismatch.
//    The derived_depth is 54.0.
//    If I swap X and Y?
//    If U is in YZ (Left):
//    Depth (Y) = Span = 54.
//    Height (Z) = 46.24.
//    Width (X) = 8.
//    Derived Width = 28.6. Mismatch.
//    Derived Depth = 54. Match.
//    Derived Height = 46.24. Match.
//    So the U-shape is in the YZ plane.
//    The "Width" (X) is 8mm. The derived 28.6 is likely noise or includes annotation.
//    I will use:
//    Rod Diameter = 8.
//    Span (Y) = 54.
//    Height (Z) = 46.24.
//    From Span = 2*R + d => 54 = 2R + 8 => R = 23.
//    From Height = Leg + R + d/2 => 46.24 = Leg + 23 + 4 => Leg = 19.24.

// Let's verify the "R20" text. If I use R=20, Span=48.
// The prompt says "derived_sizes ... override ... user_supplied_axes ... reproduce that extent exactly".
// The "authoritative_max_dimension_mm" is 54.
// I will scale the geometry to fit the 54mm max dimension.
// So R=23, Leg=19.24, d=8.

// Orientation:
// U-shape in YZ plane.
// Legs parallel to Z.
// Arch in YZ.
// Rod extends along X.

// Build Plate:
// Lowest point Z=0.
// Legs go from Z=0 to Z=Leg.
// Arch center at Z=Leg.
// Arch top at Z=Leg+R.
// Total Height = Leg + R + d/2 = 19.24 + 23 + 4 = 46.24. Correct.
// Total Depth (Y) = 2*R + d = 46 + 8 = 54. Correct.
// Total Width (X) = d = 8.

// Geometry Construction:
// 1. Left Leg: Cylinder along X, at Y = -R, Z from 0 to Leg.
//    Wait, the legs are at Y = +/- R?
//    The center of the arch is at (0, 0, Leg).
//    The legs are tangent to the arch.
//    Tangent points are at (0, +/- R, Leg).
//    So legs are at Y = -R and Y = +R.
//    Legs extend down to Z=0.
//    Legs are cylinders along X.
//    Radius = d/2 = 4.
//    Length = Leg.
//    Position: (0, -R, Leg/2) and (0, R, Leg/2).
//    Wait, cylinder axis is X.
//    translate([0, -R, Leg/2]) rotate([0,90,0]) cylinder(h=Leg, r=4);
//    translate([0, R, Leg/2]) rotate([0,90,0]) cylinder(h=Leg, r=4);

// 2. Arch:
//    Semi-circle in YZ plane, centered at (0, 0, Leg).
//    Radius R.
//    We can create this by sweeping a circle along the arc.
//    Or by using a torus segment.
//    Torus: major radius R, minor radius r=4.
//    We want the upper half (Z > Leg).
//    Torus is centered at (0,0,Leg).
//    We cut off the bottom half.
//    difference() {
//      translate([0,0,Leg]) rotate([90,0,0]) torus(R, 4); // Torus axis is Z by default? No, torus is in XY plane.
//      // rotate([90,0,0]) puts torus in XZ plane?
//      // Default torus: ring in XY, tube around Z.
//      // We want ring in YZ.
//      // Rotate 90 around X: XY -> XZ. No.
//      // Rotate 90 around Y: XY -> ZY?
//      // Let's just use rotate_extrude or hull.
//      // Hull of two circles? No.
//      // Use a torus and intersect with a cube.
//    }
    
//    Torus in YZ plane:
//    Default torus is in XY plane (axis Z).
//    To get it in YZ plane (axis X), rotate([0,90,0]).
//    Then translate to (0,0,Leg).
//    Then intersect with a cube covering Z > Leg.

//    Let's refine the Torus orientation.
//    rotate([0,90,0]) torus(R, r) -> Ring is in YZ plane. Axis is X.
//    This is correct. The tube goes around the X axis? No, the ring is in YZ, so the "hole" is along X.
//    Yes, this matches the legs which are along X.

//    So:
//    translate([0,0,Leg])
//    rotate([0,90,0])
//    torus(R, r);
//    Intersect with cube(x=100, y=100, z=100) positioned to keep Z > Leg.

//    Wait, the legs are at Y = +/- R.
//    The torus connects them.
//    The legs are cylinders along X.
//    The torus tube is also along X (at the tangent points).
//    They will merge perfectly.

//    One detail: The legs are straight. The torus is curved.
//    The intersection of the leg cylinder and the torus tube at the tangent point is smooth.

//    Code Structure:
//    module handle() {
//      // Legs
//      translate([0, -R, Leg/2]) rotate([0,90,0]) cylinder(h=Leg, r=r, center=true);
//      translate([0, R, Leg/2]) rotate([0,90,0]) cylinder(h=Leg, r=r, center=true);
//      
//      // Arch
//      translate([0,0,Leg])
//      rotate([0,90,0])
//      torus(R, r);
//      
//      // Cut bottom half of torus
//      // We only want the part where Z >= Leg.
//      // The torus is centered at Z=Leg.
//      // So we keep Z >= Leg.
//      // But the legs go down to Z=0.
//      // So we just union the legs and the top half of the torus.
//    }
    
//    To get the top half of the torus:
//    difference() {
//      translate([0,0,Leg]) rotate([0,90,0]) torus(R, r);
//      translate([-100, -100, -100]) cube([200, 200, 100]); // Cuts Z < Leg
//    }
//    Wait, the torus is centered at Z=Leg.
//    The cube should cover Z < Leg.
//    translate([-100, -100, Leg-100]) cube([200, 200, 100]);

//    Let's check the Y extent of the torus.
//    Y goes from -R to R.
//    The legs are at Y = -R and Y = R.
//    The torus connects them.
//    The legs are cylinders along X.
//    The torus tube is along X.
//    They overlap.

//    Final Dimensions:
//    R = 23
//    r = 4
//    Leg = 19.24

//    Let's double check the "R20" vs "54" conflict.
//    If I use R=20, Span=48.
//    If I use R=23, Span=54.
//    The prompt emphasizes "authoritative_max_dimension_mm": 54.
//    And "derived_sizes ... override ... user_supplied_axes".
//    I will use R=23.

//    One more check: "bend radius (R20)".
//    If the user explicitly wrote R20, maybe the 54 is the height?
//    Height = 46.24.
//    If Height = 54?
//    If Height = 54, and R=20, d=8.
//    Leg + 20 + 4 = 54 => Leg = 30.
//    Span = 48.
//    Width = 8.
//    This fits "R20" and "Leg 30" (from generation_notes: "two straight segments of length 30mm").
//    Generation notes: "path consists of two straight segments of length 30mm and a semi-circular arc of radius 20mm".
//    This is very specific.
//    If I follow the generation notes:
//    R = 20.
//    Leg = 30.
//    d = 8.
//    Height = 30 + 20 + 4 = 54.
//    Span = 40 + 8 = 48.
//    Width = 8.
//    Max Dimension = 54 (Height).
//    This matches "authoritative_max_dimension_mm": 54.
//    And it matches the explicit text "R20" and "length 30mm".
//    The derived_sizes might be misaligned or rotated.
//    Derived Height 46.24 vs Calculated 54.
//    Derived Depth 54.0 vs Calculated 48 (Span).
//    Derived Width 28.6 vs Calculated 8.
//    The "authoritative_max_dimension" is 54.
//    If I use the generation notes, the max dimension is 54 (Height).
//    This seems the most consistent with the explicit text.
//    I will use R=20, Leg=30, d=8.
//    Orientation: U-shape in XZ plane (Front) or YZ (Left)?
//    If Height is 54, and it's the max dimension, and it's vertical...
//    If U is in XZ: Height=54, Width=48, Depth=8.
//    If U is in YZ: Height=54, Depth=48, Width=8.
//    Derived Depth is 54. Derived Height is 46.
//    If I orient U in YZ: Depth=48, Height=54.
//    Derived Depth 54 is close to 48? No.
//    Derived Height 46 is close to 54? No.
//    But "authoritative_max_dimension" is 54.
//    I will stick to the explicit text: R=20, Leg=30, d=8.
//    I will orient it so the Height is 54.
//    I'll put the U-shape in the XZ plane (Front view) because "Front view ... Defines the overall U-shape".
//    So Width=48, Height=54, Depth=8.
//    Wait, if Width=48, and derived_width=28.6...
//    Maybe the handle is smaller?
//    But "authoritative_max_dimension" is 54.
//    I will produce the part with R=20, Leg=30, d=8.
//    I will center it on the build plate.

//    Final Plan:
//    R = 20
//    Leg = 30
//    d = 8
//    U-shape in XZ plane.
//    Legs along Z.
//    Arch in XZ.
//    Rod along Y.
//    Center X=0, Y=0.
//    Bottom Z=0.

//    Legs:
//    At X = +/- R.
//    Z from 0 to Leg.
//    Cylinders along Y.
//    translate([R, 0, Leg/2]) rotate([90,0,0]) cylinder(h=Leg, r=4, center=true);
//    translate([-R, 0, Leg/2]) rotate([90,0,0]) cylinder(h=Leg, r=4, center=true);

//    Arch:
//    Center (0,0,Leg).
//    Torus in XZ plane.
//    Default torus in XY. Rotate 90 around X to get XZ?
//    rotate([90,0,0]) torus(R, r) -> Ring in XZ. Axis Y.
//    Yes.
//    translate([0,0,Leg]) rotate([90,0,0]) torus(R, r);
//    Cut bottom half (Z < Leg).

//    Union.

//    Check build plate:
//    Lowest Z = 0 (bottom of legs).
//    Highest Z = Leg + R + r = 30 + 20 + 4 = 54.
//    Fits in 256.

//    Check Y extent:
//    -4 to 4. Fits.

//    Check X extent:
//    -24 to 24. Fits.

//    Code:

```openscad
/* doodle-meta {"version":1,"parameters":{"rod_diameter":{"label":"Rod Diameter","description":"Diameter of the circular cross-section of the handle","unit":"mm","feature":"rod_profile"},"arch_radius":{"label":"Arch Radius","description":"Radius of the semi-circular bend (centerline)","unit":"mm","feature":"arch"},"leg_length":{"label":"Leg Length","description":"Length of the straight vertical legs","unit":"mm","feature":"legs"}},"features":{"rod_profile":{"kind":"region","label":"Rod Cross-section","min":[0,0,0],"max":[0,0,0]},"arch":{"kind":"region","label":"Arch","min":[0,0,0],"max":[0,0,0]},"legs":{"kind":"region","label":"Legs","min":[0,0,0],"max":[0,0,0]}}} */

// Parameters based on explicit text and authoritative max dimension
rod_diameter = 8;
arch_radius = 20;
leg_length = 30;

// Derived
r = rod_diameter / 2;
R = arch_radius;
L = leg_length;

// The handle is oriented with the U-shape in the XZ plane.
// Legs are vertical (along Z).
// Rod extends along Y.
// Bottom of legs at Z=0.

module handle() {
    // Left Leg
    translate([-R, 0, L/2])
    rotate([90, 0, 0])
    cylinder(h=L, r=r, center=true);

    // Right Leg
    translate([R, 0, L/2])
    rotate([90, 0, 0])
    cylinder(h=L, r=r, center=true);

    // Arch (Upper half of torus)
    // Torus centered at (0,0,L)
    // Rotate 90 deg around X to put ring in XZ plane (axis Y)
    difference() {
        translate([0, 0, L])
        rotate([90, 0, 0])
        torus(R, r);
        
        // Cut off the bottom half (Z < L)
        // The torus is centered at Z=L.
        // We remove everything below Z=L.
        translate([-100, -100, L - 100])
        cube([200, 200, 100]);
    }
}

// Instantiate
handle();
