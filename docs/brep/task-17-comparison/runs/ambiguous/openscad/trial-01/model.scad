/* doodle-meta {"version":1,"parameters":{"width":{"label":"Overall width","description":"Changes the body width","unit":"mm","feature":"body_width"},"depth":{"label":"Overall depth","description":"Changes the body depth","unit":"mm","feature":"body_depth"},"height":{"label":"Overall height","description":"Changes the body height","unit":"mm","feature":"body_height"},"hole_diameter":{"label":"Hole diameter","description":"Changes the diameter of the central through-hole","unit":"mm","feature":"central_hole"}},"features":{"body_width":{"kind":"dimension","axis":"x","label":"Overall width"},"body_depth":{"kind":"dimension","axis":"y","label":"Overall depth"},"body_height":{"kind":"dimension","axis":"z","label":"Overall height"},"central_hole":{"kind":"region","label":"Central through-hole","min":[{"parameter":"width","scale":0.5,"offset":-4.0},{"parameter":"depth","scale":0.5,"offset":-4.0},0],"max":[{"parameter":"width","scale":0.5,"offset":4.0},{"parameter":"depth","scale":0.5,"offset":4.0},{"parameter":"height","scale":1.0,"offset":0}]}}} */

// Parameters
width = 40.0;
depth = 4.34;
height = 12.0;
hole_diameter = 8.0;

// Derived constants (not user-editable)
eps = 0.1;

// Main design
difference() {
    // Positive body: rectangular block sitting on Z=0
    cube([width, depth, height], center=false);

    // Subtractive through-hole: axis along Z, centered in XY
    translate([width/2, depth/2, -eps])
        cylinder(d=hole_diameter, h=height + 2*eps, center=false);
}
