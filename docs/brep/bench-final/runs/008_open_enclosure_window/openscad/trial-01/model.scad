/* doodle-meta {"version":1,"parameters":{"width":{"label":"Overall width","description":"Changes the body width","unit":"mm","feature":"body_width"},"depth":{"label":"Overall depth","description":"Changes the body depth","unit":"mm","feature":"body_depth"},"height":{"label":"Overall height","description":"Changes the body height","unit":"mm","feature":"body_height"},"wall_thickness":{"label":"Wall thickness","description":"Changes the thickness of the enclosure walls and base","unit":"mm","feature":"wall_thickness"},"window_width":{"label":"Window width","description":"Changes the width of the front window cutout","unit":"mm","feature":"window"},"window_height":{"label":"Window height","description":"Changes the height of the front window cutout","unit":"mm","feature":"window"},"window_center_z":{"label":"Window center height","description":"Changes the vertical position of the window center","unit":"mm","feature":"window"}},"features":{"body_width":{"kind":"dimension","axis":"x","label":"Overall width"},"body_depth":{"kind":"dimension","axis":"y","label":"Overall depth"},"body_height":{"kind":"dimension","axis":"z","label":"Overall height"},"wall_thickness":{"kind":"region","label":"Wall thickness","min":[0,0,0],"max":[{"parameter":"wall_thickness","scale":1,"offset":0},{"parameter":"wall_thickness","scale":1,"offset":0},{"parameter":"height","scale":1,"offset":0}]},"window":{"kind":"region","label":"Front window","min":[{"parameter":"width","scale":0.5,"offset":-0.5},{"parameter":"window_width","scale":1,"offset":0},{"parameter":"window_center_z","scale":1,"offset":-0.5}],"max":[{"parameter":"width","scale":0.5,"offset":0.5},{"parameter":"window_width","scale":1,"offset":0},{"parameter":"window_center_z","scale":1,"offset":0.5}]}}} */

// Top-level parameters (user-editable)
width = 120.0;
depth = 81.68;
height = 43.96;
wall_thickness = 4.0;
window_width = 59.4;
window_height = 25.7;
window_center_z = 21.98;

// Derived constants (not user-editable)
eps = 0.01;

// Module: The complete enclosure body
module enclosure_body() {
    difference() {
        // 1. Positive Body: Solid block
        cube([width, depth, height]);
        
        // 2. Shell Cavity: Remove interior to create walls and base
        // Cavity starts at wall_thickness from all sides except top (open top)
        translate([wall_thickness, wall_thickness, wall_thickness]) {
            cube([width - 2*wall_thickness, depth - 2*wall_thickness, height - wall_thickness + eps]);
        }
        
        // 3. Front Window Cutout
        // The window is on the front face (Y=0).
        // Cutter axis must be along Y to pierce the front wall.
        // Center of window in X is width/2.
        // Center of window in Z is window_center_z.
        // Cutter spans from Y = -eps to Y = wall_thickness + eps to fully traverse the front wall.
        translate([width/2, -eps, window_center_z]) {
            // Rectangular cutter centered at origin of this local frame
            // X spans -window_width/2 to +window_width/2
            // Y spans 0 to wall_thickness + 2*eps (to ensure through cut)
            // Z spans -window_height/2 to +window_height/2
            cube([window_width, wall_thickness + 2*eps, window_height], center=[true, false, true]);
        }
    }
}

// Instantiate the design
enclosure_body();
