/* doodle-meta {"version":1,"parameters":{"width":{"label":"Overall width","description":"Changes the body width","unit":"mm","feature":"body_width"},"depth":{"label":"Overall depth","description":"Changes the body depth","unit":"mm","feature":"body_depth"},"height":{"label":"Overall height","description":"Changes the body height","unit":"mm","feature":"body_height"},"wall_thickness":{"label":"Wall thickness","description":"Changes the uniform wall and floor thickness","unit":"mm","feature":"wall_thickness"},"corner_radius":{"label":"Outer corner radius","description":"Changes the outer corner radius","unit":"mm","feature":"corner_radius"}},"features":{"body_width":{"kind":"dimension","axis":"x","label":"Overall width"},"body_depth":{"kind":"dimension","axis":"y","label":"Overall depth"},"body_height":{"kind":"dimension","axis":"z","label":"Overall height"},"wall_thickness":{"kind":"region","label":"Wall thickness","min":[0,0,0],"max":[{"parameter":"wall_thickness","scale":1,"offset":0},{"parameter":"wall_thickness","scale":1,"offset":0},{"parameter":"height","scale":1,"offset":0}]},"corner_radius":{"kind":"region","label":"Outer corner radius","min":[{"parameter":"width","scale":1,"offset":0},{"parameter":"depth","scale":1,"offset":0},0],"max":[{"parameter":"width","scale":1,"offset":0},{"parameter":"depth","scale":1,"offset":0},{"parameter":"height","scale":1,"offset":0}]}}} */

// Parameters
width = 60;
depth = 40;
height = 20;
wall_thickness = 2;
corner_radius = 6;

// Derived sizes
inner_width = width - 2 * wall_thickness;
inner_depth = depth - 2 * wall_thickness;
inner_height = height - wall_thickness;
inner_radius = corner_radius - wall_thickness;

// Modules
module rounded_rect(w, d, r) {
    hull() {
        translate([r, r, 0]) cylinder(r=r, h=1, center=true);
        translate([w-r, r, 0]) cylinder(r=r, h=1, center=true);
        translate([r, d-r, 0]) cylinder(r=r, h=1, center=true);
        translate([w-r, d-r, 0]) cylinder(r=r, h=1, center=true);
    }
}

// Main design
difference() {
    // Outer shell
    translate([0, 0, height/2])
        rounded_rect(width, depth, corner_radius);
    
    // Inner cavity (subtractive)
    translate([wall_thickness, wall_thickness, wall_thickness + inner_height/2])
        rounded_rect(inner_width, inner_depth, inner_radius);
}
