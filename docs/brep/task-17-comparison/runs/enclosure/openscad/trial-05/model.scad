/* doodle-meta {"version":1,"parameters":{"width":{"label":"Overall width","description":"Changes the body width","unit":"mm","feature":"body_width"},"depth":{"label":"Overall depth","description":"Changes the body depth","unit":"mm","feature":"body_depth"},"height":{"label":"Overall height","description":"Changes the body height","unit":"mm","feature":"body_height"},"wall_thickness":{"label":"Wall thickness","description":"Changes the uniform wall thickness","unit":"mm","feature":"wall_thickness"},"window_width":{"label":"Window width","description":"Changes the width of the front window","unit":"mm","feature":"front_window"},"window_height":{"label":"Window height","description":"Changes the height of the front window","unit":"mm","feature":"front_window"}},"features":{"body_width":{"kind":"dimension","axis":"x","label":"Overall width"},"body_depth":{"kind":"dimension","axis":"y","label":"Overall depth"},"body_height":{"kind":"dimension","axis":"z","label":"Overall height"},"wall_thickness":{"kind":"region","label":"Wall thickness","min":[0,0,0],"max":[{"parameter":"wall_thickness","scale":1,"offset":0},{"parameter":"wall_thickness","scale":1,"offset":0},{"parameter":"height","scale":1,"offset":0}]},"front_window":{"kind":"region","label":"Front window","min":[{"parameter":"width","scale":0.5,"offset":-29.7},{"parameter":"depth","scale":0,"offset":0},{"parameter":"height","scale":0.5,"offset":-12.87}],"max":[{"parameter":"width","scale":0.5,"offset":29.7},{"parameter":"depth","scale":1,"offset":0},{"parameter":"height","scale":0.5,"offset":12.87}]}}} */

// Top-level parameters (user-editable)
width = 120.0;
depth = 81.68;
height = 43.96;
wall_thickness = 5.0;
window_width = 59.4;
window_height = 25.74;

// Derived constants (not user-editable)
eps = 0.1;

// Main design
difference() {
    // Outer shell
    cube([width, depth, height], center=true);
    
    // Top cavity (open top)
    translate([0, 0, height/2])
        cube([width - 2*wall_thickness, depth - 2*wall_thickness, height + eps], center=true);
    
    // Front window (through cutout along Y)
    translate([0, 0, 0])
        cube([window_width, depth + 2*eps, window_height], center=true);
}
