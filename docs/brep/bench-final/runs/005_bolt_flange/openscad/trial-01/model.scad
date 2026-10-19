/* doodle-meta {"version":1,"parameters":{"outer_diameter":{"label":"Outer Diameter","description":"Diameter of the flange body","unit":"mm","feature":"body_diameter"},"thickness":{"label":"Thickness","description":"Height of the flange plate","unit":"mm","feature":"body_thickness"},"bore_diameter":{"label":"Center Bore Diameter","description":"Diameter of the central through-hole","unit":"mm","feature":"center_bore"},"bolt_hole_diameter":{"label":"Bolt Hole Diameter","description":"Diameter of the four bolt holes","unit":"mm","feature":"bolt_holes"},"bolt_circle_diameter":{"label":"Bolt Circle Diameter","description":"Diameter of the circle on which bolt holes are centered","unit":"mm","feature":"bolt_holes"}},"features":{"body_diameter":{"kind":"dimension","axis":"x","label":"Outer Diameter"},"body_thickness":{"kind":"dimension","axis":"y","label":"Thickness"},"center_bore":{"kind":"region","label":"Center Bore","min":[-20,0,-20],"max":[20,10,20]},"bolt_holes":{"kind":"region","label":"Bolt Holes","min":[-42.5,0,-42.5],"max":[42.5,10,42.5]}}} */

// Parameters
outer_diameter = 120;
thickness = 10;
bore_diameter = 40;
bolt_hole_diameter = 10;
bolt_circle_diameter = 85;

// Derived constants
$fn = 64;
eps = 0.01;

// Bolt hole offset from center (half of bolt circle diameter projected to XZ)
// For 4 holes at 45-degree positions on bolt circle: offset = bolt_circle_diameter/2 * cos(45) = bolt_circle_diameter/2 * 0.7071
// But spec says positions are at (±30, ±30), so we use that directly
bolt_offset = 30;

// Main module
module flange() {
    difference() {
        // Base body: Cylinder oriented along Y-axis
        // Positioned so back is at Y=0, front at Y=thickness
        // Centered in X and Z
        translate([0, 0, 0])
            rotate([90, 0, 0])
                cylinder(d=outer_diameter, h=thickness, center=false);
        
        // Center Bore - through cut along Y
        translate([0, -eps, 0])
            rotate([90, 0, 0])
                cylinder(d=bore_diameter, h=thickness + 2*eps, center=false);
        
        // Bolt Holes - 4 holes at (±30, ±30) in XZ plane, cut along Y
        // Hole 1: (-30, 30) in XZ
        translate([-bolt_offset, -eps, bolt_offset])
            rotate([90, 0, 0])
                cylinder(d=bolt_hole_diameter, h=thickness + 2*eps, center=false);
        
        // Hole 2: (30, 30) in XZ
        translate([bolt_offset, -eps, bolt_offset])
            rotate([90, 0, 0])
                cylinder(d=bolt_hole_diameter, h=thickness + 2*eps, center=false);
        
        // Hole 3: (-30, -30) in XZ
        translate([-bolt_offset, -eps, -bolt_offset])
            rotate([90, 0, 0])
                cylinder(d=bolt_hole_diameter, h=thickness + 2*eps, center=false);
        
        // Hole 4: (30, -30) in XZ
        translate([bolt_offset, -eps, -bolt_offset])
            rotate([90, 0, 0])
                cylinder(d=bolt_hole_diameter, h=thickness + 2*eps, center=false);
    }
}

// Instantiate
flange();
