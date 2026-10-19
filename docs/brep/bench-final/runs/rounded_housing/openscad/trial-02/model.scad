/* doodle-meta {"version":1,"parameters":{"width":{"label":"Overall width","description":"Changes the body width along X","unit":"mm","feature":"body_width"},"depth":{"label":"Overall depth","description":"Changes the body depth along Y","unit":"mm","feature":"body_depth"},"height":{"label":"Overall height","description":"Changes the body height along Z","unit":"mm","feature":"body_height"},"corner_radius":{"label":"Corner radius","description":"Radius of the rounded vertical edges","unit":"mm","feature":"corner_fillet"}},"features":{"body_width":{"kind":"dimension","axis":"x","label":"Overall width"},"body_depth":{"kind":"dimension","axis":"y","label":"Overall depth"},"body_height":{"kind":"dimension","axis":"z","label":"Overall height"},"corner_fillet":{"kind":"region","label":"Rounded vertical edges","min":[0,0,0],"max":[{"parameter":"width","scale":1,"offset":0},{"parameter":"depth","scale":1,"offset":0},{"parameter":"height","scale":1,"offset":0}]}}} */

// Top-level editable parameters
width = 90.0;
depth = 6.62;
height = 49.38;
corner_radius = 6.0;

// Derived constants (not editable)
$fn = 64;
eps = 0.01;

// Module: Rounded rectangle profile in XY plane
module rounded_rect_profile(w, d, r) {
    // Constructed from a central cross and four corner cylinders
    // Central cross
    square([w - 2*r, d], center=true);
    square([w, d - 2*r], center=true);
    
    // Four corners
    translate([w/2 - r, d/2 - r, 0]) circle(r=r);
    translate([-w/2 + r, d/2 - r, 0]) circle(r=r);
    translate([w/2 - r, -d/2 + r, 0]) circle(r=r);
    translate([-w/2 + r, -d/2 + r, 0]) circle(r=r);
}

// Main design
// The object sits on the build plate (Z=0 to Z=height)
// Centered in X and Y for symmetry, extruded along Z

translate([0, 0, height/2]) {
    linear_extrude(height=height, center=true) {
        rounded_rect_profile(width, depth, corner_radius);
    }
}
