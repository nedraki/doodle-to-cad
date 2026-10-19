/* doodle-meta {"version":1,"parameters":{"width":{"label":"Overall width","description":"Changes the body width","unit":"mm","feature":"body_width"},"depth":{"label":"Overall depth","description":"Changes the body depth","unit":"mm","feature":"body_depth"},"thickness":{"label":"Thickness","description":"Changes the plate thickness","unit":"mm","feature":"body_thickness"},"notch_width":{"label":"Notch width","description":"Changes the width of the top notch","unit":"mm","feature":"notch"},"notch_depth":{"label":"Notch depth","description":"Changes the depth of the top notch","unit":"mm","feature":"notch"},"hole_diameter":{"label":"Hole diameter","description":"Changes the diameter of the through hole","unit":"mm","feature":"hole"},"hole_x":{"label":"Hole X position","description":"Changes the X position of the hole center","unit":"mm","feature":"hole"},"hole_y":{"label":"Hole Y position","description":"Changes the Y position of the hole center","unit":"mm","feature":"hole"},"fillet_radius":{"label":"Fillet radius","description":"Changes the radius of the top-right corner fillet","unit":"mm","feature":"fillet"}},"features":{"body_width":{"kind":"dimension","axis":"x","label":"Overall width"},"body_depth":{"kind":"dimension","axis":"y","label":"Overall depth"},"body_thickness":{"kind":"dimension","axis":"z","label":"Thickness"},"notch":{"kind":"region","label":"Top Notch","min":[{"parameter":"width","scale":0.5,"offset":-10},{"parameter":"depth","scale":1,"offset":-10},0],"max":[{"parameter":"width","scale":0.5,"offset":10},{"parameter":"depth","scale":1,"offset":0},{"parameter":"thickness","scale":1,"offset":0}]},"hole":{"kind":"region","label":"Through Hole","min":[{"parameter":"hole_x","scale":1,"offset":-4},{"parameter":"hole_y","scale":1,"offset":-4},0],"max":[{"parameter":"hole_x","scale":1,"offset":4},{"parameter":"hole_y","scale":1,"offset":4},{"parameter":"thickness","scale":1,"offset":0}]},"fillet":{"kind":"region","label":"Top Right Fillet","min":[{"parameter":"width","scale":1,"offset":-6},{"parameter":"depth","scale":1,"offset":-6},0],"max":[{"parameter":"width","scale":1,"offset":0},{"parameter":"depth","scale":1,"offset":0},{"parameter":"thickness","scale":1,"offset":0}]}}} */

// Top-level parameters (allowlist)
width = 60;
depth = 40;
thickness = 6;
notch_width = 20;
notch_depth = 10;
hole_diameter = 8;
hole_x = 12;
hole_y = 15;
fillet_radius = 6;

// Derived constants (not in allowlist)
eps = 0.01;

// Main design
notched_plate();

module notched_plate() {
    difference() {
        // Positive body: extruded profile with fillet
        union() {
            // Main rectangular body
            cube([width, depth, thickness]);
            
            // Fillet at top-right corner (X=width, Y=depth)
            // The fillet replaces the sharp corner. We add a quarter cylinder 
            // and subtract the corner cube to create the rounded effect, 
            // or more simply, we can model the base shape with the fillet included.
            // However, standard CSG approach:
            // 1. Start with full rectangle.
            // 2. Subtract the corner square.
            // 3. Add the quarter cylinder.
            // But since we are using difference() for the whole object, 
            // it's cleaner to build the positive shape first.
            
            // Let's rebuild the positive shape properly:
            // Base rectangle minus corner square plus quarter cylinder
        }
        
        // Subtract the notch
        notch_cutter();
        
        // Subtract the hole
        hole_cutter();
    }
}

// Helper to build the positive body with fillet
module positive_body() {
    // The main body is a rectangle with a filleted corner.
    // We can construct this by:
    // 1. A cube covering the whole area.
    // 2. Subtracting the corner square (width-fillet_radius to width, depth-fillet_radius to depth).
    // 3. Adding a quarter cylinder at the corner.
    
