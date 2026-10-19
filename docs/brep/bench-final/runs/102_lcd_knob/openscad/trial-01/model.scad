/* doodle-meta {"version":1,"parameters":{"base_diameter":{"label":"Base Diameter","description":"Diameter of the knob's circular base","unit":"mm","feature":"base_diameter"},"top_diameter":{"label":"Top Diameter","description":"Diameter of the knob's top surface","unit":"mm","feature":"top_diameter"},"knob_height":{"label":"Knob Height","description":"Total height of the knob","unit":"mm","feature":"knob_height"},"tab_count":{"label":"Tab Count","description":"Number of radial grip tabs","unit":"count","feature":"tab_count"},"tab_width":{"label":"Tab Width","description":"Width of each radial tab","unit":"mm","feature":"tab_width"},"tab_extension":{"label":"Tab Extension","description":"How far tabs extend beyond the base radius","unit":"mm","feature":"tab_extension"}},"features":{"base_diameter":{"kind":"dimension","axis":"x","label":"Base Diameter"},"top_diameter":{"kind":"dimension","axis":"x","label":"Top Diameter"},"knob_height":{"kind":"dimension","axis":"z","label":"Knob Height"},"tab_count":{"kind":"region","label":"Radial Tabs","min":[0,0,0],"max":[{"parameter":"base_diameter","scale":0.5,"offset":0},{"parameter":"base_diameter","scale":0.5,"offset":0},{"parameter":"knob_height","scale":1,"offset":0}]},"tab_width":{"kind":"region","label":"Tab Width","min":[0,0,0],"max":[{"parameter":"tab_width","scale":1,"offset":0},{"parameter":"tab_width","scale":1,"offset":0},{"parameter":"knob_height","scale":1,"offset":0}]},"tab_extension":{"kind":"region","label":"Tab Extension","min":[0,0,0],"max":[{"parameter":"base_diameter","scale":0.5,"offset":0},{"parameter":"base_diameter","scale":0.5,"offset":0},{"parameter":"knob_height","scale":1,"offset":0}]}}} */

// Parameters
base_diameter = 44.46104323391844;
top_diameter = 31.12273026374291;
knob_height = 13.04487008483167;
tab_count = 3;
tab_width = 10.670650376140426;
tab_extension = 3.556883458713475;

// Derived values
base_radius = base_diameter / 2;
top_radius = top_diameter / 2;
tab_length = base_radius + tab_extension;

// Module for the main tapered body (frustum)
module knob_body() {
    linear_extrude(height = knob_height, scale = top_radius / base_radius) {
        circle(r = base_radius, $fn = 64);
    }
}

// Module for a single tab
module tab() {
    // Tab is a rectangular prism extending radially
    // Positioned so it starts inside the base and extends outwards
    // Width is tab_width, Length is tab_length, Height is knob_height
    // We create it centered on X axis, extending from -base_radius to tab_length
    // To ensure manifold union, we start slightly inside the base
    translate([-base_radius, -tab_width/2, 0]) {
        cube([tab_length + base_radius, tab_width, knob_height]);
    }
}

// Module for all tabs
module tabs() {
    for (i = [0 : tab_count - 1]) {
        rotate([0, 0, i * (360 / tab_count)]) {
            tab();
        }
    }
}

// Main assembly
union() {
    knob_body();
    tabs();
}
