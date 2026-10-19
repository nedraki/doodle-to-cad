Looking at the diagnosis, I need to:
1. Fix spoke connectivity (spokes don't reach the rim)
2. Fix orientation so front view shows the wheel face (currently showing edge-on)
3. Ensure single connected solid

The key issues:
- Spokes are too short (don't overlap rim inner boundary)
- The wheel is oriented with its face in XY plane (top view shows it), but front view should show the face
- Need to rotate the entire assembly so the wheel face is in XZ plane (front view)

```openscad
/* doodle-meta {"version":1,"parameters":{"outer_diameter":{"label":"Outer Diameter","description":"Diameter of the wheel rim","unit":"mm","feature":"outer_rim"},"thickness":{"label":"Thickness","description":"Axial thickness of the wheel disc","unit":"mm","feature":"body_thickness"},"hub_diameter":{"label":"Hub Diameter","description":"Diameter of the central hub","unit":"mm","feature":"central_hub"},"spoke_width":{"label":"Spoke Width","description":"Width of each radial spoke","unit":"mm","feature":"spokes"},"spoke_count":{"label":"Spoke Count","description":"Number of radial spokes","unit":"count","feature":"spokes"}},"features":{"outer_rim":{"kind":"dimension","axis":"x","label":"Outer Diameter"},"body_thickness":{"kind":"dimension","axis":"y","label":"Thickness"},"central_hub":{"kind":"dimension","axis":"x","label":"Hub Diameter"},"spokes":{"kind":"region","label":"Spokes","min":[0,0,0],"max":[{"parameter":"outer_diameter","scale":0.5},{"parameter":"thickness"},{"parameter":"outer_diameter","scale":0.5}]}}} */

// Parameters
outer_diameter = 120.0;
thickness = 9.5;
hub_diameter = 30.0;
spoke_width = 8.0;
spoke_count = 8;

// Derived values
outer_radius = outer_diameter / 2;
hub_radius = hub_diameter / 2;
rim_thickness = 4.0;
inner_rim_radius = outer_radius - rim_thickness;
// Spoke length must overlap both hub and rim for connectivity
spoke_length = outer_radius - hub_radius + rim_thickness;

// Main module - wheel face in XZ plane, thickness along Y
module wheel_disc() {
    union() {
        // Outer Rim - ring in XZ plane, extruded along Y
        difference() {
            cylinder(h=thickness, r=outer_radius, center=true);
            cylinder(h=thickness+2, r=inner_rim_radius, center=true);
        }
        
        // Central Hub - solid disk in XZ plane, extruded along Y
        cylinder(h=thickness, r=hub_radius, center=true);
        
        // Spokes - radial bars in XZ plane, extruded along Y
        for (i = [0 : spoke_count - 1]) {
            rotate([0, 0, i * (360 / spoke_count)]) {
                translate([hub_radius, 0, 0]) {
                    cube([spoke_length, spoke_width, thickness], center=true);
                }
            }
        }
    }
}

// Rotate so wheel face is in XZ plane (front view shows the face)
// Original cylinder axis is Z, we need it along Y for front view
rotate([90, 0, 0]) {
    translate([0, 0, thickness/2]) {
        wheel_disc();
    }
}
