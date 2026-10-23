/* doodle-meta {"version":1,"parameters":{"total_height":{"label":"Total Height","description":"Overall height of the knob from base to top cap","unit":"mm","feature":"overall_height"},"base_radius":{"label":"Base Radius","description":"Radius of the bottom flange","unit":"mm","feature":"base_flange"},"neck_radius":{"label":"Neck Radius","description":"Radius of the middle neck section","unit":"mm","feature":"neck"},"cap_radius":{"label":"Cap Radius","description":"Radius of the top cap","unit":"mm","feature":"top_cap"},"base_height":{"label":"Base Height","description":"Height of the bottom flange section","unit":"mm","feature":"base_flange"},"neck_height":{"label":"Neck Height","description":"Height of the middle neck section","unit":"mm","feature":"neck"},"cap_height":{"label":"Cap Height","description":"Height of the top cap section","unit":"mm","feature":"top_cap"}},"features":{"overall_height":{"kind":"dimension","axis":"z","label":"Total Height"},"base_flange":{"kind":"region","label":"Base Flange","min":[0,0,0],"max":[{"parameter":"base_radius","scale":1,"offset":0},{"parameter":"base_radius","scale":1,"offset":0},{"parameter":"base_height","scale":1,"offset":0}]},"neck":{"kind":"region","label":"Neck","min":[0,0,{"parameter":"base_height","scale":1,"offset":0}],"max":[{"parameter":"neck_radius","scale":1,"offset":0},{"parameter":"neck_radius","scale":1,"offset":0},{"parameter":"base_height","scale":1,"offset":{"parameter":"neck_height","scale":1,"offset":0}}]},"top_cap":{"kind":"region","label":"Top Cap","min":[0,0,{"parameter":"base_height","scale":1,"offset":{"parameter":"neck_height","scale":1,"offset":0}}],"max":[{"parameter":"cap_radius","scale":1,"offset":0},{"parameter":"cap_radius","scale":1,"offset":0},{"parameter":"total_height","scale":1,"offset":0}]}}} */

// Parameters
total_height = 38.64;
base_radius = 28.0;
neck_radius = 10.0;
cap_radius = 28.0;
base_height = 10.0;
neck_height = 10.0;
cap_height = 18.64;

// Derived checks (not editable)
// total_height should equal base_height + neck_height + cap_height

module knob_body() {
    // Base Flange
    translate([0, 0, 0])
        cylinder(h = base_height, r = base_radius, center = false);
    
    // Neck
    translate([0, 0, base_height])
        cylinder(h = neck_height, r = neck_radius, center = false);
    
    // Top Cap
    translate([0, 0, base_height + neck_height])
        cylinder(h = cap_height, r = cap_radius, center = false);
}

// Main instantiation
knob_body();
