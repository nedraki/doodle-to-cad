/* doodle-meta {"version":1,"parameters":{"width":{"label":"Overall width","description":"Changes the body width","unit":"mm","feature":"body_width"},"depth":{"label":"Overall depth","description":"Changes the body depth","unit":"mm","feature":"body_depth"},"height":{"label":"Overall height","description":"Changes the body height","unit":"mm","feature":"body_height"},"wall_thickness":{"label":"Wall thickness","description":"Changes the uniform wall thickness","unit":"mm","feature":"wall_thickness"},"window_width":{"label":"Window width","description":"Changes the width of the front window","unit":"mm","feature":"front_window"},"window_height":{"label":"Window height","description":"Changes the height of the front window","unit":"mm","feature":"front_window"},"window_center_z":{"label":"Window center height","description":"Changes the vertical position of the window center","unit":"mm","feature":"front_window"}},"features":{"body_width":{"kind":"dimension","axis":"x","label":"Overall width"},"body_depth":{"kind":"dimension","axis":"y","label":"Overall depth"},"body_height":{"kind":"dimension","axis":"z","label":"Overall height"},"wall_thickness":{"kind":"region","label":"Wall thickness","min":[0,0,0],"max":[{"parameter":"wall_thickness","scale":1,"offset":0},{"parameter":"wall_thickness","scale":1,"offset":0},{"parameter":"wall_thickness","scale":1,"offset":0}]},"front_window":{"kind":"region","label":"Front window","min":[{"parameter":"width","scale":0.5,"offset":-10},{"parameter":"depth","scale":0,"offset":0},{"parameter":"window_center_z","scale":1,"offset":-10}],"max":[{"parameter":"width","scale":0.5,"offset":10},{"parameter":"depth","scale":1,"offset":0},{"parameter":"window_center_z","scale":1,"offset":10}]}}} */

// Parameters
width = 120.0;
depth = 81.68;
height = 43.96;
wall_thickness = 3.0;

// Window parameters (derived from measured view geometry and intent)
// Front view: u=0.496 -> X center. v=0.4947 -> Z center.
// Window width ~ 0.495 * width = 59.4 mm
// Window height ~ 0.5848 * height = 25.7 mm
// Window center Z ~ (1 - 0.4947) * height = 22.2 mm
window_width = 59.4;
window_height = 25.7;
window_center_z = 22.2;

// Derived internal dimensions
inner_width = width - 2 * wall_thickness;
inner_depth = depth - 2 * wall_thickness;
inner_height = height; // Open top, so inner height goes up to top

// Epsilon for boolean operations
eps = 0.01;

// Main Body Construction
difference() {
    // 1. Outer Shell
    cube([width, depth, height], center=false);
    
    // 2. Inner Cavity (Open Top)
    // Positioned to leave walls on sides and back, open at top
    translate([wall_thickness, wall_thickness, -eps]) {
        cube([inner_width, inner_depth, height + eps], center=false);
    }
    
    // 3. Front Window Cutout
    // The window is on the front face (Y=0).
    // It cuts through the front wall (Y from 0 to wall_thickness).
    // Center X is width/2. Center Z is window_center_z.
    // Cutter must traverse the wall fully.
    translate([width/2 - window_width/2, -eps, window_center_z - window_height/2]) {
        cube([window_width, wall_thickness + 2*eps, window_height], center=false);
    }
}
