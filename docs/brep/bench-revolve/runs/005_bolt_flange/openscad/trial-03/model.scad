/* doodle-meta {"version":1,"parameters":{"outer_diameter":{"label":"Outer Diameter","description":"Diameter of the main circular flange plate","unit":"mm","feature":"outer_profile"},"thickness":{"label":"Thickness","description":"Axial thickness of the flange plate","unit":"mm","feature":"body_thickness"},"bore_diameter":{"label":"Center Bore Diameter","description":"Diameter of the central through-hole","unit":"mm","feature":"center_bore"},"bolt_hole_diameter":{"label":"Bolt Hole Diameter","description":"Diameter of each of the four peripheral bolt holes","unit":"mm","feature":"bolt_holes"},"bolt_circle_diameter":{"label":"Bolt Circle Diameter","description":"Diameter of the circle on which the four bolt holes are centered","unit":"mm","feature":"bolt_holes"}},"features":{"outer_profile":{"kind":"dimension","axis":"x","label":"Outer Diameter"},"body_thickness":{"kind":"dimension","axis":"z","label":"Thickness"},"center_bore":{"kind":"region","label":"Center Bore","min":[{"parameter":"outer_diameter","scale":-0.5,"offset":0},{"parameter":"outer_diameter","scale":-0.5,"offset":0},0],"max":[{"parameter":"outer_diameter","scale":0.5,"offset":0},{"parameter":"outer_diameter","scale":0.5,"offset":0},{"parameter":"thickness","scale":1,"offset":0}]},"bolt_holes":{"kind":"region","label":"Bolt Holes","min":[{"parameter":"bolt_circle_diameter","scale":-0.5,"offset":0},{"parameter":"bolt_circle_diameter","scale":-0.5,"offset":0},0],"max":[{"parameter":"bolt_circle_diameter","scale":0.5,"offset":0},{"parameter":"bolt_circle_diameter","scale":0.5,"offset":0},{"parameter":"thickness","scale":1,"offset":0}]}}} */

// Top-level editable parameters (allowlist)
outer_diameter = 120.0;
thickness = 10.0;
bore_diameter = 40.0;
bolt_hole_diameter = 12.0;
bolt_circle_diameter = 80.0;

// Derived constants (not editable)
$fn = 64;
eps = 0.01;

// Module: Main flange body (positive solid)
module flange_body() {
    // The flange is a circular plate. It sits on the build plate (Z=0 to Z=thickness).
    // The front view (view_2) shows the circular profile in XZ, but since it's a flange,
    // the circular profile is actually in XY (top view) and the thickness is in Z.
    // Wait, the prompt says: "front geometry lies in XZ... top geometry lies in XY".
    // The object is a "Round flange". Usually, a flange is a disk.
    // View 2 (front) shows the circle. View 1 (top) shows a rectangle (side view of the disk).
    // This implies the "front" view is looking at the face of the flange.
    // If the front view looks down Y, and shows a circle, the circle is in the XZ plane?
    // No, standard flange orientation: The face is usually perpendicular to the axis of the pipe/shaft.
    // If the front view (looking down Y) shows a circle, the flange face is in the XZ plane.
    // This means the flange is a disk standing up like a wheel.
    // However, the "top" view (looking down Z) shows a rectangle.
    // If the flange is a disk in XZ, looking down Z would see the edge (a rectangle).
    // This matches the description: View 1 (top) is a rectangle (side profile), View 2 (front) is the circle.
    // So the flange is a disk in the XZ plane, with thickness along Y.
    
    // Let's re-read the coordinate contract carefully.
    // "front geometry lies in XZ and front through-features cut along Y"
    // "top geometry lies in XY and cuts along Z"
    // View 2 (front) has the circular outer profile and the holes.
    // Therefore, the main body is a cylinder with its axis along Y.
    // The "top" view (View 1) shows the thickness along Y? No, top view looks down Z.
    // If the cylinder axis is Y, looking down Z sees the side of the cylinder (a rectangle).
    // The width of that rectangle in the top view (X axis) corresponds to the diameter.
    // The height of that rectangle in the top view (Y axis? No, top view is XY plane).
    // In the top view (XY plane), X is width, Y is depth.
    // If the cylinder axis is Y, the extent in Y is the thickness.
    // The extent in X is the diameter.
    // The extent in Z is the diameter.
    
    // Let's check the derived sizes.
    // width_mm (X) = 120.0. This matches the outer diameter.
    // depth_mm (Y) = 18.75. This is likely the thickness.
    // height_mm (Z) = 117.32. This is close to the diameter (120).
    
