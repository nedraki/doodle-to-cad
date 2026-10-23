/* doodle-meta {"version":1,"parameters":{"width":{"label":"Overall width","description":"Changes the body width","unit":"mm","feature":"body_width"},"depth":{"label":"Overall depth","description":"Changes the body depth","unit":"mm","feature":"body_depth"},"height":{"label":"Overall height","description":"Changes the body height","unit":"mm","feature":"body_height"},"corner_radius":{"label":"Corner radius","description":"Changes the outer corner radius","unit":"mm","feature":"corner_radius"},"wall_thickness":{"label":"Wall thickness","description":"Changes the uniform wall and floor thickness","unit":"mm","feature":"wall_thickness"}},"features":{"body_width":{"kind":"dimension","axis":"x","label":"Overall width"},"body_depth":{"kind":"dimension","axis":"y","label":"Overall depth"},"body_height":{"kind":"dimension","axis":"z","label":"Overall height"},"corner_radius":{"kind":"region","label":"Corner radius","min":[0,0,0],"max":[{"parameter":"corner_radius","scale":1,"offset":0},{"parameter":"corner_radius","scale":1,"offset":0},{"parameter":"height","scale":1,"offset":0}]},"wall_thickness":{"kind":"region","label":"Wall thickness","min":[0,0,0],"max":[{"parameter":"wall_thickness","scale":1,"offset":0},{"parameter":"wall_thickness","scale":1,"offset":0},{"parameter":"height","scale":1,"offset":0}]}}} */

// Top-level editable parameters
width = 60;
depth = 40;
height = 20;
corner_radius = 6;
wall_thickness = 2;

// Derived sizes (not editable)
inner_width = width - 2 * wall_thickness;
inner_depth = depth - 2 * wall_thickness;
inner_height = height - wall_thickness;
inner_corner_radius = corner_radius - wall_thickness;

// Module for rounded rectangle extrusion
module rounded_rect(w, d, r, h) {
    // Create a rounded rectangle by combining a central cross and corner cylinders
    // This ensures a watertight manifold
    linear_extrude(height=h) {
        union() {
            // Central cross
            square([w - 2*r, d], center=true);
            square([w, d - 2*r], center=true);
            // Corner cylinders
            translate([-(w/2 - r), -(d/2 - r)]) circle(r=r);
            translate([ (w/2 - r), -(d/2 - r)]) circle(r=r);
            translate([-(w/2 - r),  (d/2 - r)]) circle(r=r);
            translate([ (w/2 - r),  (d/2 - r)]) circle(r=r);
        }
    }
}

// Main design
difference() {
    // Outer shell
    rounded_rect(width, depth, corner_radius, height);
    
    // Inner cavity (cutout)
    // Positioned to leave uniform floor thickness at the bottom (Z=0)
    // The cavity starts at Z = wall_thickness and goes up through the top
    translate([0, 0, wall_thickness]) {
        rounded_rect(inner_width, inner_depth, inner_corner_radius, height);
    }
}
