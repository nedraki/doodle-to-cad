/* doodle-meta {"version":1,"parameters":{"flange_diameter":{"label":"Flange Diameter","description":"Overall diameter of the circular flange plate","unit":"mm","feature":"body_diameter"},"flange_thickness":{"label":"Flange Thickness","description":"Thickness (height) of the flange plate","unit":"mm","feature":"body_thickness"},"center_bore_diameter":{"label":"Center Bore Diameter","description":"Diameter of the central through-hole","unit":"mm","feature":"center_bore"},"bolt_hole_diameter":{"label":"Bolt Hole Diameter","description":"Diameter of the four peripheral bolt holes","unit":"mm","feature":"bolt_holes"},"bolt_circle_diameter":{"label":"Bolt Circle Diameter","description":"Diameter of the circle on which bolt holes are centered","unit":"mm","feature":"bolt_holes"}},"features":{"body_diameter":{"kind":"dimension","axis":"x","label":"Flange Diameter"},"body_thickness":{"kind":"dimension","axis":"z","label":"Flange Thickness"},"center_bore":{"kind":"region","label":"Center Bore","min":[{"parameter":"center_bore_diameter","scale":-0.5},{"parameter":"center_bore_diameter","scale":-0.5},0],"max":[{"parameter":"center_bore_diameter","scale":0.5},{"parameter":"center_bore_diameter","scale":0.5},{"parameter":"flange_thickness"}]},"bolt_holes":{"kind":"region","label":"Bolt Holes","min":[{"parameter":"bolt_circle_diameter","scale":-0.5},{"parameter":"bolt_circle_diameter","scale":-0.5},0],"max":[{"parameter":"bolt_circle_diameter","scale":0.5},{"parameter":"bolt_circle_diameter","scale":0.5},{"parameter":"flange_thickness"}]}}} */

// Parameters
flange_diameter = 80;
flange_thickness = 6.666666666666666;
center_bore_diameter = 26.666666666666664;
bolt_hole_diameter = 8;
bolt_circle_diameter = 53.33333333333333;

// Derived constants
$fn = 64;
eps = 0.01;

