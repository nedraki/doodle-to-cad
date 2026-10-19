/* doodle-meta {"version":1,"parameters":{"plate_width":{"label":"Plate Width","description":"Overall width of the plate along X","unit":"mm","feature":"body_width"},"plate_depth":{"label":"Plate Depth","description":"Overall depth of the plate along Y","unit":"mm","feature":"body_depth"},"plate_thickness":{"label":"Plate Thickness","description":"Thickness of the plate along Z","unit":"mm","feature":"body_thickness"},"notch_width":{"label":"Notch Width","description":"Width of the notch cut from the back edge","unit":"mm","feature":"notch"},"notch_depth":{"label":"Notch Depth","description":"Depth of the notch cut from the back edge","unit":"mm","feature":"notch"},"fillet_radius":{"label":"Fillet Radius","description":"Radius of the fillet on the back-right corner","unit":"mm","feature":"fillet"},"hole_diameter":{"label":"Hole Diameter","description":"Diameter of the through hole","unit":"mm","feature":"hole"},"hole_x":{"label":"Hole X Position","description":"X position of the hole center from left edge","unit":"mm","feature":"hole"},"hole_y":{"label":"Hole Y Position","description":"Y position of the hole center from front edge","unit":"mm","feature":"hole"}},"features":{"body_width":{"kind":"dimension","axis":"x","label":"Overall Width"},"body_depth":{"kind":"dimension","axis":"y","label":"Overall Depth"},"body_thickness":{"kind":"dimension","axis":"z","label":"Thickness"},"notch":{"kind":"region","label":"Top Edge Notch","min":[{"parameter":"plate_width","scale":0.5,"offset":-10},{"parameter":"plate_depth","scale":1.0,"offset":0},0],"max":[{"parameter":"plate_width","scale":0.5,"offset":10},{"parameter":"plate_depth","scale":1.0,"offset":10},{"parameter":"plate_thickness","scale":1.0,"offset":0}]},"fillet":{"kind":"region","label":"Top-Right Fillet","min":[{"parameter":"plate_width","scale":1.0,"offset":-6},{"parameter":"plate_depth","scale":1.0,"offset":-6},0],"max":[{"parameter":"plate_width","scale":1.0,"offset":0},{"parameter":"plate_depth","scale":1.0,"offset":0},{"parameter":"plate_thickness","scale":1.0,"offset":0}]},"hole":{"kind":"region","label":"Through Hole","min":[{"parameter":"hole_x","scale":1.0,"offset":-4},{"parameter":"hole_y","scale":1.0,"offset":-4},0],"max":[{"parameter":"hole_x","scale":1.0,"offset":4},{"parameter":"hole_y","scale":1.0,"offset":4},{"parameter":"plate_thickness","scale":1.0,"offset":0}]}}} */

// Parameters
plate_width = 60;
plate_depth = 40;
plate_thickness = 6;
notch_width = 20;
notch_depth = 10;
fillet_radius = 6;
hole_diameter = 8;
hole_x = 12;
hole_y = 15;

// Derived constants
eps = 0.01;

// Main Design
difference() {
    // 1. Base Plate
    cube([plate_width, plate_depth, plate_thickness]);

    // 2. Notch Cutout (Back Edge, Centered)
    // Back edge is at Y = plate_depth.
    // Notch cuts from Y = plate_depth - notch_depth to Y = plate_depth + eps
    // Centered on X: X from (plate_width - notch_width)/2 to (plate_width + notch_width)/2
    translate([
        (plate_width - notch_width) / 2,
        plate_depth - notch_depth,
        -eps
    ])
    cube([
        notch_width,
        notch_depth + eps,
        plate_thickness + 2 * eps
    ]);

    // 3. Fillet Cutout (Back-Right Corner)
    // Corner is at (plate_width, plate_depth).
    // We subtract a square of size fillet_radius x fillet_radius at the corner,
    // and add back a cylinder of radius fillet_radius to create the rounded corner.
    // This effectively rounds the corner.
    // The square to subtract is at X: [plate_width - fillet_radius, plate_width]
    // Y: [plate_depth - fillet_radius, plate_depth]
    // We use a difference inside the main difference? No, we can just subtract the "corner square minus cylinder".
    // Or simpler: Subtract the square, then Union the cylinder? No, we are in a difference block.
    // We need to subtract the material that is OUTSIDE the fillet but INSIDE the corner square.
    // Material to remove = Square - Cylinder.
    // So we subtract (Square - Cylinder).
    // This is equivalent to: difference() { Square; Cylinder; }
    // But we are already in a difference. So we can just subtract the Square, and then Union the Cylinder back?
    // No, the structure is difference() { Base; Cutters; }.
    // If we subtract the Square, we lose the corner. We want to keep the rounded part.
    // So we should NOT subtract the whole square. We should subtract (Square - Cylinder).
    // In OpenSCAD, difference() { A; B; } removes B from A.
    // To remove (Square - Cylinder), we can do:
    // difference() {
    //    Base;
    //    translate(...) {
    //       difference() {
    //          cube([fillet_radius, fillet_radius, ...]);
    //          cylinder(...);
    //       }
    //    }
    // }
    
    translate([
        plate_width - fillet_radius,
        plate_depth - fillet_radius,
        -eps
    ])
    difference() {
        cube([fillet_radius, fillet_radius, plate_thickness + 2 * eps]);
        translate([0, 0, -eps])
        cylinder(h = plate_thickness + 2 * eps, r = fillet_radius, center = false);
    }

    // 4. Through Hole
    // Position (hole_x, hole_y) from bottom-left (0,0).
    // Cylinder axis is Z.
    translate([hole_x, hole_y, -eps])
    cylinder(h = plate_thickness + 2 * eps, d = hole_diameter, center = false);
}
