/* doodle-meta {"version":1,"parameters":{"width":{"label":"Overall width","description":"Changes the body width","unit":"mm","feature":"body_width"},"depth":{"label":"Overall depth","description":"Changes the body depth","unit":"mm","feature":"body_depth"},"thickness":{"label":"Thickness","description":"Changes the plate thickness","unit":"mm","feature":"body_thickness"},"notch_width":{"label":"Notch width","description":"Changes the width of the top notch","unit":"mm","feature":"notch"},"notch_depth":{"label":"Notch depth","description":"Changes the depth of the top notch","unit":"mm","feature":"notch"},"hole_diameter":{"label":"Hole diameter","description":"Changes the diameter of the through-hole","unit":"mm","feature":"hole"},"hole_x":{"label":"Hole X position","description":"Changes the X position of the hole","unit":"mm","feature":"hole"},"hole_y":{"label":"Hole Y position","description":"Changes the Y position of the hole","unit":"mm","feature":"hole"},"fillet_radius":{"label":"Fillet radius","description":"Changes the radius of the top-right corner fillet","unit":"mm","feature":"fillet"}},"features":{"body_width":{"kind":"dimension","axis":"x","label":"Overall width"},"body_depth":{"kind":"dimension","axis":"y","label":"Overall depth"},"body_thickness":{"kind":"dimension","axis":"z","label":"Thickness"},"notch":{"kind":"region","label":"Top Notch","min":[{"parameter":"width","scale":0.5,"offset":-10},{"parameter":"depth","scale":1.0,"offset":-10},0],"max":[{"parameter":"width","scale":0.5,"offset":10},{"parameter":"depth","scale":1.0,"offset":0},{"parameter":"thickness","scale":1.0,"offset":0}]},"hole":{"kind":"region","label":"Through Hole","min":[{"parameter":"hole_x","scale":1.0,"offset":-4},{"parameter":"hole_y","scale":1.0,"offset":-4},0],"max":[{"parameter":"hole_x","scale":1.0,"offset":4},{"parameter":"hole_y","scale":1.0,"offset":4},{"parameter":"thickness","scale":1.0,"offset":0}]},"fillet":{"kind":"region","label":"Top-Right Fillet","min":[{"parameter":"width","scale":1.0,"offset":-6},{"parameter":"depth","scale":1.0,"offset":-6},0],"max":[{"parameter":"width","scale":1.0,"offset":0},{"parameter":"depth","scale":1.0,"offset":0},{"parameter":"thickness","scale":1.0,"offset":0}]}}} */

// Parameters
width = 60;
depth = 40;
thickness = 6;
notch_width = 20;
notch_depth = 10;
hole_diameter = 8;
hole_x = 12;
hole_y = 15;
fillet_radius = 6;

// Derived constants
eps = 0.01;

// Main design
difference() {
    // Base body with fillet
    body_with_fillet();
    
    // Subtract notch
    notch_cutter();
    
    // Subtract hole
    hole_cutter();
}

// Module for the main body with top-right fillet
module body_with_fillet() {
    // Main rectangular body
    cube([width, depth, thickness]);
    
    // Add fillet at top-right corner (X=width, Y=depth)
    // The fillet replaces the sharp corner with a quarter cylinder
    // We need to add material where the fillet curves inward
    // Actually, we need to subtract the corner and add the fillet
    // Better approach: create the body as a union of the main rect minus corner plus fillet
    
    // Let's rebuild: create full rect, subtract corner square, add fillet cylinder
    // But since we're in difference(), let's handle this differently
    // We'll create the body shape properly here
    
    // Full rectangle
    translate([0, 0, 0])
        cube([width, depth, thickness]);
    
    // Add fillet: a quarter cylinder at the top-right corner
    // The fillet center is at (width - fillet_radius, depth - fillet_radius)
    // We need to add the material that fills the corner curve
    // Actually, the fillet means the corner is rounded, so we subtract the sharp corner
    // and the fillet is part of the body shape
    
    // Correct approach: The body is the rectangle MINUS the corner square PLUS the quarter cylinder
    // But since we want a clean shape, let's use a different method:
    // Create the body as: rectangle with corner cut, then union with fillet cylinder
    
    // For simplicity in this context, let's create the body properly:
    // The body should be the rectangle minus the corner triangle/square area, 
    // but with the fillet curve. 
    
    // Simplest correct approach: 
    // 1. Start with full rectangle
    // 2. Subtract a square at the corner (fillet_radius x fillet_radius)
    // 3. Union with a quarter cylinder of radius fillet_radius
    
    // But we're already in a difference() block. Let me restructure.
}

// Let me restructure the main design properly:

difference() {
    // Positive body: rectangle with fillet
    union() {
        // Main rectangle minus the corner square
        difference() {
            cube([width, depth, thickness]);
            // Subtract the corner square at top-right
            translate([width - fillet_radius, depth - fillet_radius, -eps])
                cube([fillet_radius + eps, fillet_radius + eps, thickness + 2*eps]);
        }
        
        // Add the fillet (quarter cylinder) at top-right corner
        // Center of the fillet arc is at (width - fillet_radius, depth - fillet_radius)
        translate([width - fillet_radius, depth - fillet_radius, -eps])
            cylinder(h = thickness + 2*eps, r = fillet_radius, center = false);
    }
    
    // Subtract the notch from the top edge (Y=depth side)
    // Notch is centered at X=width/2, extends from Y=depth down by notch_depth
    translate([width/2 - notch_width/2, depth - notch_depth, -eps])
        cube([notch_width, notch_depth + eps, thickness + 2*eps]);
    
    // Subtract the through-hole
    // Hole is at (hole_x, hole_y), diameter hole_diameter, through Z
    translate([hole_x, hole_y, -eps])
        cylinder(h = thickness + 2*eps, d = hole_diameter, center = false);
}
