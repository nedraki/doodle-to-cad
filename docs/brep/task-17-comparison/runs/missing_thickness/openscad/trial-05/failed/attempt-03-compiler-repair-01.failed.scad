/* doodle-meta {"version":1,"parameters":{"overall_length":{"label":"Overall Length","description":"Changes the tray length along X","unit":"mm","feature":"body_length"},"overall_width":{"label":"Overall Width","description":"Changes the tray width along Y","unit":"mm","feature":"body_width"},"overall_height":{"label":"Overall Height","description":"Changes the tray height along Z","unit":"mm","feature":"body_height"},"wall_thickness":{"label":"Wall Thickness","description":"Changes the uniform wall and floor thickness","unit":"mm","feature":"wall_thickness"},"corner_radius":{"label":"Corner Radius","description":"Changes the outer corner radius","unit":"mm","feature":"corner_radius"}},"features":{"body_length":{"kind":"dimension","axis":"x","label":"Overall Length"},"body_width":{"kind":"dimension","axis":"y","label":"Overall Width"},"body_height":{"kind":"dimension","axis":"z","label":"Overall Height"},"wall_thickness":{"kind":"region","label":"Wall Thickness","min":[0,0,0],"max":[{"parameter":"wall_thickness","scale":1,"offset":0},{"parameter":"overall_width","scale":1,"offset":0},{"parameter":"overall_height","scale":1,"offset":0}]},"corner_radius":{"kind":"region","label":"Corner Radius","min":[{"parameter":"overall_length","scale":1,"offset":0},{"parameter":"overall_width","scale":1,"offset":0},0],"max":[{"parameter":"overall_length","scale":1,"offset":0},{"parameter":"overall_width","scale":1,"offset":0},{"parameter":"overall_height","scale":1,"offset":0}]}}} */

// Parameters
overall_length = 60;
overall_width = 40;
overall_height = 20;
wall_thickness = 2;
corner_radius = 6;

// Derived dimensions
inner_length = overall_length - 2 * wall_thickness;
inner_width = overall_width - 2 * wall_thickness;
inner_corner_radius = corner_radius - wall_thickness;
cavity_height = overall_height - wall_thickness;

// Module for rounded rectangle
module rounded_rect(l, w, r) {
    hull() {
        translate([r, r, 0]) cylinder(h=1, r=r, center=false);
        translate([l-r, r, 0]) cylinder(h=1, r=r, center=false);
        translate([r, w-r, 0]) cylinder(h=1, r=r, center=false);
        translate([l-r, w-r, 0]) cylinder(h=1, r=r, center=false);
    }
}

// Main design
difference() {
    // Outer body
    translate([0, 0, 0])
    linear_extrude(height=overall_height)
    rounded_rect(overall_length, overall_width, corner_radius);
    
    // Inner cavity (subtractive)
    translate([wall_thickness, wall_thickness, wall_thickness])
    linear_extrude(height=cavity_height + 1) // +1 to ensure clean cut through top
    rounded_rect(inner_length, inner_width, inner_corner_radius);
}
