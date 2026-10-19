/* doodle-meta {"version":1,"parameters":{"outer_diameter":{"label":"Outer Diameter","description":"Diameter of the wheel rim","unit":"mm","feature":"outer_rim"},"thickness":{"label":"Thickness","description":"Height of the wheel disc (Z-axis)","unit":"mm","feature":"body_thickness"},"hub_diameter":{"label":"Hub Diameter","description":"Diameter of the central hub","unit":"mm","feature":"central_hub"},"spoke_width":{"label":"Spoke Width","description":"Width of each radial spoke","unit":"mm","feature":"spokes"},"spoke_count":{"label":"Spoke Count","description":"Number of spokes","unit":"count","feature":"spokes"}},"features":{"outer_rim":{"kind":"dimension","axis":"x","label":"Outer Diameter"},"body_thickness":{"kind":"dimension","axis":"z","label":"Thickness"},"central_hub":{"kind":"dimension","axis":"x","label":"Hub Diameter"},"spokes":{"kind":"region","label":"Spokes","min":[0,0,0],"max":[120,120,8]}}} */

// Parameters
outer_diameter = 120.0;
thickness = 8.0;
hub_diameter = 30.0;
spoke_width = 10.0;
spoke_count = 8;

// Derived values
outer_radius = outer_diameter / 2;
hub_radius = hub_diameter / 2;
spoke_length = outer_radius - hub_radius;

// Main module
module wheel_disc() {
    difference() {
        union() {
            // Outer Rim
            difference() {
                cylinder(h = thickness, r = outer_radius, center = true);
                cylinder(h = thickness + 2, r = outer_radius - 10, center = true); // Rim thickness 10mm
            }
            
            // Central Hub
            cylinder(h = thickness, r = hub_radius, center = true);
            
            // Spokes
            for (i = [0 : spoke_count - 1]) {
                rotate([0, 0, i * (360 / spoke_count)]) {
                    translate([hub_radius, 0, 0]) {
                        cube([spoke_length, spoke_width, thickness], center = true);
                    }
                }
            }
        }
        
        // Optional: Center hole for axle (not explicitly requested but common, keeping solid as per "central solid disk")
        // If a hole was needed, it would be subtracted here. 
        // The spec says "central solid disk", so we leave it solid.
    }
}

// Position on build plate (Z=0 to Z=thickness)
translate([0, 0, thickness / 2]) {
    wheel_disc();
}
