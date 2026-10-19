/* doodle-meta {"version":1,"parameters":{"width":{"label":"Overall width","description":"Changes the body width","unit":"mm","feature":"body_width"},"depth":{"label":"Overall depth","description":"Changes the body depth","unit":"mm","feature":"body_depth"},"height":{"label":"Overall height","description":"Changes the body height","unit":"mm","feature":"body_height"},"panel_thickness":{"label":"Panel thickness","description":"Thickness of the upright panel","unit":"mm","feature":"panel_thickness"},"base_thickness":{"label":"Base thickness","description":"Thickness of the horizontal base","unit":"mm","feature":"base_thickness"}},"features":{"body_width":{"kind":"dimension","axis":"x","label":"Overall width"},"body_depth":{"kind":"dimension","axis":"y","label":"Overall depth"},"body_height":{"kind":"dimension","axis":"z","label":"Overall height"},"panel_thickness":{"kind":"dimension","axis":"y","label":"Panel thickness"},"base_thickness":{"kind":"dimension","axis":"z","label":"Base thickness"}}} */

// Top-level parameters (user-editable)
width = 80.18;
depth = 71.67;
height = 100.0;
panel_thickness = 10.0;
base_thickness = 10.0;

// Derived constants (not user-editable)
eps = 0.1;

// Cutout definitions in view-normalized coordinates (u, v) and sizes (su, sv)
// u maps to +X, v maps to -Z (v=0 is top, v=1 is bottom)
// X = u * width
// Z = (1 - v) * height

// Cutout 1: Slot in upper-left (contour_8)
c1_u = 0.2724; c1_v = 0.1968; c1_su = 0.2988; c1_sv = 0.1968;
// Cutout 2: Rectangle in center (contour_6)
c2_u = 0.5362; c2_v = 0.4268; c2_su = 0.1173; c2_sv = 0.3135;
// Cutout 3: Rectangle in lower-left (contour_4)
c3_u = 0.3269; c3_v = 0.6087; c3_su = 0.1732; c3_sv = 0.4027;
// Cutout 4: Polygon/Rectangle in lower-right (contour_2)
c4_u = 0.7472; c4_v = 0.6087; c4_su = 0.1369; c4_sv = 0.3891;

// Helper module for rectangular cutouts
module rect_cutout(cx, cz, w, h) {
    // cx, cz are center coordinates in XZ plane
    // w, h are width (X) and height (Z)
    // Cut along Y axis (through the panel)
    // Panel Y range: [depth - panel_thickness, depth]
    // Cutter Y range: [depth - panel_thickness - eps, depth + eps]
    translate([cx, depth - panel_thickness - eps, cz])
        cube([w, panel_thickness + 2*eps, h], center=true);
}

// Helper module for slot cutouts (stadium shape)
module slot_cutout(cx, cz, w, h) {
    // Stadium shape: rectangle with semicircular ends
    // w is total width, h is total height (diameter of ends)
    // Cut along Y axis
    r = h / 2;
    straight_len = w - h;
    
    translate([cx, depth - panel_thickness - eps, cz])
        rotate([90, 0, 0])
            union() {
                // Central rectangle
                cube([straight_len, panel_thickness + 2*eps, h], center=true);
                // Left cap
                translate([-straight_len/2, 0, 0])
                    cylinder(h=panel_thickness + 2*eps, r=r, center=true);
                // Right cap
                translate([straight_len/2, 0, 0])
                    cylinder(h=panel_thickness + 2*eps, r=r, center=true);
            }
}

// Main design
difference() {
    // Positive Body: L-shape
    union() {
        // Base: Extends from Y=0 to Y=depth, Z=0 to Z=base_thickness, X=0 to X=width
        cube([width, depth, base_thickness]);
        
        // Upright Panel: Extends from Y=depth-panel_thickness to Y=depth, Z=0 to Z=height, X=0 to X=width
        // Note: The panel sits on the back edge of the base.
        // Base is Y: 0..depth. Panel is Y: depth-panel_thickness..depth.
        // They overlap in Z: 0..base_thickness.
        translate([0, depth - panel_thickness, 0])
            cube([width, panel_thickness, height]);
    }
    
    // Subtractive Cutouts
    // Convert view coords to CAD coords
    // X = u * width
    // Z = (1 - v) * height
    
    // Cutout 1: Slot
    c1_x = c1_u * width;
    c1_z = (1 - c1_v) * height;
    c1_w = c1_su * width;
    c1_h = c1_sv * height;
    slot_cutout(c1_x, c1_z, c1_w, c1_h);
    
    // Cutout 2: Rectangle
    c2_x = c2_u * width;
    c2_z = (1 - c2_v) * height;
    c2_w = c2_su * width;
    c2_h = c2_sv * height;
    rect_cutout(c2_x, c2_z, c2_w, c2_h);
    
    // Cutout 3: Rectangle
    c3_x = c3_u * width;
    c3_z = (1 - c3_v) * height;
    c3_w = c3_su * width;
    c3_h = c3_sv * height;
    rect_cutout(c3_x, c3_z, c3_w, c3_h);
    
    // Cutout 4: Rectangle (treating low-confidence polygon as rectangle per intent)
    c4_x = c4_u * width;
    c4_z = (1 - c4_v) * height;
    c4_w = c4_su * width;
    c4_h = c4_sv * height;
    rect_cutout(c4_x, c4_z, c4_w, c4_h);
}
