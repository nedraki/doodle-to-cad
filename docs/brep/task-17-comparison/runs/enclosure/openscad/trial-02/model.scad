/* doodle-meta {"version":1,"parameters":{"box_width":{"label":"Overall width","description":"Changes the box width along X","unit":"mm","feature":"body_width"},"box_depth":{"label":"Overall depth","description":"Changes the box depth along Y","unit":"mm","feature":"body_depth"},"box_height":{"label":"Overall height","description":"Changes the box height along Z","unit":"mm","feature":"body_height"},"wall_thickness":{"label":"Wall thickness","description":"Uniform thickness of walls and floor","unit":"mm","feature":"wall_thickness"},"window_width":{"label":"Window width","description":"Width of the rectangular window in the front wall","unit":"mm","feature":"front_window"},"window_height":{"label":"Window height","description":"Height of the rectangular window in the front wall","unit":"mm","feature":"front_window"},"window_center_z":{"label":"Window center height","description":"Vertical center of the window from the bottom","unit":"mm","feature":"front_window"}},"features":{"body_width":{"kind":"dimension","axis":"x","label":"Overall width"},"body_depth":{"kind":"dimension","axis":"y","label":"Overall depth"},"body_height":{"kind":"dimension","axis":"z","label":"Overall height"},"wall_thickness":{"kind":"region","label":"Wall thickness","min":[0,0,0],"max":[{"parameter":"wall_thickness","scale":1,"offset":0},{"parameter":"wall_thickness","scale":1,"offset":0},{"parameter":"wall_thickness","scale":1,"offset":0}]},"front_window":{"kind":"region","label":"Front window","min":[{"parameter":"box_width","scale":0.25,"offset":0},0,{"parameter":"window_center_z","scale":1,"offset":-10.2}],[{"parameter":"box_width","scale":0.75,"offset":0},{"parameter":"wall_thickness","scale":1,"offset":0},{"parameter":"window_center_z","scale":1,"offset":10.2}]}}} */

// Top-level editable parameters
box_width = 120.0;
box_depth = 81.68;
box_height = 43.96;
wall_thickness = 4.0;
window_width = 60.0;
window_height = 20.4;
window_center_z = 21.98;

// Derived (not editable)
eps = 0.01;
inner_width = box_width - 2 * wall_thickness;
inner_depth = box_depth - 2 * wall_thickness;
inner_height = box_height - wall_thickness;

module box_body() {
    // Outer solid
    cube([box_width, box_depth, box_height]);
}

module inner_cavity() {
    // Hollow interior (open top)
    translate([wall_thickness, wall_thickness, wall_thickness])
        cube([inner_width, inner_depth, inner_height]);
}

module window_cutter() {
    // Rectangular through-hole in the front wall (cut along Y)
    translate([box_width/2 - window_width/2, -eps, window_center_z - window_height/2])
        cube([window_width, wall_thickness + 2*eps, window_height]);
}

difference() {
    box_body();
    inner_cavity();
    window_cutter();
}