// Main Design
difference() {
    // 1. Positive Body: Circular Plate
    // The flange sits on the build plate (Z=0 to Z=flange_thickness)
    cylinder(d=flange_diameter, h=flange_thickness, center=false);

    // 2. Subtractive Cutters
    
    // Center Bore: Through hole along Z axis
    // Axis is Z, so no rotation needed. Centered at X=0, Y=0.
    // Must traverse the full thickness.
    translate([0, 0, -eps])
        cylinder(d=center_bore_diameter, h=flange_thickness + 2*eps, center=false);

    // Bolt Holes: 4 holes arranged symmetrically
    // The specification places them at (±40, ±40).
    // This corresponds to a bolt circle diameter of sqrt(40^2 + 40^2) * 2 = 113.1? 
    // Wait, the spec says bolt_circle_diameter = 80. 
    // If bolt_circle_diameter is 80, radius is 40.
    // The coordinates (40, 40) imply a radius of sqrt(40^2+40^2) = 56.57.
    // The "repetitions" section says radius 56.5.
    // The "dimensions" section says bolt_circle_diameter 80.
    // There is a conflict. 
    // View 2 (Front) shows holes at normalized centers approx 0.24 and 0.75.
    // Center is 0.5. Offset is 0.25.
    // Total width 120. Offset = 0.25 * 120 = 30mm from center?
    // If offset is 30mm in X and 30mm in Z (which maps to Y in 3D for the front view? No, Front view is XZ).
    // Let's re-read the coordinate mapping carefully.
    // Front view (view_2): u -> +X, v -> -Z.
    // The holes are in the XY plane of the flange (since it's a flange plate extruded in Z).
    // Wait, the "Front" view in standard mechanical drawing of a flange usually looks at the face.
    // If the flange is extruded in Z, the "Front" view (looking down Y) sees the XZ plane? 
    // No, if the flange is a disk in XY extruded in Z, the "Top" view (looking down Z) sees the circle.
    // The "Front" view (looking down Y) sees the edge (rectangle).
    // BUT the input says:
    // view_2 (front) constrains: "Outer circular profile... Defines the XY plane geometry."
    // This implies the "Front" view provided is actually the view of the FACE of the flange.
    // In standard third-angle projection, if the Top view is the rectangle (edge), the Front view is the circle (face).
    // This means the flange face is in the XZ plane? Or the flange is oriented such that its face is visible in Front?
    // Let's look at the "Top" view (view_1). It is a rectangle. 
    // If Top is rectangle and Front is Circle, the object is a disk standing up? 
    // OR, the labels "Front" and "Top" are swapped relative to standard orientation, OR the object is oriented differently.
    // Let's trust the "constrains" text:
    // view_2 (front) -> "Defines the XY plane geometry" (Circular profile).
    // view_1 (top) -> "Flange thickness... rectangular profile".
    // This implies the circular face is in the XY plane? No, if Front sees the circle, the circle is in XZ (if looking down Y) or XY (if looking down Z).
    // Standard: Front looks down Y. Top looks down Z.
    // If Front (down Y) sees a circle, the circle is in the XZ plane.
    // If Top (down Z) sees a rectangle, the object is thin in Z? No, Top sees XY. If it sees a rectangle, the object is rectangular in XY?
    // Contradiction.
    
    // Let's look at the "construction_plan":
    // op_2: extrude, profile_plane: XY, direction_axis: Z.
    // This creates a disk in XY, extruded in Z.
    // If this is the case:
    // Top view (down Z) should see the Circle.
    // Front view (down Y) should see the Rectangle (edge).
    // BUT the input data says:
    // view_1 (top) is a rectangle.
    // view_2 (front) is a circle.
    // This implies the "Top" view in the input data is actually the view looking down the axis of the cylinder? No, that would be a circle.
    // If view_1 is a rectangle, and it's the "Top" view (down Z), then the object is NOT a disk in XY.
    // If the object is a disk in XZ (standing up), then:
    // Front (down Y) sees Circle. (Matches view_2)
    // Top (down Z) sees Rectangle. (Matches view_1)
    // Right (down X) sees Rectangle.
    
    // So the flange is oriented with its face in the XZ plane, and thickness along Y.
    // Let's verify with the "cutout_policy" and "previous_candidate_failures".
    // Failure: "Y=120 mm vs expected 18.75 mm". 
    // If the flange is in XZ, its diameter is in X and Z. Thickness is in Y.
    // Max dimension 120. So X=120, Z=120. Y=10 (thickness).
    // The previous failure said Y=120 was wrong. This supports Y being the thickness (small).
    
    // So:
    // Body: Cylinder with axis along Y.
    // Diameter 120. Height (Thickness) 10.
    // Centered at origin?
    // "The part must sit on the build plate: lowest geometry at Z=0".
    // If the cylinder is along Y, its circular face is in XZ.
    // To sit on Z=0, the bottom of the circle must be at Z=0.
    // So the center of the circle is at Z = Radius = 60.
    // X center = 0.
    // Y center = Thickness/2 = 5.
    
    // Let's re-evaluate the "Front" view mapping.
    // view_2 (front) looks down Y.
    // u -> +X, v -> -Z.
    // Center of view is (0.5, 0.5).
    // Center of circle in view is (0.5, 0.5).
    // This maps to X=0, Z=0 in view coordinates?
    // If the circle is centered at X=0, Z=60 (to sit on plate), the view center (Z=0) would be at the bottom edge.
    // The view shows the circle centered.
    // This implies the view coordinate system is centered on the object, not the build plate.
    // The "cad_mapping" says: "origin: shared object origin".
    // If the object origin is the center of the flange face, then Z=0 is the center.
    // But the requirement says "lowest geometry at Z=0".
    // So we must translate the final object up by Radius.
    
    // Let's construct the object centered at origin first, then translate.
    // Body: Cylinder axis Y.
    // translate([0,0,0]) rotate([90,0,0]) cylinder(d=120, h=10, center=true);
    // This puts the center at (0,0,0).
    // Then translate([0,0,60]) to put bottom at Z=0.
    
    // Holes:
    // Center bore: Through the thickness (Y axis).
    // Bolt holes: Through the thickness (Y axis).
    
    // Positions from view_2 (Front, looking down Y):
    // u -> X, v -> -Z.
    // Center bore: center (0.5, 0.5) -> X=0, Z=0 (relative to center).
    // Bolt holes:
    // contour_11: center (0.2432, 0.2511).
    // u=0.2432 -> X = (0.2432 - 0.5) * 120 = -30.8 mm.
    // v=0.2511 -> Z = (0.5 - 0.2511) * 120 = 29.8 mm.
    // Wait, v maps to -Z. So higher v is lower Z.
    // v=0.25 is above center (0.5). So Z is positive.
    // Z = (0.5 - 0.2511) * 120 = 29.88 mm.
    // So hole at (-30.8, 29.9).
    
    // contour_9: center (0.7466, 0.2511).
    // u=0.7466 -> X = (0.7466 - 0.5) * 120 = 29.6 mm.
    // v=0.2511 -> Z = 29.9 mm.
    // Hole at (29.6, 29.9).
    
    // contour_4: center (0.2432, 0.758).
    // u=0.2432 -> X = -30.8 mm.
    // v=0.758 -> Z = (0.5 - 0.758) * 120 = -30.96 mm.
    // Hole at (-30.8, -31.0).
    
    // contour_2: center (0.7466, 0.758).
    // u=0.7466 -> X = 29.6 mm.
    // v=0.758 -> Z = -31.0 mm.
    // Hole at (29.6, -31.0).
    
    // These positions are roughly (±30, ±30).
    // Radius = sqrt(30^2 + 30^2) = 42.4.
    // Bolt circle diameter = 84.8.
    // Spec says bolt_circle_diameter = 80.
    // Spec says bolt hole centers at (40,40) in the "features" list.
    // (40,40) -> Radius 56.5. Diameter 113.
    // The "repetitions" say radius 56.5.
    // The "dimensions" say bolt_circle_diameter 80.
    // The "measured" data suggests ~30mm offset from center.
    // 30mm offset -> Diameter 60? No, 30 is half-width.
    // If holes are at X=±30, Z=±30, the distance from center is 42.4.
    // If the spec "bolt_circle_diameter 80" is authoritative, radius is 40.
    // If radius is 40, and they are symmetric at 45 degrees, X=28.28, Z=28.28.
    // This matches the measured ~30mm closely.
    // I will use the parameter `bolt_circle_diameter` = 80.
    // And place them at 45, 135, 225, 315 degrees.
    
    // Implementation:
    // 1. Create cylinder along Y.
    // 2. Subtract center bore (cylinder along Y).
    // 3. Subtract 4 bolt holes (cylinders along Y).
    // 4. Translate up by Radius to sit on Z=0.
}

