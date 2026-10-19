/* doodle-meta {"version":1,"parameters":{"width":{"label":"Overall width","description":"Changes the overall width of the box","unit":"mm","feature":"body_width"},"depth":{"label":"Overall depth","description":"Changes the overall depth of the box","unit":"mm","feature":"body_depth"},"height":{"label":"Overall height","description":"Changes the overall height of the box","unit":"mm","feature":"body_height"},"wall_thickness":{"label":"Wall thickness","description":"Changes the uniform wall thickness of the box","unit":"mm","feature":"wall_thickness"},"window_width":{"label":"Window width","description":"Changes the width of the rectangular window","unit":"mm","feature":"front_window"},"window_height":{"label":"Window height","description":"Changes the height of the rectangular window","unit":"mm","feature":"front_window"},"window_z":{"label":"Window vertical position","description":"Changes the vertical center position of the window","unit":"mm","feature":"front_window"}},"features":{"body_width":{"kind":"dimension","axis":"x","label":"Overall width"},"body_depth":{"kind":"dimension","axis":"y","label":"Overall depth"},"body_height":{"kind":"dimension","axis":"z","label":"Overall height"},"wall_thickness":{"kind":"region","label":"Wall thickness","min":[0,0,0],"max":[{"parameter":"wall_thickness","scale":1,"offset":0},{"parameter":"wall_thickness","scale":1,"offset":0},{"parameter":"height","scale":1,"offset":0}]},"front_window":{"kind":"region","label":"Front window","min":[{"parameter":"width","scale":0.5,"offset":-0.5},{"parameter":"width","scale":0.5,"offset":-0.5},{"parameter":"window_z","scale":1,"offset":-0.5}],"max":[{"parameter":"width","scale":0.5,"offset":0.5},{"parameter":"width","scale":0.5,"offset":0.5},{"parameter":"window_z","scale":1,"offset":0.5}]}}} */

// Parameters
width = 120.0;
depth = 81.68;
height = 43.96;
wall_thickness = 3.0;
window_width = 60.0;
window_height = 25.7;
window_z = 22.0; // Centered vertically in the front view

// Derived constants
eps = 0.01;

// Main Body Construction
difference() {
    // 1. Outer Shell
    cube([width, depth, height], center=false);

    // 2. Inner Cavity (Open Top)
    // Subtract the interior volume to create walls and floor
    translate([wall_thickness, wall_thickness, wall_thickness]) {
        cube([width - 2*wall_thickness, depth - 2*wall_thickness, height - wall_thickness + eps], center=false);
    }

    // 3. Front Window Cutout
    // The window is in the front wall (Y=0 to Y=wall_thickness)
    // It cuts through the Y axis
    translate([width/2, -eps, window_z]) {
        // Center the cutter on the X and Z axes relative to the wall
        // X: centered at width/2
        // Y: spans from -eps to wall_thickness + eps to ensure clean cut
        // Z: centered at window_z
        cube([window_width, wall_thickness + 2*eps, window_height], center=true);
    }
}
