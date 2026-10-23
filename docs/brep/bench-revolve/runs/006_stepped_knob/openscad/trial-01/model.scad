/* doodle-meta {"version":1,"parameters":{"base_diameter":{"label":"Base Flange Diameter","description":"Diameter of the bottom flange","unit":"mm","feature":"base_flange"},"neck_diameter":{"label":"Neck Diameter","description":"Diameter of the central neck section","unit":"mm","feature":"neck"},"top_diameter":{"label":"Top Flange Diameter","description":"Diameter of the top flange","unit":"mm","feature":"top_flange"},"base_height":{"label":"Base Height","description":"Height of the bottom flange","unit":"mm","feature":"base_flange"},"neck_height":{"label":"Neck Height","description":"Height of the central neck","unit":"mm","feature":"neck"},"top_height":{"label":"Top Height","description":"Height of the top flange","unit":"mm","feature":"top_flange"}},"features":{"base_flange":{"kind":"region","label":"Base Flange","min":[0,0,0],"max":[{"parameter":"base_diameter","scale":0.5},{"parameter":"base_diameter","scale":0.5},{"parameter":"base_height"}]},"neck":{"kind":"region","label":"Neck","min":[0,0,{"parameter":"base_height"}],"max":[{"parameter":"neck_diameter","scale":0.5},{"parameter":"neck_diameter","scale":0.5},{"parameter":"base_height","offset":0},{"parameter":"neck_height","offset":0}]},"top_flange":{"kind":"region","label":"Top Flange","min":[0,0,{"parameter":"base_height","offset":0},{"parameter":"neck_height","offset":0}],"max":[{"parameter":"top_diameter","scale":0.5},{"parameter":"top_diameter","scale":0.5},{"parameter":"base_height","offset":0},{"parameter":"neck_height","offset":0},{"parameter":"top_height","offset":0}]}}} */

// Parameters
base_diameter = 56.0;
neck_diameter = 28.0;
top_diameter = 56.0;

base_height = 10.0;
neck_height = 18.64;
top_height = 10.0;

// Derived radii
base_r = base_diameter / 2;
neck_r = neck_diameter / 2;
top_r = top_diameter / 2;

// Total height
total_height = base_height + neck_height + top_height;

// Module for the stepped knob
module stepped_knob() {
    // Base Flange
    translate([0, 0, 0])
        cylinder(h = base_height, r = base_r, center = false);
    
    // Neck
    translate([0, 0, base_height])
        cylinder(h = neck_height, r = neck_r, center = false);
        
    // Top Flange
    translate([0, 0, base_height + neck_height])
        cylinder(h = top_height, r = top_r, center = false);
}

// Instantiate the design
stepped_knob();
