/* doodle-meta {"version":1,"parameters":{"outer_diameter":{"label":"Outer Diameter","description":"Diameter of the wheel rim","unit":"mm","feature":"rim"},"wheel_thickness":{"label":"Wheel Thickness","description":"Width of the wheel along the axle axis","unit":"mm","feature":"body"},"hub_diameter":{"label":"Hub Diameter","description":"Diameter of the central hub","unit":"mm","feature":"hub"},"spoke_count":{"label":"Spoke Count","description":"Number of radial spokes","unit":"count","feature":"spokes"},"spoke_width":{"label":"Spoke Width","description":"Width of each spoke","unit":"mm","feature":"spokes"}},"features":{"rim":{"kind":"dimension","axis":"x","label":"Outer Diameter"},"body":{"kind":"dimension","axis":"y","label":"Wheel Thickness"},"hub":{"kind":"region","label":"Hub","min":[0,0,0],"max":[{"parameter":"hub_diameter","scale":0.5},{"parameter":"wheel_thickness","scale":0.5},{"parameter":"wheel_thickness","scale":0.5}]},"spokes":{"kind":"region","label":"Spokes","min":[{"parameter":"hub_diameter","scale":0.5},{"parameter":"wheel_thickness","scale":0.5},{"parameter":"wheel_thickness","scale":0.5}],[{"parameter":"outer_diameter","scale":0.5},{"parameter":"wheel_thickness","scale":0.5},{"parameter":"wheel_thickness","scale":0.5}]}}} */

// Parameters
outer_diameter = 120.0;
wheel_thickness = 9.5;
hub_diameter = 24.0;
spoke_count = 8;
spoke_width = 6.0;

// Derived dimensions
outer_radius = outer_diameter / 2.0;
hub_radius = hub_diameter / 2.0;
rim_inner_radius = outer_radius - 4.0;
spoke_length = outer_radius; // Extend to outer radius to ensure overlap with rim

// Modules
module wheel_body() {
    // Rim: Outer cylinder minus inner cylinder
    difference() {
        cylinder(h = wheel_thickness, r = outer_radius, center = true);
        cylinder(h = wheel_thickness + 0.1, r = rim_inner_radius, center = true);
    }
    
    // Hub: Central cylinder
    cylinder(h = wheel_thickness, r = hub_radius, center = true);
    
    // Spokes: Array of rectangular bars
    for (i = [0 : spoke_count - 1]) {
        rotate([0, 0, i * (360.0 / spoke_count)]) {
            // Translate so the spoke starts at the hub center and extends to the rim
            // The cube is centered at [spoke_length/2, 0, 0] relative to the rotation
            // This ensures it spans from 0 to spoke_length (which is outer_radius)
            translate([spoke_length / 2.0, 0, 0]) {
                cube([spoke_length, spoke_width, wheel_thickness], center = true);
            }
        }
    }
}

// Main Design
// Rotate the wheel assembly by 90 degrees around the X-axis to orient the wheel face in the XZ plane (Front view)
// and the thickness along the Y-axis (Right view).
// Then translate so the lowest point sits on Z=0.
translate([0, 0, outer_radius]) {
    rotate([90, 0, 0]) {
        wheel_body();
    }
}
