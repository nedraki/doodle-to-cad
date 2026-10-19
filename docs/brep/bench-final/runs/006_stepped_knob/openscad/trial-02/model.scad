/* doodle-meta {"version":1,"parameters":{"total_height":{"label":"Total Height","description":"Overall height of the knob from base to top","unit":"mm","feature":"overall_height"},"base_diameter":{"label":"Base Diameter","description":"Diameter of the wide bottom flange","unit":"mm","feature":"base_diameter"},"neck_diameter":{"label":"Neck Diameter","description":"Diameter of the narrow middle section","unit":"mm","feature":"neck_diameter"},"head_diameter":{"label":"Head Diameter","description":"Diameter of the wide top section","unit":"mm","feature":"head_diameter"},"base_height":{"label":"Base Height","description":"Height of the bottom flange section","unit":"mm","feature":"base_height"},"head_height":{"label":"Head Height","description":"Height of the top head section","unit":"mm","feature":"head_height"}},"features":{"overall_height":{"kind":"dimension","axis":"z","label":"Total Height"},"base_diameter":{"kind":"dimension","axis":"x","label":"Base Diameter"},"neck_diameter":{"kind":"dimension","axis":"x","label":"Neck Diameter"},"head_diameter":{"kind":"dimension","axis":"x","label":"Head Diameter"},"base_height":{"kind":"dimension","axis":"z","label":"Base Height"},"head_height":{"kind":"dimension","axis":"z","label":"Head Height"}}} */

// Parameters
total_height = 56.0;
base_diameter = 56.0;
neck_diameter = 28.0;
head_diameter = 40.0;
base_height = 10.0;
head_height = 11.0;

// Derived dimensions
base_radius = base_diameter / 2;
neck_radius = neck_diameter / 2;
head_radius = head_diameter / 2;
neck_height = total_height - base_height - head_height;

// Modules
module knob_body() {
    // Base Flange
    translate([0, 0, 0])
        cylinder(h = base_height, r = base_radius, center = false);
    
    // Neck
    translate([0, 0, base_height])
        cylinder(h = neck_height, r = neck_radius, center = false);
    
    // Head
    translate([0, 0, base_height + neck_height])
        cylinder(h = head_height, r = head_radius, center = false);
}

// Main Design
knob_body();
