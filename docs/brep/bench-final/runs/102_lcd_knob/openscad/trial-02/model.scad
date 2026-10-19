/* doodle-meta {"version":1,"parameters":{"overall_width":{"label":"Overall Width","description":"Maximum width of the knob including wings","unit":"mm","feature":"body_width"},"overall_depth":{"label":"Overall Depth","description":"Maximum depth of the knob including wings","unit":"mm","feature":"body_depth"},"overall_height":{"label":"Overall Height","description":"Total height of the knob","unit":"mm","feature":"body_height"},"base_diameter":{"label":"Base Diameter","description":"Diameter of the knob base before taper","unit":"mm","feature":"body_taper"},"top_diameter":{"label":"Top Diameter","description":"Diameter of the knob top face","unit":"mm","feature":"body_taper"},"wing_length":{"label":"Wing Length","description":"Length of the grip wings extending from the base","unit":"mm","feature":"grip_wings"},"wing_width":{"label":"Wing Width","description":"Width of the grip wings","unit":"mm","feature":"grip_wings"},"shaft_diameter":{"label":"Shaft Hole Diameter","description":"Diameter of the central mounting hole","unit":"mm","feature":"shaft_hole"}},"features":{"body_width":{"kind":"dimension","axis":"x","label":"Overall Width"},"body_depth":{"kind":"dimension","axis":"y","label":"Overall Depth"},"body_height":{"kind":"dimension","axis":"z","label":"Overall Height"},"body_taper":{"kind":"region","label":"Tapered Body","min":[0,0,0],"max":[{"parameter":"overall_width","scale":0.5,"offset":0},{"parameter":"overall_depth","scale":0.5,"offset":0},{"parameter":"overall_height","scale":1,"offset":0}]},"grip_wings":{"kind":"region","label":"Grip Wings","min":[{"parameter":"overall_width","scale":0.5,"offset":0},{"parameter":"overall_depth","scale":0.5,"offset":0},0],"max":[{"parameter":"overall_width","scale":1,"offset":0},{"parameter":"overall_depth","scale":1,"offset":0},{"parameter":"overall_height","scale":1,"offset":0}]},"shaft_hole":{"kind":"region","label":"Shaft Hole","min":[{"parameter":"shaft_diameter","scale":-0.5,"offset":0},{"parameter":"shaft_diameter","scale":-0.5,"offset":0},0],"max":[{"parameter":"shaft_diameter","scale":0.5,"offset":0},{"parameter":"shaft_diameter","scale":0.5,"offset":0},{"parameter":"overall_height","scale":1,"offset":0}]}}} */

// Parameters
overall_width = 53.04476978569913;
overall_depth = 53.04476978569913;
overall_height = 15.563335455124125;
base_diameter = 31.826861871419478;
top_diameter = 49.07702100572883;
wing_length = 10.608953957139827;
wing_width = 12.73074474856779;
shaft_diameter = 9.945894334818586;

// Derived values
base_radius = base_diameter / 2;
top_radius = top_diameter / 2;
wing_extent = base_radius + wing_length;

// Modules
module knob_body() {
    // Lofted tapered body (wider at top, narrower at base)
    hull() {
        // Bottom circle
        translate([0, 0, 0])
            cylinder(h=0.01, r=base_radius, center=true);
        
        // Top circle
        translate([0, 0, overall_height])
            cylinder(h=0.01, r=top_radius, center=true);
    }
}

module grip_wing() {
    // Single wing extending radially
    // Positioned to start from the base radius and extend outwards
    // Using a tapered shape for better grip appearance
    translate([base_radius - 2, 0, overall_height/2])
        hull() {
            // Inner part (wider)
            translate([0, 0, 0])
                cube([2, wing_width, overall_height], center=true);
            // Outer part (narrower tip)
            translate([wing_length, 0, 0])
                cube([2, wing_width * 0.6, overall_height], center=true);
        }
}

module grip_wings() {
    // Three wings at 120 degree intervals
    for (i = [0:2]) {
        rotate([0, 0, i * 120])
            grip_wing();
    }
}

module shaft_hole() {
    // Central through-hole for shaft
    cylinder(h=overall_height + 2, d=shaft_diameter, center=true);
}

// Main Design
difference() {
    union() {
        knob_body();
        grip_wings();
    }
    // Subtract shaft hole
    translate([0, 0, overall_height/2])
        shaft_hole();
}