// Helper module for a hole through the flange (along Y)
module flange_hole(d, x, z) {
    // The flange body is centered at (0,0,0) before translation.
    // Holes are cut along Y.
    // We need to position them at X=x, Z=z.
    // The cylinder axis is Y.
    // rotate([90,0,0]) makes cylinder axis Y.
    // translate([x, 0, z]) moves it to position.
    // The cylinder should span the thickness.
    // Since the body is centered at Y=0 with height `flange_thickness`,
    // the cylinder should be centered at Y=0 with height `flange_thickness + 2*eps`.
    translate([x, 0, z])
        rotate([90, 0, 0])
            cylinder(d=d, h=flange_thickness + 2*eps, center=true);
}

// Re-implementing the main block with the correct orientation logic

difference() {
    // Body: Cylinder along Y axis
    // Centered at origin (0,0,0) for now.
    // Diameter 120, Height (Thickness) 10.
    rotate([90, 0, 0])
        cylinder(d=flange_diameter, h=flange_thickness, center=true);
        
    // Center Bore
    // Through hole along Y.
    rotate([90, 0, 0])
        cylinder(d=center_bore_diameter, h=flange_thickness + 2*eps, center=true);
        
    // Bolt Holes
    // Placed on bolt_circle_diameter at 45, 135, 225, 315 degrees.
    // Radius = bolt_circle_diameter / 2
    bolt_radius = bolt_circle_diameter / 2;
    
    // Hole 1: 45 deg (X+, Z+)
    flange_hole(bolt_hole_diameter, bolt_radius * cos(45), bolt_radius * sin(45));
    
    // Hole 2: 135 deg (X-, Z+)
    flange_hole(bolt_hole_diameter, bolt_radius * cos(135), bolt_radius * sin(135));
    
    // Hole 3: 225 deg (X-, Z-)
    flange_hole(bolt_hole_diameter, bolt_radius * cos(225), bolt_radius * sin(225));
    
    // Hole 4: 315 deg (X+, Z-)
    flange_hole(bolt_hole_diameter, bolt_radius * cos(315), bolt_radius * sin(315));
}

// Translate the entire object so it sits on the build plate (Z=0)
// The object is currently centered at Z=0.
// The lowest point is Z = -flange_diameter/2.
// We need to move it up by flange_diameter/2.
translate([0, 0, flange_diameter / 2])
    difference() {
        // Body
        rotate([90, 0, 0])
            cylinder(d=flange_diameter, h=flange_thickness, center=true);
            
        // Center Bore
        rotate([90, 0, 0])
            cylinder(d=center_bore_diameter, h=flange_thickness + 2*eps, center=true);
            
        // Bolt Holes
        bolt_radius = bolt_circle_diameter / 2;
        
        flange_hole(bolt_hole_diameter, bolt_radius * cos(45), bolt_radius * sin(45));
        flange_hole(bolt_hole_diameter, bolt_radius * cos(135), bolt_radius * sin(135));
        flange_hole(bolt_hole_diameter, bolt_radius * cos(225), bolt_radius * sin(225));
        flange_hole(bolt_hole_diameter, bolt_radius * cos(315), bolt_radius * sin(315));
    }
