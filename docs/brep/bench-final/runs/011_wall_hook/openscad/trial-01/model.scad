/* doodle-meta {"version":1,"parameters":{"width":{"label":"Overall width","description":"Changes the overall width of the L-hook","unit":"mm","feature":"body_width"},"height":{"label":"Overall height","description":"Changes the overall height of the L-hook","unit":"mm","feature":"body_height"},"depth":{"label":"Thickness","description":"Changes the thickness (depth) of the L-hook","unit":"mm","feature":"body_depth"},"backplate_width":{"label":"Backplate width","description":"Changes the width of the vertical backplate","unit":"mm","feature":"backplate_width"},"hook_thickness":{"label":"Hook thickness","description":"Changes the vertical thickness of the horizontal hook arm","unit":"mm","feature":"hook_thickness"}},"features":{"body_width":{"kind":"dimension","axis":"x","label":"Overall width"},"body_height":{"kind":"dimension","axis":"z","label":"Overall height"},"body_depth":{"kind":"dimension","axis":"y","label":"Thickness"},"backplate_width":{"kind":"region","label":"Backplate width","min":[0,0,0],"max":[{"parameter":"backplate_width","scale":1,"offset":0},{"parameter":"depth","scale":1,"offset":0},{"parameter":"height","scale":1,"offset":0}]},"hook_thickness":{"kind":"region","label":"Hook thickness","min":[{"parameter":"backplate_width","scale":1,"offset":0},0,{"parameter":"height","scale":1,"offset":0},{"parameter":"hook_thickness","scale":-1,"offset":0}],"max":[{"parameter":"width","scale":1,"offset":0},{"parameter":"depth","scale":1,"offset":0},{"parameter":"height","scale":1,"offset":0}]}}} */

// Overall dimensions
width = 60.0;
height = 54.42;
depth = 13.6;

// Local dimensions
backplate_width = 15.0;
hook_thickness = 12.0;

module l_hook() {
    // Vertical backplate
    cube([backplate_width, depth, height]);
    
    // Horizontal hook arm
    translate([backplate_width, 0, height - hook_thickness])
        cube([width - backplate_width, depth, hook_thickness]);
}

// Instantiate the design
l_hook();
