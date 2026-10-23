/* doodle-meta {"version":1,"parameters":{"width":{"label":"Overall width","description":"Changes the body width along X","unit":"mm","feature":"body_width"},"depth":{"label":"Overall depth","description":"Changes the body depth along Y","unit":"mm","feature":"body_depth"},"height":{"label":"Overall height","description":"Changes the body height along Z","unit":"mm","feature":"body_height"},"chamfer_size":{"label":"Chamfer size","description":"Size of the 45-degree chamfer on all edges","unit":"mm","feature":"chamfer"}},"features":{"body_width":{"kind":"dimension","axis":"x","label":"Overall width"},"body_depth":{"kind":"dimension","axis":"y","label":"Overall depth"},"body_height":{"kind":"dimension","axis":"z","label":"Overall height"},"chamfer":{"kind":"region","label":"Chamfered edges","min":[0,0,0],"max":[{"parameter":"width","scale":1,"offset":0},{"parameter":"depth","scale":1,"offset":0},{"parameter":"height","scale":1,"offset":0}]}}} */

// User-editable parameters
width = 80.0;
depth = 43.09;
height = 5.69;
chamfer_size = 2.0;

// Derived constants (not user-editable)
eps = 0.01;

// Module to create the chamfered block
module chamfered_block() {
    // Start with the main rectangular block
    // Positioned so the bottom is at Z=0
    difference() {
        // Main body
        cube([width, depth, height], center=false);
        
        // Subtract chamfers from all 12 edges
        
        // 4 Vertical edges (along Z)
        // Bottom-Left-Front (X=0, Y=0)
        translate([0, 0, -eps])
            rotate([0, 0, 45])
                cube([chamfer_size * sqrt(2), chamfer_size * sqrt(2), height + 2*eps], center=true);
                
        // Bottom-Right-Front (X=width, Y=0)
        translate([width, 0, -eps])
            rotate([0, 0, -45])
                cube([chamfer_size * sqrt(2), chamfer_size * sqrt(2), height + 2*eps], center=true);
                
        // Bottom-Left-Back (X=0, Y=depth)
        translate([0, depth, -eps])
            rotate([0, 0, 135])
                cube([chamfer_size * sqrt(2), chamfer_size * sqrt(2), height + 2*eps], center=true);
                
        // Bottom-Right-Back (X=width, Y=depth)
        translate([width, depth, -eps])
            rotate([0, 0, -135])
                cube([chamfer_size * sqrt(2), chamfer_size * sqrt(2), height + 2*eps], center=true);

        // 4 Horizontal edges along X (Top and Bottom, Front and Back faces)
        // Bottom-Front (Y=0, Z=0)
        translate([-eps, 0, 0])
            rotate([45, 0, 0])
                cube([width + 2*eps, chamfer_size * sqrt(2), chamfer_size * sqrt(2)], center=true);
                
        // Bottom-Back (Y=depth, Z=0)
        translate([-eps, depth, 0])
            rotate([-45, 0, 0])
                cube([width + 2*eps, chamfer_size * sqrt(2), chamfer_size * sqrt(2)], center=true);
                
        // Top-Front (Y=0, Z=height)
        translate([-eps, 0, height])
            rotate([-45, 0, 0])
                cube([width + 2*eps, chamfer_size * sqrt(2), chamfer_size * sqrt(2)], center=true);
                
        // Top-Back (Y=depth, Z=height)
        translate([-eps, depth, height])
            rotate([45, 0, 0])
                cube([width + 2*eps, chamfer_size * sqrt(2), chamfer_size * sqrt(2)], center=true);

        // 4 Horizontal edges along Y (Top and Bottom, Left and Right faces)
        // Bottom-Left (X=0, Z=0)
        translate([0, -eps, 0])
            rotate([0, -45, 0])
                cube([chamfer_size * sqrt(2), depth + 2*eps, chamfer_size * sqrt(2)], center=true);
                
        // Bottom-Right (X=width, Z=0)
        translate([width, -eps, 0])
            rotate([0, 45, 0])
                cube([chamfer_size * sqrt(2), depth + 2*eps, chamfer_size * sqrt(2)], center=true);
                
        // Top-Left (X=0, Z=height)
        translate([0, -eps, height])
            rotate([0, 45, 0])
                cube([chamfer_size * sqrt(2), depth + 2*eps, chamfer_size * sqrt(2)], center=true);
                
        // Top-Right (X=width, Z=height)
        translate([width, -eps, height])
            rotate([0, -45, 0])
                cube([chamfer_size * sqrt(2), depth + 2*eps, chamfer_size * sqrt(2)], center=true);
    }
}

// Instantiate the design
chamfered_block();
