/* doodle-meta {"version":1,"parameters":{"outer_diameter":{"label":"Outer Diameter","description":"Diameter of the wheel rim","unit":"mm","feature":"outer_diameter"},"thickness":{"label":"Thickness","description":"Height of the wheel disc","unit":"mm","feature":"thickness"},"hub_diameter":{"label":"Hub Diameter","description":"Diameter of the central hub","unit":"mm","feature":"hub_diameter"},"spoke_width":{"label":"Spoke Width","description":"Width of each radial spoke","unit":"mm","feature":"spoke_width"},"spoke_count":{"label":"Spoke Count","description":"Number of spokes","unit":"count","feature":"spoke_count"}},"features":{"outer_diameter":{"kind":"dimension","axis":"x","label":"Outer Diameter"},"thickness":{"kind":"dimension","axis":"z","label":"Thickness"},"hub_diameter":{"kind":"dimension","axis":"x","label":"Hub Diameter"},"spoke_width":{"kind":"dimension","axis":"x","label":"Spoke Width"},"spoke_count":{"kind":"dimension","axis":"z","label":"Spoke Count"}}} */

// Parameters
outer_diameter = 120.0;
thickness = 9.5;
hub_diameter = 30.0;
spoke_width = 8.0;
spoke_count = 8;

// Derived constants
$fn = 64;
eps = 0.01;

// Modules
module wheel_body() {
    // Outer Rim
    difference() {
        cylinder(d=outer_diameter, h=thickness, center=false);
        translate([0,0,-eps])
            cylinder(d=outer_diameter - 2*thickness, h=thickness + 2*eps, center=false);
    }
    
    // Central Hub
    translate([0,0,0])
        cylinder(d=hub_diameter, h=thickness, center=false);
        
    // Spokes
    for (i = [0 : spoke_count - 1]) {
        rotate([0, 0, i * (360 / spoke_count)])
            translate([0, -spoke_width/2, 0])
                cube([outer_diameter/2, spoke_width, thickness]);
    }
}

// Main Design
wheel_body();
