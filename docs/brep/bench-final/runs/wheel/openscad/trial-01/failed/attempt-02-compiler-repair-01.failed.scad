Looking at the diagnosis, I need to:
1. Fix spoke connectivity (extend spokes to overlap hub and rim)
2. Fix orientation so the circular face is in the XZ plane (front view) rather than XY plane

The current model has the wheel lying flat (circular face in XY, thickness along Z), but the front view should show the circular face. I need to rotate the wheel so its axis is along Y, making the circular face visible from the front (looking down Y).

```openscad
/* doodle-meta {"version":1,"parameters":{"outer_diameter":{"label":"Outer Diameter","description":"Overall diameter of the wheel rim","unit":"mm","feature":"rim_od"},"rim_thickness":{"label":"Rim Thickness","description":"Radial thickness of the rim ring","unit":"mm","feature":"rim_thickness"},"wheel_width":{"label":"Wheel Width","description":"Axial thickness of the wheel (depth along Y)","unit":"mm","feature":"wheel_width"},"hub_diameter":{"label":"Hub Diameter","description":"Diameter of the central hub","unit":"mm","feature":"hub_diameter"},"spoke_count":{"label":"Spoke Count","description":"Number of radial spokes","unit":"count","feature":"spokes"},"spoke_width":{"label":"Spoke Width","description":"Width of each spoke","unit":"mm","feature":"spokes"}},"features":{"rim_od":{"kind":"dimension","axis":"x","label":"Outer Diameter"},"rim_thickness":{"kind":"dimension","axis":"x","label":"Rim Thickness"},"wheel_width":{"kind":"dimension","axis":"y","label":"Wheel Width"},"hub_diameter":{"kind":"dimension","axis":"x","label":"Hub Diameter"},"spokes":{"kind":"region","label":"Spokes","min":[0,0,0],"max":[{"parameter":"outer_diameter","scale":0.5,"offset":0},{"parameter":"wheel_width","scale":1,"offset":0},{"parameter":"outer_diameter","scale":0.5,"offset":0}]}}} */

// Parameters
outer_diameter = 120;
rim_thickness = 10;
wheel_width = 8;
hub_diameter = 30;
spoke_count = 8;
spoke_width = 8;

// Derived values
outer_radius = outer_diameter / 2;
inner_radius = outer_radius - rim_thickness;
hub_radius = hub_diameter / 2;
spoke_overlap = 3; // overlap into hub and rim for watertight connection
spoke_length = inner_radius - hub_radius + 2 * spoke_overlap;

// The wheel's circular face is in the XZ plane (front view looks down Y)
// Wheel axis is along Y. Build plate is Z=0, so wheel sits on its edge.

// Modules (all built in XZ plane, extruded along Y)

module rim() {
    difference() {
        cylinder(h = wheel_width, r = outer_radius, center = true);
        cylinder(h = wheel_width + 2, r = inner_radius, center = true);
    }
}

module hub() {
    cylinder(h = wheel_width, r = hub_radius, center = true);
}

module spoke() {
    // Spoke extends from hub_radius - overlap to inner_radius + overlap
    // Centered on X axis, extending in +X direction
    // Start position: hub_radius - spoke_overlap
    // Length: spoke_length (which includes overlap on both ends)
    translate([hub_radius - spoke_overlap + spoke_length / 2, 0, 0]) {
        cube([spoke_length, wheel_width, spoke_width], center = true);
    }
}

module spokes() {
    for (i = [0 : spoke_count - 1]) {
        rotate([0, 0, i * (360 / spoke_count)]) {
            spoke();
        }
    }
}

// Main Design
// Build the wheel in XZ plane (cylinders default axis is Z, but we need axis along Y)
// So we build with Z as the wheel axis, then rotate 90° about X to put axis along Y.
// Then translate so the wheel sits on the build plate (lowest point at Z=0).

// The wheel is built with its axis along Z (cylinders default), then rotated so axis is along Y.
// After rotation about X by 90°, the original Z-axis becomes Y-axis.
// The wheel's circular face is now in the XZ plane (visible from front looking down Y).
// The wheel's thickness is along Y.
// The wheel's lowest point (bottom of circle) needs to be at Z=0.

// Build wheel with axis along Z first, then rotate to align axis with Y.
// After rotate([90,0,0]), the Z-axis maps to -Y. The wheel center is at origin.
// The wheel extends from -outer_radius to +outer_radius in X and Z (after rotation).
// We need the bottom of the wheel (Z = -outer_radius after rotation) to be at Z=0.
// So translate up by outer_radius.

translate([0, 0, outer_radius]) {
    rotate([90, 0, 0]) {
        union() {
            rim();
            hub();
            spokes();
        }
    }
}
