/* doodle-meta {"version":1,"parameters":{"width":{"label":"Overall width","description":"Changes the body width","unit":"mm","feature":"body_width"},"depth":{"label":"Overall depth","description":"Changes the base depth","unit":"mm","feature":"body_depth"},"height":{"label":"Overall height","description":"Changes the panel height","unit":"mm","feature":"body_height"},"thickness":{"label":"Material thickness","description":"Thickness of the L-profile walls","unit":"mm","feature":"wall_thickness"}},"features":{"body_width":{"kind":"dimension","axis":"x","label":"Overall width"},"body_depth":{"kind":"dimension","axis":"y","label":"Overall depth"},"body_height":{"kind":"dimension","axis":"z","label":"Overall height"},"wall_thickness":{"kind":"dimension","axis":"x","label":"Material thickness"}}} */

// Top-level parameters (allowlist)
width = 80.18;
depth = 71.67;
height = 100.0;
thickness = 10.0;

// Derived sizes (not editable)
eps = 0.01;
panel_x_start = width - thickness;
base_z_end = thickness;

// Hole parameters derived from front view proportions
// Front view maps: X = u * width, Z = (1-v) * height
// Hole 1 (Top Left): center u=0.2724, v=0.1968, size u=0.2988, v=0.1968
h1_cx = 0.2724 * width;
h1_cz = (1 - 0.1968) * height;
h1_w = 0.2988 * width;
h1_h = 0.1968 * height;

// Hole 2 (Center Vertical): center u=0.5362, v=0.4268, size u=0.1173, v=0.3135
h2_cx = 0.5362 * width;
h2_cz = (1 - 0.4268) * height;
h2_w = 0.1173 * width;
h2_h = 0.3135 * height;

// Hole 3 (Bottom Left): center u=0.3269, v=0.6087, size u=0.1732, v=0.4027
h3_cx = 0.3269 * width;
h3_cz = (1 - 0.6087) * height;
h3_w = 0.1732 * width;
h3_h = 0.4027 * height;

// Hole 4 (Bottom Right): center u=0.7472, v=0.6087, size u=0.1369, v=0.3891
h4_cx = 0.7472 * width;
h4_cz = (1 - 0.6087) * height;
h4_w = 0.1369 * width;
h4_h = 0.3891 * height;

// Main design
difference() {
    // Positive Body: L-shape
    // Base: extends from Y=0 to Y=depth, Z=0 to Z=thickness, X=0 to X=width
    // Panel: extends from Y=0 to Y=thickness, Z=0 to Z=height, X=panel_x_start to X=width
    
    // Union of base and panel
    union() {
        // Base
        cube([width, depth, thickness]);
        
        // Panel
        translate([panel_x_start, 0, 0])
            cube([thickness, thickness, height]);
    }
    
    // Subtractive Cutters for holes in the panel
    // The panel is at X in [panel_x_start, width], Y in [0, thickness], Z in [0, height]
    // Holes cut through the panel thickness (along Y axis)
    
    // Hole 1: Top Left
    translate([h1_cx, 0, h1_cz])
        rotate([90, 0, 0])
            cube([h1_w, thickness + 2*eps, h1_h], center=true);
            
    // Hole 2: Center Vertical
    translate([h2_cx, 0, h2_cz])
        rotate([90, 0, 0])
            cube([h2_w, thickness + 2*eps, h2_h], center=true);
            
    // Hole 3: Bottom Left
    translate([h3_cx, 0, h3_cz])
        rotate([90, 0, 0])
            cube([h3_w, thickness + 2*eps, h3_h], center=true);
            
    // Hole 4: Bottom Right
    translate([h4_cx, 0, h4_cz])
        rotate([90, 0, 0])
            cube([h4_w, thickness + 2*eps, h4_h], center=true);
}
