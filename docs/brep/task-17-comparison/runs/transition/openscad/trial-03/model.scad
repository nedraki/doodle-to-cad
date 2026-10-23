/* doodle-meta {"version":1,"parameters":{"base_width":{"label":"Base Width","description":"Width of the rectangular base along X","unit":"mm","feature":"base_width"},"base_depth":{"label":"Base Depth","description":"Depth of the rectangular base along Y","unit":"mm","feature":"base_depth"},"top_diameter":{"label":"Top Diameter","description":"Diameter of the circular top face","unit":"mm","feature":"top_diameter"},"height":{"label":"Height","description":"Vertical height of the transition piece","unit":"mm","feature":"height"}},"features":{"base_width":{"kind":"dimension","axis":"x","label":"Base Width"},"base_depth":{"kind":"dimension","axis":"y","label":"Base Depth"},"top_diameter":{"kind":"dimension","axis":"x","label":"Top Diameter"},"height":{"kind":"dimension","axis":"z","label":"Height"}}} */

// User-editable parameters
base_width = 60;
base_depth = 40;
top_diameter = 30;
height = 60;

// Derived constants (not user-editable)
$fn = 64;
top_radius = top_diameter / 2;

// Module: Rectangular base profile centered at origin in XY plane
module rect_profile(w, d) {
    square([w, d], center=true);
}

// Module: Circular top profile centered at origin in XY plane
module circle_profile(d) {
    circle(d=d);
}

// Main design
// Loft from rectangular base to circular top
// The loft creates a solid with planar faces connecting the two profiles
// Base is at Z=0, Top is at Z=height

// To create the loft, we use a convex hull of the two profiles
// Profile 1: Rectangle at Z=0
// Profile 2: Circle at Z=height

hull() {
    // Bottom rectangular profile
    translate([0, 0, 0])
        linear_extrude(height=0.01, center=false)
            rect_profile(base_width, base_depth);
    
    // Top circular profile
    translate([0, 0, height])
        linear_extrude(height=0.01, center=false)
            circle_profile(top_diameter);
}
