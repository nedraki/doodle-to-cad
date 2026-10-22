/* doodle-meta {"version":1,"parameters":{"overall_width":{"label":"Overall width","description":"Diameter of the widest section (base flange)","unit":"mm","feature":"body_width"},"overall_height":{"label":"Overall height","description":"Total height of the knob from base to top","unit":"mm","feature":"body_height"},"base_diameter":{"label":"Base diameter","description":"Diameter of the bottom flange","unit":"mm","feature":"base_flange"},"base_height":{"label":"Base height","description":"Height of the bottom flange section","unit":"mm","feature":"base_flange"},"neck_diameter":{"label":"Neck diameter","description":"Diameter of the narrow middle section","unit":"mm","feature":"neck"},"neck_height":{"label":"Neck height","description":"Height of the narrow middle section","unit":"mm","feature":"neck"},"head_diameter":{"label":"Head diameter","description":"Diameter of the top head section","unit":"mm","feature":"head"},"head_height":{"label":"Head height","description":"Height of the top head section","unit":"mm","feature":"head"}},"features":{"body_width":{"kind":"dimension","axis":"x","label":"Overall width"},"body_height":{"kind":"dimension","axis":"z","label":"Overall height"},"base_flange":{"kind":"region","label":"Base flange","min":[{"parameter":"overall_width","scale":-0.5},{"parameter":"overall_width","scale":-0.5},0],"max":[{"parameter":"overall_width","scale":0.5},{"parameter":"overall_width","scale":0.5},{"parameter":"base_height"}]},"neck":{"kind":"region","label":"Neck","min":[{"parameter":"neck_diameter","scale":-0.5},{"parameter":"neck_diameter","scale":-0.5},{"parameter":"base_height"}],"max":[{"parameter":"neck_diameter","scale":0.5},{"parameter":"neck_diameter","scale":0.5},{"parameter":"base_height","offset":0,"parameter":"neck_height"}]},"head":{"kind":"region","label":"Head","min":[{"parameter":"head_diameter","scale":-0.5},{"parameter":"head_diameter","scale":-0.5},{"parameter":"base_height","offset":0,"parameter":"neck_height"}],"max":[{"parameter":"head_diameter","scale":0.5},{"parameter":"head_diameter","scale":0.5},{"parameter":"overall_height"}]}}} */

// Overall dimensions
overall_width = 56.0;
overall_height = 38.64;

// Section dimensions (derived from profile analysis)
base_diameter = 56.0;
base_height = 10.0;

neck_diameter = 20.0;
neck_height = 14.0;

head_diameter = 40.0;
head_height = 14.64;

// Derived positions
neck_z_start = base_height;
head_z_start = base_height + neck_height;

// Main body construction
module knob_body() {
    // Base flange
    translate([0, 0, 0])
        cylinder(h = base_height, d = base_diameter, center = false);
    
    // Neck
    translate([0, 0, neck_z_start])
        cylinder(h = neck_height, d = neck_diameter, center = false);
    
    // Head
    translate([0, 0, head_z_start])
        cylinder(h = head_height, d = head_diameter, center = false);
}

// Instantiate the design
knob_body();
