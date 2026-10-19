/* doodle-meta {"version":1,"parameters":{"width":{"label":"Overall width","description":"Changes the body width","unit":"mm","feature":"body_width"},"depth":{"label":"Overall depth","description":"Changes the body depth","unit":"mm","feature":"body_depth"},"height":{"label":"Overall height","description":"Changes the body height","unit":"mm","feature":"body_height"},"radius":{"label":"Corner radius","description":"Changes the outer corner radius","unit":"mm","feature":"corner_radius"},"wall":{"label":"Wall thickness","description":"Changes the uniform wall and floor thickness","unit":"mm","feature":"wall_thickness"}},"features":{"body_width":{"kind":"dimension","axis":"x","label":"Overall width"},"body_depth":{"kind":"dimension","axis":"y","label":"Overall depth"},"body_height":{"kind":"dimension","axis":"z","label":"Overall height"},"corner_radius":{"kind":"region","label":"Corner radius","min":[0,0,0],"max":[{"parameter":"width","scale":0.5},{"parameter":"depth","scale":0.5},{"parameter":"height","scale":0.5}]},"wall_thickness":{"kind":"region","label":"Wall thickness","min":[0,0,0],"max":[{"parameter":"width","scale":0.5},{"parameter":"depth","scale":0.5},{"parameter":"height","scale":0.5}]}}} */

// Parameters
width = 46.15;
depth = 5.31;
height = 60.0;
radius = 6.0;
wall = 2.0;

// Derived dimensions
inner_width = width - 2 * wall;
inner_depth = depth - 2 * wall;
inner_height = height - wall;
inner_radius = radius - wall;

// Modules
module rounded_rect(w, d, r) {
    // Creates a rounded rectangle centered at origin in XY plane
    // w: width (X), d: depth (Y), r: corner radius
    // Ensure radius is valid
    r_safe = min(r, w/2, d/2);
    
    // Center rectangle
    cube([w - 2*r_safe, d, 1], center=true);
    cube([w, d - 2*r_safe, 1], center=true);
    
    // Corners
    translate([w/2 - r_safe, d/2 - r_safe, 0]) cylinder(r=r_safe, h=1, center=true);
    translate([-w/2 + r_safe, d/2 - r_safe, 0]) cylinder(r=r_safe, h=1, center=true);
    translate([w/2 - r_safe, -d/2 + r_safe, 0]) cylinder(r=r_safe, h=1, center=true);
    translate([-w/2 + r_safe, -d/2 + r_safe, 0]) cylinder(r=r_safe, h=1, center=true);
}

// Main Design
difference() {
    // Outer Body
    translate([0, 0, height/2]) {
        linear_extrude(height=height, center=true) {
            rounded_rect(width, depth, radius);
        }
    }
    
    // Inner Cavity (Subtractive)
    // Cut from top, leaving floor of thickness 'wall'
    // The cavity starts at Z = wall and goes up to Z = height
    // We create a cutter that spans from Z=wall to Z=height+epsilon
    translate([0, 0, wall + (height - wall)/2]) {
        linear_extrude(height=height - wall + 0.1, center=true) {
            rounded_rect(inner_width, inner_depth, inner_radius);
        }
    }
}
