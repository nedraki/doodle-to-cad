I'll analyze the diagnosis and repair the orientation. The wheel's axis must be along Z (vertical), built directly in the XY plane with cylinders (default Z axis), then translated up by `outer_radius` so the lowest point sits at Z=0. This removes the `rotate([90,0,0])` and fixes the dimension swap (X=120, Y=120, Z=8).

Key changes:
- Remove `rotate([90,0,0])` — build wheel with axis along Z directly.
- Spokes become flat plates in XY (thickness along Z), rotated about Z.
- Translate up by `outer_radius` so the wheel rests on the build plate.
- Update doodle-meta feature coordinates to match the new Z-axis orientation.

```openscad
/* doodle-meta {"version":1,"parameters":{"outer_diameter":{"label":"Outer Diameter","description":"Overall diameter of the wheel rim","unit":"mm","feature":"rim_od"},"rim_thickness":{"label":"Rim Thickness","description":"Radial thickness of the rim ring","unit":"mm","feature":"rim_thickness"},"wheel_width":{"label":"Wheel Width","description":"Axial thickness of the wheel (height along Z)","unit":"mm","feature":"wheel_width"},"hub_diameter":{"label":"Hub Diameter","description":"Diameter of the central hub","unit":"mm","feature":"hub_diameter"},"spoke_count":{"label":"Spoke Count","description":"Number of radial spokes","unit":"count","feature":"spokes"},"spoke_width":{"label":"Spoke Width","description":"Width of each spoke","unit":"mm","feature":"spokes"}},"features":{"rim_od":{"kind":"dimension","axis":"x","label":"Outer Diameter"},"rim_thickness":{"kind":"dimension","axis":"x","label":"Rim Thickness"},"wheel_width":{"kind":"dimension","axis":"z","label":"Wheel Width"},"hub_diameter":{"kind":"dimension","axis":"x","label":"Hub Diameter"},"spokes":{"kind":"region","label":"Spokes","min":[{"parameter":"outer_diameter","scale":-0.5,"offset":0},{"parameter":"outer_diameter","scale":-0.5,"offset":0},0],"max":[{"parameter":"outer_diameter","scale":0.5,"offset":0},{"parameter":"outer_diameter","scale":0.5,"offset":0},{"parameter":"wheel_width","scale":1,"offset":0}]}}} */

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

// The wheel's circular face lies in the XY plane (front view looks down Y).
// The wheel axis is along Z (vertical). Build plate is Z=0, so the wheel
// rests on its edge: lowest point of the rim at Z=0.

// Modules (built with axis along Z, extruded along Z)

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
    // Centered on X axis, extending in +X direction.
    // Flat plate: width along Y, thickness along Z.
    translate([hub_radius - spoke_overlap + spoke_length / 2, 0, 0]) {
        cube([spoke_length, spoke_width, wheel_width], center = true);
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
// Build the wheel with its axis along Z (cylinders default axis is Z).
// The circular face is in the XY plane; thickness is along Z.
// Translate up by outer_radius so the lowest point of the rim sits at Z=0.

translate([0, 0, outer_radius]) {
    union() {
        rim();
        hub();
        spokes();
    }
}
