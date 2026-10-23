/* doodle-meta {"version":1,"parameters":{"outer_diameter":{"label":"Outer Diameter","description":"Diameter of the wheel rim","unit":"mm","feature":"wheel_body"},"wheel_thickness":{"label":"Wheel Thickness","description":"Thickness of the wheel (axial depth)","unit":"mm","feature":"wheel_body"},"hub_diameter":{"label":"Hub Diameter","description":"Diameter of the central hub","unit":"mm","feature":"wheel_body"},"spoke_count":{"label":"Spoke Count","description":"Number of spokes","unit":"count","feature":"wheel_body"},"spoke_width":{"label":"Spoke Width","description":"Width of each spoke","unit":"mm","feature":"wheel_body"}},"features":{"wheel_body":{"kind":"region","label":"Wheel Body","min":[0,0,0],"max":[{"parameter":"outer_diameter","scale":0.5},{"parameter":"wheel_thickness","offset":0},{"parameter":"outer_diameter","scale":0.5}]}}} */

// Parameters
outer_diameter = 120;
wheel_thickness = 9.5;
hub_diameter = 30;
spoke_count = 8;
spoke_width = 8;
rim_thickness = 5;

// Derived parameters
outer_radius = outer_diameter / 2;
hub_radius = hub_diameter / 2;
inner_rim_radius = outer_radius - rim_thickness;

// Spoke dimensions
spoke_start_radius = hub_radius - 2;
spoke_end_radius = inner_rim_radius + 2;
spoke_length = spoke_end_radius - spoke_start_radius;
spoke_center_radius = (spoke_start_radius + spoke_end_radius) / 2;

module wheel() {
    union() {
        // Rim
        difference() {
            cylinder(h = wheel_thickness, r = outer_radius, center = false);
            cylinder(h = wheel_thickness, r = inner_rim_radius, center = false);
        }
        
        // Hub
        cylinder(h = wheel_thickness, r = hub_radius, center = false);
        
        // Spokes
        for (i = [0 : spoke_count - 1]) {
            rotate([0, 0, i * (360 / spoke_count)]) {
                translate([spoke_center_radius, 0, wheel_thickness / 2]) {
                    cube([spoke_length, spoke_width, wheel_thickness], center = true);
                }
            }
        }
    }
}

// Rotate the entire wheel so the axis aligns with Y
// Original axis is Z, we need it along Y.
// rotate([90, 0, 0]) rotates Z to -Y.
// translate([0, wheel_thickness, 0]) moves it back to Y=0..wheel_thickness.
rotate([90, 0, 0]) {
    translate([0, -wheel_thickness, 0]) {
        wheel();
    }
}
