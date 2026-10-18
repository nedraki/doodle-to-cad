/* doodle-meta {"version":1,"parameters":{"outer_diameter":{"label":"Outer Diameter","description":"Diameter of the wheel rim","unit":"mm","feature":"outer_rim"},"wheel_thickness":{"label":"Wheel Thickness","description":"Axial thickness (width) of the wheel","unit":"mm","feature":"wheel_thickness"},"hub_diameter":{"label":"Hub Diameter","description":"Diameter of the central hub","unit":"mm","feature":"central_hub"},"spoke_count":{"label":"Spoke Count","description":"Number of radial spokes","unit":"count","feature":"spokes"},"spoke_width":{"label":"Spoke Width","description":"Width of each spoke","unit":"mm","feature":"spokes"}},"features":{"outer_rim":{"kind":"dimension","axis":"x","label":"Outer Diameter"},"wheel_thickness":{"kind":"dimension","axis":"z","label":"Wheel Thickness"},"central_hub":{"kind":"region","label":"Central Hub","min":[0,0,0],"max":[{"parameter":"hub_diameter","scale":0.5},{"parameter":"hub_diameter","scale":0.5},{"parameter":"wheel_thickness"}]},"spokes":{"kind":"region","label":"Spokes","min":[0,0,0],"max":[{"parameter":"outer_diameter","scale":0.5},{"parameter":"outer_diameter","scale":0.5},{"parameter":"wheel_thickness"}]}}} */

// Parameters
outer_diameter = 120.0;
wheel_thickness = 9.5;
hub_diameter = 30.0;
spoke_count = 8;
spoke_width = 10.0;

// Derived constants
$fn = 64;
eps = 0.01;
rim_thickness = 5.0;

// Main module
module wheel() {
    union() {
        // Outer Rim (Ring)
        difference() {
            cylinder(h = wheel_thickness, d = outer_diameter, center = true);
            cylinder(h = wheel_thickness + 2*eps, d = outer_diameter - 2*rim_thickness, center = true);
        }
        
        // Central Hub
        cylinder(h = wheel_thickness, d = hub_diameter, center = true);
        
        // Spokes
        for (i = [0 : spoke_count - 1]) {
            rotate([0, 0, i * 360 / spoke_count]) {
                // Spoke connects hub to rim
                // Length extends from center to outer radius + overlap into rim
                // Width is spoke_width
                // Positioned along X axis
                translate([0, 0, 0]) {
                    // Length: outer_diameter/2 + rim_thickness ensures overlap with rim
                    // Centered at 0, so it spans from -(L/2) to +(L/2)
                    // We want it to start at 0 (center) and go to outer edge.
                    // So we translate it by L/2 in X? 
                    // Or just make it long enough and centered.
                    // If centered at 0, length L covers -L/2 to L/2.
                    // We want coverage from 0 to outer_radius.
                    // So L/2 should be >= outer_radius.
                    // L = outer_diameter/2 + rim_thickness.
                    // L/2 = outer_diameter/4 + rim_thickness/2.
                    // This is not enough to reach the rim if centered at 0.
                    // The spoke needs to reach from center (0) to outer radius (60).
                    // So the cube should span from 0 to 60+overlap.
                    // Let's use translate to position it correctly.
                    // Cube centered at [L/2, 0, 0] with size [L, W, H].
                    // This spans X from 0 to L.
                    cube([outer_diameter/2 + rim_thickness, spoke_width, wheel_thickness], center = true);
                }
            }
        }
    }
}

// Final instantiation
// The wheel is centered at Z=0 in the module.
// We need to move it so the bottom is at Z=0.
translate([0, 0, wheel_thickness/2]) {
    wheel();
}
