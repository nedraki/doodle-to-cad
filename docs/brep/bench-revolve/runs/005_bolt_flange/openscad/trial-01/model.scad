/* doodle-meta {"version":1,"parameters":{"outer_diameter":{"label":"Outer Diameter","description":"Diameter of the flange outer circle","unit":"mm","feature":"outer_profile"},"thickness":{"label":"Thickness","description":"Height of the flange plate","unit":"mm","feature":"body_thickness"},"bore_diameter":{"label":"Center Bore Diameter","description":"Diameter of the central through hole","unit":"mm","feature":"center_bore"},"bolt_hole_diameter":{"label":"Bolt Hole Diameter","description":"Diameter of the four bolt holes","unit":"mm","feature":"bolt_holes"},"bolt_circle_diameter":{"label":"Bolt Circle Diameter","description":"Diameter of the circle passing through bolt hole centers","unit":"mm","feature":"bolt_pattern"}},"features":{"outer_profile":{"kind":"dimension","axis":"x","label":"Outer Diameter"},"body_thickness":{"kind":"dimension","axis":"y","label":"Thickness"},"center_bore":{"kind":"region","label":"Center Bore","min":[{"parameter":"bore_diameter","scale":-0.5,"offset":0},0,{"parameter":"bore_diameter","scale":-0.5,"offset":0}],"max":[{"parameter":"bore_diameter","scale":0.5,"offset":0},{"parameter":"thickness","scale":1,"offset":0},{"parameter":"bore_diameter","scale":0.5,"offset":0}]},"bolt_holes":{"kind":"region","label":"Bolt Holes","min":[{"parameter":"bolt_circle_diameter","scale":-0.5,"offset":0},0,{"parameter":"bolt_circle_diameter","scale":-0.5,"offset":0}],"max":[{"parameter":"bolt_circle_diameter","scale":0.5,"offset":0},{"parameter":"thickness","scale":1,"offset":0},{"parameter":"bolt_circle_diameter","scale":0.5,"offset":0}]}}} */

// Parameters
outer_diameter = 120.0;
thickness = 18.75;
bore_diameter = 40.0;
bolt_hole_diameter = 12.0;
bolt_circle_diameter = 80.0;

// Derived constants
eps = 0.1;
bolt_radius = bolt_circle_diameter / 2.0;

// Main Design
difference() {
    // Positive Body: Flange Plate
    // Flat face lies in XZ plane (Front view).
    // Thickness extends along Y-axis.
    // Sits on build plate (Z=0 to Z=outer_diameter).
    // Centered in X (-60 to 60) and Y (-thickness/2 to thickness/2).
    translate([0, 0, outer_diameter/2])
        rotate([90, 0, 0])
            cylinder(d=outer_diameter, h=thickness, center=true);

    // Subtractive Cutters
    
    // Center Bore
    // Axis along Y (depth), cuts through thickness
    translate([0, 0, outer_diameter/2])
        rotate([90, 0, 0])
            cylinder(d=bore_diameter, h=thickness + 2*eps, center=true);

    // Bolt Holes (4x)
    // Axis along Y (depth), cuts through thickness
    // Positions in XZ plane (Front view)
    // Angles: 45, 135, 225, 315 degrees relative to center (0, outer_diameter/2)
    for (angle = [45, 135, 225, 315]) {
        translate([
            bolt_radius * cos(angle),
            0,
            outer_diameter/2 + bolt_radius * sin(angle)
        ])
        rotate([90, 0, 0])
            cylinder(d=bolt_hole_diameter, h=thickness + 2*eps, center=true);
    }
}
