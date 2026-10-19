/* doodle-meta {"version":1,"parameters":{"width":{"label":"Overall width","description":"Changes the body width","unit":"mm","feature":"body_width"},"depth":{"label":"Overall depth","description":"Changes the body depth","unit":"mm","feature":"body_depth"},"height":{"label":"Overall height","description":"Changes the body height","unit":"mm","feature":"body_height"},"wall_thickness":{"label":"Wall thickness","description":"Thickness of the vertical wall and base plate","unit":"mm","feature":"wall_thickness"},"hole_diameter":{"label":"Hole diameter","description":"Diameter of the circular mounting holes","unit":"mm","feature":"holes"},"slot_width":{"label":"Slot width","description":"Width of the rectangular slot","unit":"mm","feature":"slot"},"slot_height":{"label":"Slot height","description":"Height of the rectangular slot","unit":"mm","feature":"slot"}},"features":{"body_width":{"kind":"dimension","axis":"x","label":"Overall width"},"body_depth":{"kind":"dimension","axis":"y","label":"Overall depth"},"body_height":{"kind":"dimension","axis":"z","label":"Overall height"},"wall_thickness":{"kind":"region","label":"Wall thickness","min":[0,0,0],"max":[{"parameter":"width","scale":0.1,"offset":0},{"parameter":"depth","scale":0.1,"offset":0},{"parameter":"height","scale":0.1,"offset":0}]},"holes":{"kind":"region","label":"Mounting holes","min":[{"parameter":"width","scale":0.5,"offset":0},{"parameter":"depth","scale":0.5,"offset":0},0],"max":[{"parameter":"width","scale":0.9,"offset":0},{"parameter":"depth","scale":0.9,"offset":0},{"parameter":"height","scale":0.9,"offset":0}]},"slot":{"kind":"region","label":"Rectangular slot","min":[{"parameter":"width","scale":0.1,"offset":0},{"parameter":"depth","scale":0.1,"offset":0},{"parameter":"height","scale":0.4,"offset":0}],"max":[{"parameter":"width","scale":0.4,"offset":0},{"parameter":"depth","scale":0.9,"offset":0},{"parameter":"height","scale":0.6,"offset":0}]}}} */

// Top-level parameters (allowlist)
width = 43.22;
depth = 60.0;
height = 45.52;
wall_thickness = 4.0;
hole_diameter = 6.0;
slot_width = 10.0;
slot_height = 6.0;

// Derived sizes (not in allowlist)
eps = 0.01;
base_height = wall_thickness;
vertical_height = height - base_height;
chamfer_size = 8.0;

// Hole positions (derived from view measurements)
hole_top_x = width * 0.6341;
hole_top_z = height * (1 - 0.1733);
hole_bottom_x = width * 0.6341;
hole_bottom_z = height * (1 - 0.8323);
slot_center_x = width * 0.2657;
slot_center_z = height * (1 - 0.4983);

// Main design
difference() {
    // Positive body: L-bracket
    union() {
        // Vertical wall (back part)
        translate([0, depth - wall_thickness, 0])
            cube([width, wall_thickness, height]);
        
        // Base plate (bottom part)
        cube([width, depth, base_height]);
        
        // Mounting tab on left side of vertical face
        translate([0, depth - wall_thickness, height * 0.5])
            cube([wall_thickness, wall_thickness, height * 0.3]);
    }
    
    // Chamfer top-right corner of vertical face
    translate([width - chamfer_size, depth - wall_thickness - eps, height - chamfer_size])
        rotate([0, 0, 0])
            cube([chamfer_size + eps, wall_thickness + 2*eps, chamfer_size + eps]);
    
    // Through holes in vertical wall (cut along Y)
    // Top hole
    translate([hole_top_x, depth - wall_thickness/2, hole_top_z])
        rotate([90, 0, 0])
            cylinder(d=hole_diameter, h=wall_thickness + 2*eps, center=true);
    
    // Bottom hole
    translate([hole_bottom_x, depth - wall_thickness/2, hole_bottom_z])
        rotate([90, 0, 0])
            cylinder(d=hole_diameter, h=wall_thickness + 2*eps, center=true);
    
    // Rectangular slot in vertical wall (cut along Y)
    translate([slot_center_x, depth - wall_thickness/2, slot_center_z])
        rotate([90, 0, 0])
            cube([slot_width, wall_thickness + 2*eps, slot_height], center=true);
}
