/* doodle-meta {"version":1,"parameters":{"width":{"label":"Overall width","description":"Changes the body width","unit":"mm","feature":"body_width"},"depth":{"label":"Overall depth","description":"Changes the base depth","unit":"mm","feature":"body_depth"},"height":{"label":"Overall height","description":"Changes the back height","unit":"mm","feature":"body_height"},"back_thickness":{"label":"Back thickness","description":"Thickness of the vertical back wall","unit":"mm","feature":"back_thickness"},"base_thickness":{"label":"Base thickness","description":"Thickness of the horizontal base","unit":"mm","feature":"base_thickness"}},"features":{"body_width":{"kind":"dimension","axis":"x","label":"Overall width"},"body_depth":{"kind":"dimension","axis":"y","label":"Overall depth"},"body_height":{"kind":"dimension","axis":"z","label":"Overall height"},"back_thickness":{"kind":"dimension","axis":"y","label":"Back thickness"},"base_thickness":{"kind":"dimension","axis":"z","label":"Base thickness"}}} */

// Top-level parameters (user-editable)
width = 80.18;
depth = 71.67;
height = 100.0;
back_thickness = 12.0;
base_thickness = 12.0;

// Derived sizes (not user-editable)
cutout_w1 = 24.0;
cutout_h1 = 19.7;
cutout_cx1 = 21.8;
cutout_cz1 = 80.3;

cutout_w2 = 9.4;
cutout_h2 = 31.4;
cutout_cx2 = 43.0;
cutout_cz2 = 57.3;

cutout_w3 = 13.9;
cutout_h3 = 40.3;
cutout_cx3 = 26.2;
cutout_cz3 = 39.1;

cutout_w4 = 11.0;
cutout_h4 = 38.9;
cutout_cx4 = 59.9;
cutout_cz4 = 39.1;

eps = 0.1;

// Main design
difference() {
    // Positive body: L-shape
    union() {
        // Vertical back wall (at Y=0 to Y=back_thickness)
        cube([width, back_thickness, height]);
        // Horizontal base (at Z=0 to Z=base_thickness, extending to Y=depth)
        cube([width, depth, base_thickness]);
    }
    
    // Subtractive cutters for through-holes in the back wall (cut along Y)
    // Cutout 1: Upper-left
    translate([cutout_cx1, depth/2, cutout_cz1])
        cube([cutout_w1, depth + 2*eps, cutout_h1], center=true);
            
    // Cutout 2: Center
    translate([cutout_cx2, depth/2, cutout_cz2])
        cube([cutout_w2, depth + 2*eps, cutout_h2], center=true);
            
    // Cutout 3: Lower-left
    translate([cutout_cx3, depth/2, cutout_cz3])
        cube([cutout_w3, depth + 2*eps, cutout_h3], center=true);
            
    // Cutout 4: Lower-right
    translate([cutout_cx4, depth/2, cutout_cz4])
        cube([cutout_w4, depth + 2*eps, cutout_h4], center=true);
}
