/* doodle-meta {"version":1,"parameters":{"outer_diameter":{"label":"Outer Diameter","description":"Diameter of the wheel rim","unit":"mm","feature":"outer_rim"},"thickness":{"label":"Thickness","description":"Height of the wheel disc","unit":"mm","feature":"body_thickness"},"hub_diameter":{"label":"Hub Diameter","description":"Diameter of the central hub","unit":"mm","feature":"central_hub"},"spoke_width":{"label":"Spoke Width","description":"Width of each radial spoke","unit":"mm","feature":"spokes"},"spoke_count":{"label":"Spoke Count","description":"Number of radial spokes","unit":"count","feature":"spokes"}},"features":{"outer_rim":{"kind":"dimension","axis":"x","label":"Outer Diameter"},"body_thickness":{"kind":"dimension","axis":"z","label":"Thickness"},"central_hub":{"kind":"dimension","axis":"x","label":"Hub Diameter"},"spokes":{"kind":"region","label":"Spokes","min":[0,0,0],"max":[{"parameter":"outer_diameter","scale":0.5},{"parameter":"outer_diameter","scale":0.5},{"parameter":"thickness"}]}}} */

// Parameters
outer_diameter = 120.0;
thickness = 9.5;
hub_diameter = 30.0;
spoke_width = 8.0;
spoke_count = 8;

// Derived constants
outer_radius = outer_diameter / 2;
hub_radius = hub_diameter / 2;
eps = 0.01;

// Main Design
wheel_disc();

module wheel_disc() {
    // 1. Base Solid: Outer Cylinder
    // Positioned so bottom is at Z=0
    translate([0, 0, 0])
        cylinder(h=thickness, r=outer_radius, center=false, $fn=128);

    // 2. Subtract Inter-Spoke Voids
    // We subtract the space between spokes to leave the rim, hub, and spokes.
    // The voids are sectors of an annulus from hub_radius to outer_radius.
    difference() {
        // Re-assert base solid for difference context (though we are inside a module, 
        // standard practice is to build positive then subtract. 
        // Here we use a union of positive parts approach which is cleaner for spokes)
        
        // Actually, let's use the Union approach for clarity and manifold safety:
        // Union of Rim + Hub + Spokes.
    }
    
    // Let's restart the module logic with a Union approach which is robust for this shape.
    union() {
        // Outer Rim
        difference() {
            cylinder(h=thickness, r=outer_radius, center=false, $fn=128);
            cylinder(h=thickness + 2*eps, r=outer_radius - spoke_width, center=true, $fn=128);
        }
        
        // Central Hub
        cylinder(h=thickness, r=hub_radius, center=false, $fn=64);
        
        // Spokes
        for (i = [0 : spoke_count - 1]) {
            rotate([0, 0, i * (360 / spoke_count)]) {
                // Spoke extends from center (overlapping hub) to outer edge (overlapping rim)
                // Width is spoke_width, Length is outer_radius
                translate([0, -spoke_width/2, 0])
                    cube([outer_radius, spoke_width, thickness]);
            }
        }
    }
}
