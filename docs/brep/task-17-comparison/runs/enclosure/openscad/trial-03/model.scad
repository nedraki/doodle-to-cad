/* doodle-meta {"version":1,"parameters":{"width":{"label":"Overall width","description":"Changes the body width","unit":"mm","feature":"body_width"},"depth":{"label":"Overall depth","description":"Changes the body depth","unit":"mm","feature":"body_depth"},"height":{"label":"Overall height","description":"Changes the body height","unit":"mm","feature":"body_height"},"wall_thickness":{"label":"Wall thickness","description":"Changes the uniform wall thickness","unit":"mm","feature":"wall_thickness"},"window_width":{"label":"Window width","description":"Changes the width of the front window","unit":"mm","feature":"front_window"},"window_height":{"label":"Window height","description":"Changes the height of the front window","unit":"mm","feature":"front_window"},"window_center_z":{"label":"Window center height","description":"Changes the vertical position of the window center","unit":"mm","feature":"front_window"}},"features":{"body_width":{"kind":"dimension","axis":"x","label":"Overall width"},"body_depth":{"kind":"dimension","axis":"y","label":"Overall depth"},"body_height":{"kind":"dimension","axis":"z","label":"Overall height"},"wall_thickness":{"kind":"region","label":"Wall thickness","min":[0,0,0],"max":[{"parameter":"wall_thickness","scale":1,"offset":0},{"parameter":"wall_thickness","scale":1,"offset":0},{"parameter":"height","scale":1,"offset":0}]},"front_window":{"kind":"region","label":"Front window","min":[{"parameter":"width","scale":0.5,"offset":-0.5},{"parameter":"window_width","scale":0.5,"offset":0},{"parameter":"window_center_z","scale":1,"offset":-0.5},{"parameter":"window_height","scale":0.5,"offset":0}],"max":[{"parameter":"width","scale":0.5,"offset":0.5},{"parameter":"window_width","scale":0.5,"offset":0},{"parameter":"window_center_z","scale":1,"offset":0.5},{"parameter":"window_height","scale":0.5,"offset":0}]}}} */

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

// Main design
difference() {
    // Outer shell
    cube([width, depth, height], center=false);
    
    // Hollow out the interior (open top)
    translate([wall_thickness, wall_thickness, wall_thickness])
        cube([width - 2*wall_thickness, depth - 2*wall_thickness, height - wall_thickness + eps], center=false);
    
    // Front window cutout (through the front wall)
    // Front wall is at Y=0 to Y=wall_thickness
    // Window is centered in X and at window_center_z in Z
    translate([width/2 - window_width/2, -eps, window_center_z - window_height/2])
        cube([window_width, wall_thickness + 2*eps, window_height], center=false);
}
