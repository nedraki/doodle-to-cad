/* doodle-meta {"version":1,"parameters":{"width":{"label":"Overall width","description":"Changes the body width","unit":"mm","feature":"body_width"},"depth":{"label":"Overall depth","description":"Changes the body depth","unit":"mm","feature":"body_depth"},"thickness":{"label":"Plate thickness","description":"Changes the plate thickness","unit":"mm","feature":"body_thickness"},"notch_width":{"label":"Notch width","description":"Changes the width of the top notch","unit":"mm","feature":"notch"},"notch_depth":{"label":"Notch depth","description":"Changes the depth of the top notch","unit":"mm","feature":"notch"},"fillet_radius":{"label":"Fillet radius","description":"Changes the radius of the top-right corner fillet","unit":"mm","feature":"fillet"},"hole_diameter":{"label":"Hole diameter","description":"Changes the diameter of the through hole","unit":"mm","feature":"hole"},"hole_x":{"label":"Hole X position","description":"Changes the X position of the through hole","unit":"mm","feature":"hole"},"hole_y":{"label":"Hole Y position","description":"Changes the Y position of the through hole","unit":"mm","feature":"hole"}},"features":{"body_width":{"kind":"dimension","axis":"x","label":"Overall width"},"body_depth":{"kind":"dimension","axis":"y","label":"Overall depth"},"body_thickness":{"kind":"dimension","axis":"z","label":"Plate thickness"},"notch":{"kind":"region","label":"Top Notch","min":[{"parameter":"width","scale":0.3333,"offset":0},{"parameter":"depth","scale":1.0,"offset":0},0],"max":[{"parameter":"width","scale":0.6667,"offset":0},{"parameter":"depth","scale":1.0,"offset":0},{"parameter":"thickness","scale":1.0,"offset":0}]},"fillet":{"kind":"region","label":"Top-Right Fillet","min":[{"parameter":"width","scale":1.0,"offset":-6},{"parameter":"depth","scale":1.0,"offset":-6},0],"max":[{"parameter":"width","scale":1.0,"offset":0},{"parameter":"depth","scale":1.0,"offset":0},{"parameter":"thickness","scale":1.0,"offset":0}]},"hole":{"kind":"region","label":"Through Hole","min":[{"parameter":"hole_x","scale":1.0,"offset":-4},{"parameter":"hole_y","scale":1.0,"offset":-4},0],"max":[{"parameter":"hole_x","scale":1.0,"offset":4},{"parameter":"hole_y","scale":1.0,"offset":4},{"parameter":"thickness","scale":1.0,"offset":0}]}}} */

// Top-level parameters (user-editable)
width = 60;
depth = 40;
thickness = 6;
notch_width = 20;
notch_depth = 10;
fillet_radius = 6;
hole_diameter = 8;
hole_x = 12;
hole_y = 15;

// Derived constants (not user-editable)
eps = 0.01;

// Main design
difference() {
    // Positive body: rectangular plate with fillet on top-right corner
    union() {
        // Main rectangular body
        cube([width, depth, thickness]);
        
        // Fillet on top-right corner (X=width, Y=depth)
        // Create a cylinder that fills the corner, then subtract the square part
        translate([width - fillet_radius, depth - fillet_radius, 0])
            cylinder(h = thickness, r = fillet_radius, $fn = 32);
    }
    
    // Subtract the square part of the fillet corner to make it round
    // The fillet cylinder is at (width-fr, depth-fr), so we need to remove the square corner
    // Actually, the union above adds a cylinder at the corner. We need to ensure the corner is rounded.
    // Let's rethink: The base cube has sharp corners. We want to round the top-right corner (X=width, Y=depth).
    // To do this properly: create the base shape as a polygon extruded, or use difference to cut the corner.
    
    // Better approach: Start with full cube, then cut the corner with a cylinder subtraction approach.
    // But we already unioned a cylinder. Let's correct the approach.
    
    // Correct approach: 
    // 1. Create the base plate as a cube.
    // 2. Cut out the notch from the top edge (Y=depth side).
    // 3. Cut out the hole.
    // 4. Round the top-right corner by cutting with a cylinder.
    
    // Let me restart the geometry logic properly.
}

// Let me rewrite the entire design with correct CSG logic.

// Clear and restart
difference() {
    // Base plate
    cube([width, depth, thickness]);
    
    // Cut the top-right corner (X=width, Y=depth) to create fillet
    // The corner to round is at (width, depth). We cut a cylinder centered at (width, depth) with radius fillet_radius.
    // But we want to keep the material inside the fillet radius, so we subtract the area outside the fillet.
    // Actually, to round a corner: subtract a cylinder from the corner region.
    // The cylinder should be centered at (width, depth) and we subtract the part that extends beyond the fillet.
    // Wait - to create a fillet (rounded corner), we need to remove the sharp corner material.
    // The sharp corner is at (width, depth). We want to replace it with a quarter-circle of radius fillet_radius.
    // So we subtract a cylinder centered at (width, depth) with radius fillet_radius? No, that would remove too much.
    // 
    // Correct: The fillet means the corner is rounded inward. The material near (width, depth) is removed.
    // We subtract a cylinder centered at (width, depth) with radius fillet_radius, but only the part that is 
    // outside the desired rounded boundary. Actually, the standard way:
    // The rounded corner means the boundary follows a quarter circle from (width-fr, depth) to (width, depth-fr).
    // So we need to subtract the region that is outside this quarter circle but inside the original corner.
    // 
    // Simpler: Create the plate as a polygon in XY, then extrude.
    
    // Let me use a different approach: define the 2D profile and extrude.
}

// Final correct implementation using polygon extrusion for the base shape

// Define the 2D profile of the plate (XY plane) with fillet on top-right corner
// Top-right corner is at (width, depth). Fillet radius = fillet_radius.
// The profile goes: (0,0) -> (width,0) -> (width, depth-fr) -> arc to (width-fr, depth) -> (0, depth) -> (0,0)

module plate_profile() {
    // Create the 2D polygon for the plate with rounded top-right corner
    // Points: bottom-left, bottom-right, right side up to fillet start, fillet arc, top side from fillet end, top-left
    fr = fillet_radius;
    steps = 16;
    
    polygon([
        [0, 0],
        [width, 0],
        [width, depth - fr],
        // Fillet arc from (width, depth-fr) to (width-fr, depth)
        for (i = [0:steps]) let(
            angle = 90 * i / steps,
            rad = 90 - angle,
            x = width - fr + fr * cos(rad),
            y = depth - fr + fr * sin(rad)
        ) [x, y],
        [0, depth]
    ]);
}

difference() {
    // Extrude the plate profile
    linear_extrude(height = thickness)
        plate_profile();
    
    // Cut the notch from the top edge (Y=depth side)
    // Notch is centered on top edge, width=notch_width, depth=notch_depth
    // Top edge is at Y=depth. Notch extends inward (decreasing Y) by notch_depth.
    // Notch X range: centered, so from (width-notch_width)/2 to (width+notch_width)/2
    translate([(width - notch_width) / 2, depth - notch_depth, -eps])
        cube([notch_width, notch_depth + eps, thickness + 2 * eps]);
    
    // Cut the through hole
    // Hole at (hole_x, hole_y), diameter=hole_diameter, through Z
    translate([hole_x, hole_y, -eps])
        cylinder(h = thickness + 2 * eps, d = hole_diameter, $fn = 32);
}
