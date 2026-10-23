/* doodle-meta {"version":1,"parameters":{"width":{"label":"Overall width","description":"Changes the body width","unit":"mm","feature":"body_width"},"depth":{"label":"Overall depth","description":"Changes the body depth","unit":"mm","feature":"body_depth"},"height":{"label":"Overall height","description":"Changes the body height","unit":"mm","feature":"body_height"},"wall_thickness":{"label":"Wall thickness","description":"Thickness of the enclosure walls","unit":"mm","feature":"wall"},"window_width":{"label":"Window width","description":"Width of the front window cutout","unit":"mm","feature":"window"},"window_height":{"label":"Window height","description":"Height of the front window cutout","unit":"mm","feature":"window"},"window_center_z":{"label":"Window center height","description":"Vertical position of the window center from the bottom","unit":"mm","feature":"window"}},"features":{"body_width":{"kind":"dimension","axis":"x","label":"Overall width"},"body_depth":{"kind":"dimension","axis":"y","label":"Overall depth"},"body_height":{"kind":"dimension","axis":"z","label":"Overall height"},"wall":{"kind":"region","label":"Wall thickness","min":[0,0,0],"max":[{"parameter":"width","scale":0.5,"offset":0},{"parameter":"depth","scale":0.5,"offset":0},{"parameter":"height","scale":1,"offset":0}]},"window":{"kind":"region","label":"Front window","min":[{"parameter":"width","scale":0.5,"offset":-0.2475},{"parameter":"depth","scale":0,"offset":0},{"parameter":"window_center_z","scale":1,"offset":-0.2924}],"max":[{"parameter":"width","scale":0.5,"offset":0.2475},{"parameter":"depth","scale":1,"offset":0},{"parameter":"window_center_z","scale":1,"offset":0.2924}]}}} */

// Top-level parameters (user-editable)
width = 120.0;
depth = 81.68;
height = 43.96;
wall_thickness = 3.0;
window_width = 59.4;
window_height = 25.8;
window_center_z = 21.98;

// Derived constants (not user-editable)
eps = 0.01;

// Main design
module enclosure() {
    difference() {
        // Outer solid box
        cube([width, depth, height], center=false);
        
        // Internal cavity for open-top shell
        // Cavity starts at wall_thickness from bottom, sides, and back
        // Top is open (no top wall)
        translate([wall_thickness, wall_thickness, wall_thickness]) {
            cube([width - 2*wall_thickness, depth - wall_thickness, height - wall_thickness], center=false);
        }
        
        // Front window cutout
        // Centered in X, centered in Z at window_center_z
        // Cuts through the front wall (Y from -eps to wall_thickness+eps)
        translate([width/2, -eps, window_center_z]) {
            rotate([90, 0, 0]) {
                cylinder(h=wall_thickness + 2*eps, d=window_width, center=true);
            }
        }
    }
}

// Instantiate the design
enclosure();
