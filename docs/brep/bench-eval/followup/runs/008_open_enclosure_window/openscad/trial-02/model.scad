/* doodle-meta {"version":1,"parameters":{"width":{"label":"Overall width","description":"Changes the body width","unit":"mm","feature":"body_width"},"depth":{"label":"Overall depth","description":"Changes the body depth","unit":"mm","feature":"body_depth"},"height":{"label":"Overall height","description":"Changes the body height","unit":"mm","feature":"body_height"},"wall_thickness":{"label":"Wall thickness","description":"Thickness of walls and bottom","unit":"mm","feature":"wall_thickness"},"window_width":{"label":"Window width","description":"Width of the front window opening","unit":"mm","feature":"front_window"},"window_height":{"label":"Window height","description":"Height of the front window opening","unit":"mm","feature":"front_window"}},"features":{"body_width":{"kind":"dimension","axis":"x","label":"Overall width"},"body_depth":{"kind":"dimension","axis":"y","label":"Overall depth"},"body_height":{"kind":"dimension","axis":"z","label":"Overall height"},"front_window":{"kind":"region","label":"Front Window","min":[{"parameter":"width","scale":0.2525,"offset":0},{"parameter":"depth","scale":-0.1,"offset":0},{"parameter":"height","scale":0.2078,"offset":0}],"max":[{"parameter":"width","scale":0.7475,"offset":0},{"parameter":"depth","scale":1.1,"offset":0},{"parameter":"height","scale":0.7922,"offset":0}]}}} */

// Top-level parameters (user-editable)
width = 120.0;
depth = 81.68;
height = 43.96;
wall_thickness = 3.0;
window_width = 60.0;
window_height = 25.6;

// Derived constants (not user-editable)
eps = 0.01;

// Main design
main_enclosure();

module main_enclosure() {
    difference() {
        // Outer shell body
        outer_shell();
        
        // Subtract inner cavity to create open-top shell
        inner_cavity();
        
        // Subtract front window cutout
        front_window_cutter();
    }
}

module outer_shell() {
    cube([width, depth, height], center=false);
}

module inner_cavity() {
    // Inner cavity: subtracted from top, leaving bottom and walls
    // Positioned to leave wall_thickness on all sides and bottom
    translate([wall_thickness, wall_thickness, wall_thickness]) {
        cube([width - 2*wall_thickness, depth - 2*wall_thickness, height - wall_thickness + eps], center=false);
    }
}

module front_window_cutter() {
    // Window is centered horizontally on front face
    // Vertical position: center at ~50% of height based on measured view
    // Window height ~25.6mm, so bottom at (height - window_height)/2
    window_z_bottom = (height - window_height) / 2.0;
    window_x_left = (width - window_width) / 2.0;
    
    // Cutter spans through the front wall (Y direction)
    // Front wall is at Y=0 to Y=wall_thickness
    // Cutter must traverse fully: from Y=-eps to Y=wall_thickness+eps
    translate([window_x_left, -eps, window_z_bottom]) {
        cube([window_width, wall_thickness + 2*eps, window_height], center=false);
    }
}