    // Since we are inside a difference() in the main module, 
    // we need to be careful. Let's restructure.
    
    // Actually, let's just define the positive geometry as a union of parts 
    // that form the correct shape, then subtract the cuts.
    
    // Part 1: The main block without the filleted corner
    // We can split the rectangle into:
    // - A large rectangle from (0,0) to (width, depth-fillet_radius)
    // - A rectangle from (0, depth-fillet_radius) to (width-fillet_radius, depth)
    // - A quarter cylinder at (width-fillet_radius, depth-fillet_radius)
    
    // This is complex. A simpler way for OpenSCAD:
    // Use a hull or minkowski? No, keep it simple.
    
    // Let's use the standard "subtract corner, add cylinder" approach 
    // but apply it to the positive shape before the final difference.
    
    // Wait, the main module is `difference()`. 
    // The first argument is the positive shape.
    // So I should define a module `base_shape()` that returns the solid plate with fillet.
    
    // Let's rewrite the main module to use a helper for the base shape.
}

// Redefining the main module for clarity and correctness
module notched_plate() {
    difference() {
        base_plate();
        notch_cutter();
        hole_cutter();
    }
}

module base_plate() {
    // Construct the plate with the fillet on the top-right corner (X=width, Y=depth)
    
    // 1. Main body excluding the corner square
    // We can create the shape by unioning:
    // - A rectangle covering most of the plate
    // - A quarter cylinder for the corner
    
    // Rectangle 1: Full width, height up to (depth - fillet_radius)
    // This covers the bottom part and the left part of the top strip.
    // Actually, let's do:
    // - Rectangle from (0,0) to (width, depth - fillet_radius)
    // - Rectangle from (0, depth - fillet_radius) to (width - fillet_radius, depth)
    // - Quarter cylinder at (width - fillet_radius, depth - fillet_radius)
    
    // Rectangle 1: Bottom section
    translate([0, 0, 0])
        cube([width, depth - fillet_radius, thickness]);
        
    // Rectangle 2: Top-left section (excluding the corner)
    translate([0, depth - fillet_radius, 0])
        cube([width - fillet_radius, fillet_radius, thickness]);
        
    // Quarter Cylinder: Top-right corner
    // Center of the full cylinder would be at (width - fillet_radius, depth - fillet_radius)
    // We want the quarter that fills the corner (X > width-fr, Y > depth-fr)
    // A cylinder centered at (width-fr, depth-fr) with radius fr.
    // We need to intersect it with the corner box to get the quarter.
    // Or simpler: 
    // Create a cylinder centered at (width-fr, depth-fr).
    // Intersect with a cube from (width-fr, depth-fr) to (width, depth).
    
    translate([width - fillet_radius, depth - fillet_radius, 0])
        intersection() {
            cylinder(h = thickness, r = fillet_radius, center = false);
            // The cylinder is centered at the corner of the intersection box?
            // No, cylinder center is at (0,0) in local coords.
            // We want the quadrant where x>0, y>0.
            // So we intersect with a cube starting at 0,0.
            translate([0, 0, 0])
                cube([fillet_radius, fillet_radius, thickness]);
        }
}

module notch_cutter() {
    // Notch is on the top edge (Y=depth), centered on X.
    // Width: notch_width, Depth: notch_depth.
    // It cuts through the thickness.
    
    // Center X is width/2.
    // The notch extends from Y = depth - notch_depth to Y = depth.
    // X extends from (width/2 - notch_width/2) to (width/2 + notch_width/2).
    
    translate([width/2 - notch_width/2, depth - notch_depth, -eps])
        cube([notch_width, notch_depth + eps, thickness + 2*eps]);
}

module hole_cutter() {
    // Hole is at (hole_x, hole_y).
    // Diameter: hole_diameter.
    // Through the thickness.
    
    // Cylinder axis is Z.
    translate([hole_x, hole_y, -eps])
        cylinder(h = thickness + 2*eps, d = hole_diameter, center = false);
}
