/* doodle-meta {"version":1,"parameters":{"width":{"label":"Overall width","description":"Changes the body width","unit":"mm","feature":"body_width"},"depth":{"label":"Overall depth","description":"Changes the body depth","unit":"mm","feature":"body_depth"},"height":{"label":"Overall height","description":"Changes the body height","unit":"mm","feature":"body_height"},"wall_thickness":{"label":"Wall thickness","description":"Changes the thickness of the walls and floor","unit":"mm","feature":"wall_thickness"},"window_width":{"label":"Window width","description":"Changes the width of the front window","unit":"mm","feature":"window"},"window_height":{"label":"Window height","description":"Changes the height of the front window","unit":"mm","feature":"window"}},"features":{"body_width":{"kind":"dimension","axis":"x","label":"Overall width"},"body_depth":{"kind":"dimension","axis":"y","label":"Overall depth"},"body_height":{"kind":"dimension","axis":"z","label":"Overall height"},"wall_thickness":{"kind":"region","label":"Wall thickness","min":[0,0,0],"max":[{"parameter":"wall_thickness","scale":1,"offset":0},{"parameter":"wall_thickness","scale":1,"offset":0},{"parameter":"wall_thickness","scale":1,"offset":0}]},"window":{"kind":"region","label":"Front window","min":[{"parameter":"width","scale":0.5,"offset":-12.12},{"parameter":"depth","scale":0,"offset":0},{"parameter":"height","scale":0.5,"offset":-12.86}],"max":[{"parameter":"width","scale":0.5,"offset":12.12},{"parameter":"depth","scale":1,"offset":0},{"parameter":"height","scale":0.5,"offset":12.86}]}}} */

// Top-level parameters (user-editable)
width = 120.0;
depth = 81.68;
height = 43.96;
wall_thickness = 3.0;
window_width = 24.24;
window_height = 25.72;

// Derived constants (not user-editable)
eps = 0.01;
floor_thickness = wall_thickness;
window_center_z = height / 2.0;

// Module: The complete enclosure body
module enclosure() {
    difference() {
        // 1. Positive Body: Solid block
        cube([width, depth, height]);
        
        // 2. Subtract: Internal Cavity (Open Top)
        // Cuts from Z=floor_thickness up to above the top surface
        translate([wall_thickness, wall_thickness, floor_thickness])
            cube([width - 2*wall_thickness, depth - 2*wall_thickness, height]);
            
        // 3. Subtract: Front Window
        // Cuts through the front wall (Y axis)
        // Centered in X, centered in Z
        translate([width/2 - window_width/2, -eps, window_center_z - window_height/2])
            cube([window_width, wall_thickness + 2*eps, window_height]);
    }
}

// Instantiate the design
enclosure();
