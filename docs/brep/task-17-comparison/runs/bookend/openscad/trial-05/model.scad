/* doodle-meta {"version":1,"parameters":{"width":{"label":"Overall width","description":"Changes the body width","unit":"mm","feature":"body_width"},"depth":{"label":"Overall depth","description":"Changes the base depth","unit":"mm","feature":"body_depth"},"height":{"label":"Overall height","description":"Changes the total height","unit":"mm","feature":"body_height"},"panel_thickness":{"label":"Panel thickness","description":"Thickness of the vertical upright","unit":"mm","feature":"panel_thickness"},"base_thickness":{"label":"Base thickness","description":"Thickness of the horizontal base","unit":"mm","feature":"base_thickness"}},"features":{"body_width":{"kind":"dimension","axis":"x","label":"Overall width"},"body_depth":{"kind":"dimension","axis":"y","label":"Overall depth"},"body_height":{"kind":"dimension","axis":"z","label":"Overall height"},"panel_thickness":{"kind":"dimension","axis":"y","label":"Panel thickness"},"base_thickness":{"kind":"dimension","axis":"z","label":"Base thickness"}}} */

// Parameters
width = 80.18;
depth = 71.67;
height = 100.0;
panel_thickness = 8.0;
base_thickness = 8.0;

// Derived dimensions
base_depth = depth - panel_thickness;
panel_height = height - base_thickness;

// Cutout parameters (derived from view_1 normalized coordinates)
// View 1: u -> X, v -> -Z (v=0 is top, v=1 is bottom)
// X = u * width, Z = (1-v) * height

// Cutout 1 (Upper-Left): center (0.2724, 0.1968), size (0.2988, 0.1968)
c1_cx = 0.2724 * width;
c1_cz = (1.0 - 0.1968) * height;
c1_w = 0.2988 * width;
c1_h = 0.1968 * height;

// Cutout 2 (Center): center (0.5362, 0.4268), size (0.1173, 0.3135)
c2_cx = 0.5362 * width;
c2_cz = (1.0 - 0.4268) * height;
c2_w = 0.1173 * width;
c2_h = 0.3135 * height;

// Cutout 3 (Lower-Left): center (0.3269, 0.6087), size (0.1732, 0.4027)
c3_cx = 0.3269 * width;
c3_cz = (1.0 - 0.6087) * height;
c3_w = 0.1732 * width;
c3_h = 0.4027 * height;

// Cutout 4 (Lower-Right): center (0.7472, 0.6087), size (0.1369, 0.3891)
c4_cx = 0.7472 * width;
c4_cz = (1.0 - 0.6087) * height;
c4_w = 0.1369 * width;
c4_h = 0.3891 * height;

// Epsilon for boolean operations
eps = 0.01;

// Main design
difference() {
    // Positive Body: L-shape
    union() {
        // Base: extends from Y=0 to Y=depth, Z=0 to Z=base_thickness
        cube([width, depth, base_thickness]);
        
        // Panel: extends from Y=0 to Y=panel_thickness, Z=base_thickness to Z=height
        // Positioned at the back (Y=0) to match right view where tall mass is at u=0 (front/Y=0)
        // Wait, right view u=0 is FRONT (Y=0). The tall mass is at u=0.
        // So the panel is at Y=0. The base extends from Y=0 to Y=depth.
        // This forms an L with the vertical leg at Y=0.
        translate([0, 0, base_thickness])
            cube([width, panel_thickness, panel_height]);
    }
    
    // Subtractive Cutters (Through the panel wall along Y)
    // The panel occupies Y in [0, panel_thickness].
    // Cutters must span Y from -eps to panel_thickness + eps.
    
    // Cutout 1: Slot (Rounded ends)
    // Center X: c1_cx, Center Z: c1_cz
    // Width (X): c1_w, Height (Z): c1_h
    // Slot orientation: Horizontal (long axis along X)
    translate([c1_cx, 0, c1_cz])
        rotate([90, 0, 0])
            hull() {
                translate([-c1_w/2 + c1_h/2, 0, 0])
                    cylinder(h=panel_thickness + 2*eps, r=c1_h/2, center=true);
                translate([c1_w/2 - c1_h/2, 0, 0])
                    cylinder(h=panel_thickness + 2*eps, r=c1_h/2, center=true);
            }
            
    // Cutout 2: Rectangle
    translate([c2_cx, 0, c2_cz])
        cube([c2_w, panel_thickness + 2*eps, c2_h], center=true);
        
    // Cutout 3: Rectangle
    translate([c3_cx, 0, c3_cz])
        cube([c3_w, panel_thickness + 2*eps, c3_h], center=true);
        
    // Cutout 4: Rectangle
    translate([c4_cx, 0, c4_cz])
        cube([c4_w, panel_thickness + 2*eps, c4_h], center=true);
}
