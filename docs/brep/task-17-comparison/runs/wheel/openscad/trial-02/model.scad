/* doodle-meta {"version":1,"parameters":{"outer_diameter":{"label":"Outer Diameter","description":"Diameter of the wheel rim","unit":"mm","feature":"body_width"},"thickness":{"label":"Thickness","description":"Axial thickness of the disc","unit":"mm","feature":"body_height"},"hub_diameter":{"label":"Hub Diameter","description":"Diameter of the central hub","unit":"mm","feature":"hub"},"spoke_width":{"label":"Spoke Width","description":"Width of each radial spoke","unit":"mm","feature":"spokes"},"spoke_count":{"label":"Spoke Count","description":"Number of radial spokes","unit":"count","feature":"spokes"}},"features":{"body_width":{"kind":"dimension","axis":"x","label":"Outer Diameter"},"body_height":{"kind":"dimension","axis":"z","label":"Thickness"},"hub":{"kind":"region","label":"Central Hub","min":[{"parameter":"hub_diameter","scale":-0.5},{"parameter":"hub_diameter","scale":-0.5},0],"max":[{"parameter":"hub_diameter","scale":0.5},{"parameter":"hub_diameter","scale":0.5},{"parameter":"thickness"}]},"spokes":{"kind":"region","label":"Spokes","min":[{"parameter":"outer_diameter","scale":-0.5},{"parameter":"outer_diameter","scale":-0.5},0],"max":[{"parameter":"outer_diameter","scale":0.5},{"parameter":"outer_diameter","scale":0.5},{"parameter":"thickness"}]}}} */

// Parameters
outer_diameter = 120.0;
thickness = 9.5;
hub_diameter = 30.0;
spoke_width = 8.0;
spoke_count = 8;

// Derived constants
$fn = 64;
outer_radius = outer_diameter / 2;
hub_radius = hub_diameter / 2;
rim_thickness = 8.0; // Estimated rim band thickness
inner_rim_radius = outer_radius - rim_thickness;

// Main module
module wheel_disc() {
    difference() {
        // Positive Body: Union of Hub, Rim, and Spokes
        union() {
            // 1. Central Hub
            cylinder(h=thickness, r=hub_radius, center=false);
            
            // 2. Outer Rim
            difference() {
                cylinder(h=thickness, r=outer_radius, center=false);
                cylinder(h=thickness + 0.2, r=inner_rim_radius, center=true);
            }
            
            // 3. Spokes
            for (i = [0 : spoke_count - 1]) {
                rotate([0, 0, i * (360 / spoke_count)]) {
                    // Spoke connects hub to rim
                    // Length extends from center to outer radius to ensure overlap
                    translate([0, -spoke_width/2, 0]) {
                        cube([outer_radius, spoke_width, thickness]);
                    }
                }
            }
        }
        
        // Subtractive Cutters (if any)
        // Currently none required as the structure is defined by the union of positive parts.
        // If a center hole was needed, it would go here.
    }
}

// Instantiate design
wheel_disc();