    // So the object is a disk in the XZ plane, centered at origin?
    // "The part must sit on the build plate: lowest geometry at Z=0".
    // If it's a disk in XZ, it would be floating unless we shift it.
    // But a flange usually sits flat.
    // Let's reconsider the standard orientation.
    // Usually, a flange lies flat on the table.
    // If it lies flat, the face is in XY.
    // Then the Front view (looking down Y) would see the edge (rectangle).
    // The Top view (looking down Z) would see the circle.
    // BUT the prompt says:
    // View 2 (front) constrains "Outer diameter, center bore...". View 2 shows the circle.
    // View 1 (top) constrains "Flange thickness". View 1 shows a rectangle.
    // This implies the "Front" view is the face view.
    // If the Front view is the face view, the face is in XZ.
    // This means the flange is standing up.
    // To sit on the build plate (Z=0), the bottom of the circle must be at Z=0.
    // So the center of the circle is at Z = outer_diameter / 2.
    // The thickness is along Y.
    // The "Top" view (looking down Z) sees the thickness (Y) and width (X).
    // The rectangle in View 1 has width 120 (X) and height 18.75 (Y).
    // This confirms: Axis of cylinder is Y.
    // Center of cylinder is at (0, 0, outer_diameter/2).
    // Wait, if it sits on Z=0, the lowest point is Z=0.
    // The cylinder extends from Z=0 to Z=outer_diameter.
    // The Y extent is -thickness/2 to +thickness/2? Or 0 to thickness?
    // "front through-features cut along Y".
    // If the body is centered at Y=0, the cutters go along Y.
    
    // Let's build the positive body:
    // A cylinder with axis along Y.
    // Radius = outer_diameter / 2.
    // Height (along Y) = thickness.
    // Position: Centered in X and Y, but shifted in Z so bottom is at 0.
    // Center Z = outer_diameter / 2.
    
    translate([0, 0, outer_diameter / 2])
        rotate([90, 0, 0]) // Rotate Z-axis cylinder to Y-axis
            cylinder(h=thickness, r=outer_diameter/2, center=true);
}

// Module: Center bore cutter
module center_bore_cutter() {
    // Cuts along Y (axis of the flange)
    translate([0, 0, outer_diameter / 2])
        rotate([90, 0, 0])
            cylinder(h=thickness + 2*eps, d=bore_diameter, center=true);
}

// Module: Bolt hole cutter
module bolt_hole_cutter(angle_deg) {
    // Bolt holes are on a circle in the XZ plane (face of the flange)
    // Center of flange face is at (0, 0, outer_diameter/2)
    // Radius of bolt circle
    r_bolt = bolt_circle_diameter / 2;
    
    // Calculate position in XZ plane relative to flange center
    // Angle 0 is typically +X. 
    // The view shows 4 holes. Symmetric.
    // Let's place them at 45, 135, 225, 315 degrees? 
    // Or 0, 90, 180, 270?
    // The drawing shows holes at corners of a square.
    // If the square is aligned with axes, holes are at 45 deg offsets from axes?
    // Or are the holes on the axes?
    // "Top-left", "Top-right" etc.
    // If we look at the front view (XZ), "Top" is +Z, "Left" is -X.
    // So Top-Left is (-X, +Z).
    // This corresponds to angle 135 degrees (if 0 is +X, 90 is +Z).
    // Top-Right is (+X, +Z) -> 45 degrees.
    // Bottom-Right is (+X, -Z) -> -45 (315) degrees.
    // Bottom-Left is (-X, -Z) -> 225 degrees.
    
    // So the angles are 45, 135, 225, 315.
    
    // Position relative to flange center (0,0,0 in local rotated frame)
    // In the global frame, the flange center is at (0, 0, outer_diameter/2).
    // The hole is at:
    // X = r_bolt * cos(angle)
    // Z_local = r_bolt * sin(angle)
    // Global Z = outer_diameter/2 + Z_local
    
    // The cutter axis is along Y.
    
    translate([
        r_bolt * cos(angle_deg),
        0,
        outer_diameter / 2 + r_bolt * sin(angle_deg)
    ])
        rotate([90, 0, 0])
            cylinder(h=thickness + 2*eps, d=bolt_hole_diameter, center=true);
}

// Main Design
difference() {
    flange_body();
    
    center_bore_cutter();
    
    // Four bolt holes at 45, 135, 225, 315 degrees
    bolt_hole_cutter(45);
    bolt_hole_cutter(135);
    bolt_hole_cutter(225);
    bolt_hole_cutter(315);
}
