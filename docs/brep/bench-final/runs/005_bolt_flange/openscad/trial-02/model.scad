/* doodle-meta {"version":1,"parameters":{"outer_diameter":{"label":"Outer Diameter","description":"Diameter of the flange body","unit":"mm","feature":"outer_profile"},"thickness":{"label":"Thickness","description":"Height of the flange plate","unit":"mm","feature":"body_thickness"},"bore_diameter":{"label":"Center Bore Diameter","description":"Diameter of the central through-hole","unit":"mm","feature":"center_bore"},"bolt_hole_diameter":{"label":"Bolt Hole Diameter","description":"Diameter of the four peripheral bolt holes","unit":"mm","feature":"bolt_holes"},"bolt_hole_offset":{"label":"Bolt Hole Offset","description":"Distance from center to bolt hole centers (X and Y)","unit":"mm","feature":"bolt_holes"}},"features":{"outer_profile":{"kind":"dimension","axis":"x","label":"Outer Diameter"},"body_thickness":{"kind":"dimension","axis":"z","label":"Thickness"},"center_bore":{"kind":"region","label":"Center Bore","min":[0,0,0],"max":[0,0,0]},"bolt_holes":{"kind":"region","label":"Bolt Holes","min":[0,0,0],"max":[0,0,0]}}} */

// Parameters
outer_diameter = 120;
thickness = 10;
bore_diameter = 40;
bolt_hole_diameter = 12;
bolt_hole_offset = 35;

// Derived constants
$fn = 64;
eps = 0.01;

// Main Design
difference() {
    // 1. Positive Body: Circular plate
    // The flange sits on the build plate (Z=0) and extends up to Z=thickness.
    // The front view (looking down Y) shows the circular profile in XZ.
    // The top view (looking down Z) shows the circular profile in XY.
    // Since it's a flange, the "front" view in the prompt description likely refers to the face with the holes,
    // which is the XY plane if the flange is lying flat, or XZ if standing up.
    // Standard flange orientation for printing is usually flat on the bed.
    // However, the prompt says "front geometry lies in XZ". This implies the flange is standing up?
    // Let's re-read carefully: "front geometry lies in XZ and front through-features cut along Y".
    // If the flange is a disk, and the front view shows the circle, then the disk face is in XZ.
    // This means the disk is vertical, like a wheel.
    // The "top" view constrains thickness. Top view looks down Z.
    // If the disk is in XZ, its thickness is along Y.
    // So the flange is a vertical disk of thickness Y.
    
    // Let's verify with the "previous_candidate_failures":
    // "Y=119.343 mm vs expected 18.75 mm, Z=10 mm vs expected 117.32 mm"
    // This suggests the previous attempt had the disk in XY (Z=10 thickness) and failed because
    // the system expected the disk to be in XZ (Y=thickness, Z=diameter).
    // Wait, the derived sizes say:
    // width_mm (X) = 120
    // depth_mm (Y) = 18.75
    // height_mm (Z) = 117.32
    // This confirms the flange is standing up in the XZ plane.
    // X is width (diameter), Z is height (diameter), Y is depth (thickness).
    
    // So:
    // Body: Cylinder with axis along Y.
    // Diameter: 120mm (in XZ plane).
    // Height (Thickness): 18.75mm (along Y).
    // Centered at X=0, Z=0? No, "lowest geometry at Z=0".
    // So the cylinder center is at Z = outer_diameter / 2.
    // And Y is centered? Or from 0 to thickness?
    // "top geometry lies in XY and cuts along Z".
    // If the flange is vertical, the "top" view is looking down Z.
    // The top view shows the thickness (Y) and width (X).
    // The prompt says "top view ... constrains Flange thickness (height)".
    // In the derived sizes, depth_mm (Y) is 18.75. This is the thickness.
    
    // Let's construct the body:
    // A cylinder along Y axis.
    // Radius = outer_diameter / 2.
    // Height = thickness (along Y).
    // Position: Centered in X (0), Centered in Y (0 to thickness? or -t/2 to t/2?).
    // "lowest geometry at Z=0".
    // So Z ranges from 0 to outer_diameter.
    // Y ranges from 0 to thickness (or centered). Let's center it in Y for symmetry, or start at 0.
    // Usually, we center the main body and then shift.
    // Let's place the cylinder center at (0, 0, outer_diameter/2).
    // The cylinder axis is Y.
    // So we rotate a standard Z-cylinder by 90 degrees around X to align it with Y.
    
    translate([0, 0, outer_diameter/2])
        rotate([90, 0, 0])
            cylinder(h=thickness, r=outer_diameter/2, center=true);

    // 2. Subtract Center Bore
    // Through hole along Y (the thickness axis).
    // Diameter: bore_diameter.
    // Center: (0, 0, outer_diameter/2).
    translate([0, 0, outer_diameter/2])
        rotate([90, 0, 0])
            cylinder(h=thickness + 2*eps, r=bore_diameter/2, center=true);

    // 3. Subtract Bolt Holes
    // Four holes, symmetric pattern.
    // Positions in XZ plane (front view):
    // The prompt says bolt holes are at (35, 35), (-35, 35), etc. in the "front" view.
    // Front view is XZ.
    // So X offsets are +/- 35.
    // Z offsets are +/- 35 relative to the center of the flange.
    // The center of the flange is at Z = outer_diameter/2.
    // So the Z coordinates of the holes are (outer_diameter/2) +/- 35.
    
    // Hole 1: X=35, Z=outer_diameter/2 + 35
    // Hole 2: X=-35, Z=outer_diameter/2 + 35
    // Hole 3: X=-35, Z=outer_diameter/2 - 35
    // Hole 4: X=35, Z=outer_diameter/2 - 35
    
    // All holes cut along Y.
    
    // Hole 1
    translate([bolt_hole_offset, 0, outer_diameter/2 + bolt_hole_offset])
        rotate([90, 0, 0])
            cylinder(h=thickness + 2*eps, r=bolt_hole_diameter/2, center=true);
            
    // Hole 2
    translate([-bolt_hole_offset, 0, outer_diameter/2 + bolt_hole_offset])
        rotate([90, 0, 0])
            cylinder(h=thickness + 2*eps, r=bolt_hole_diameter/2, center=true);
            
    // Hole 3
    translate([-bolt_hole_offset, 0, outer_diameter/2 - bolt_hole_offset])
        rotate([90, 0, 0])
            cylinder(h=thickness + 2*eps, r=bolt_hole_diameter/2, center=true);
            
    // Hole 4
    translate([bolt_hole_offset, 0, outer_diameter/2 - bolt_hole_offset])
        rotate([90, 0, 0])
            cylinder(h=thickness + 2*eps, r=bolt_hole_diameter/2, center=true);
}
