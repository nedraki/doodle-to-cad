/* doodle-meta {"version":1,"parameters":{"outer_diameter":{"label":"Outer Diameter","description":"Diameter of the wheel rim","unit":"mm","feature":"outer_diameter"},"thickness":{"label":"Thickness","description":"Thickness of the wheel disc","unit":"mm","feature":"thickness"},"hub_diameter":{"label":"Hub Diameter","description":"Diameter of the central hub","unit":"mm","feature":"hub_diameter"},"spoke_width":{"label":"Spoke Width","description":"Width of each radial spoke","unit":"mm","feature":"spoke_width"},"spoke_count":{"label":"Spoke Count","description":"Number of radial spokes","unit":"count","feature":"spoke_count"}},"features":{"outer_diameter":{"kind":"dimension","axis":"x","label":"Outer Diameter"},"thickness":{"kind":"dimension","axis":"z","label":"Thickness"},"hub_diameter":{"kind":"dimension","axis":"x","label":"Hub Diameter"},"spoke_width":{"kind":"dimension","axis":"x","label":"Spoke Width"},"spoke_count":{"kind":"dimension","axis":"z","label":"Spoke Count"}}} */

// Parameters
outer_diameter = 120.0;
thickness = 8.0;
hub_diameter = 30.0;
spoke_width = 10.0;
spoke_count = 8;

// Derived values
outer_radius = outer_diameter / 2.0;
hub_radius = hub_diameter / 2.0;
rim_thickness = 10.0;
inner_rim_radius = outer_radius - rim_thickness;

module wheel_disc() {
    union() {
        // Outer Rim - ring in XY plane, extruded along Z
        difference() {
            // Outer cylinder along Z axis
            cylinder(h=thickness, r=outer_radius, center=true);
            // Inner cutout along Z axis
            cylinder(h=thickness+2, r=inner_rim_radius, center=true);
        }

        // Central Hub - solid disk along Z axis
        cylinder(h=thickness, r=hub_radius, center=true);

        // Spokes - bars in XY plane, extruded along Z
        for (i = [0 : spoke_count - 1]) {
            rotate([0, 0, i * (360 / spoke_count)]) {
                // Spoke extends from center outward to outer_radius to ensure
                // overlap with both hub and rim
                translate([outer_radius / 2.0, 0, 0]) {
                    cube([outer_radius, spoke_width, thickness], center=true);
                }
            }
        }
    }
}

// Position so the wheel sits on the build plate (lowest Z = 0)
// The wheel face is in XY plane, centered at origin in X and Y.
// Lowest point of the wheel is at Z = -thickness/2, so translate up by thickness/2.
translate([0, 0, thickness/2]) {
    wheel_disc();
}
