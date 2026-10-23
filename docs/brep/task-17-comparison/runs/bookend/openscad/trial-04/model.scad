/* doodle-meta {"version":1,"parameters":{"width":{"label":"Overall width","description":"Changes the width of the bookend along the X axis","unit":"mm","feature":"body_width"},"depth":{"label":"Overall depth","description":"Changes the depth of the bookend along the Y axis","unit":"mm","feature":"body_depth"},"height":{"label":"Overall height","description":"Changes the height of the bookend along the Z axis","unit":"mm","feature":"body_height"},"wall_thickness":{"label":"Wall thickness","description":"Changes the thickness of the L-profile walls","unit":"mm","feature":"wall_thickness"}},"features":{"body_width":{"kind":"dimension","axis":"x","label":"Overall width"},"body_depth":{"kind":"dimension","axis":"y","label":"Overall depth"},"body_height":{"kind":"dimension","axis":"z","label":"Overall height"},"wall_thickness":{"kind":"region","label":"Wall thickness","min":[0,0,0],"max":[{"parameter":"wall_thickness","scale":1,"offset":0},{"parameter":"depth","scale":1,"offset":0},{"parameter":"height","scale":1,"offset":0}]}}} */

// Overall dimensions from derived_sizes
width = 80.18;
depth = 71.67;
height = 100.0;

// Wall thickness inferred from right view stroke width (reduced to match thin stroke)
wall_thickness = 10.0;

// Cutout parameters derived from front view normalized coordinates
// Front view mapping: X = u * width, Z = (1 - v) * height
// Cutout 1 (Top Left - Slot): center (0.2724, 0.1968), size (0.2988, 0.1968)
c1_u = 0.2724; c1_v = 0.1968; c1_w = 0.2988; c1_h = 0.1968;
// Cutout 2 (Center): center (0.5362, 0.4268), size (0.1173, 0.3135)
c2_u = 0.5362; c2_v = 0.4268; c2_w = 0.1173; c2_h = 0.3135;
// Cutout 3 (Bottom Left): center (0.3269, 0.6087), size (0.1732, 0.4027)
c3_u = 0.3269; c3_v = 0.6087; c3_w = 0.1732; c3_h = 0.4027;
// Cutout 4 (Bottom Right): center (0.7472, 0.6087), size (0.1369, 0.3891)
c4_u = 0.7472; c4_v = 0.6087; c4_w = 0.1369; c4_h = 0.3891;

// Helper to convert normalized view coords to mm
function u_to_x(u) = u * width;
function v_to_z(v) = (1.0 - v) * height;

// Helper to convert normalized size to mm
function w_to_mm(w) = w * width;
function h_to_mm(h) = h * height;

module l_shape_body() {
    // Base: Horizontal plate at bottom
    // Extends from Y=0 to Y=depth, Z=0 to Z=wall_thickness, X=0 to X=width
    cube([width, depth, wall_thickness]);
    
    // Panel: Vertical plate at front (Y=0)
    // Extends from Y=0 to Y=wall_thickness, Z=0 to Z=height, X=0 to X=width
    // This matches the right view where the vertical leg is on the right (front)
    translate([0, 0, 0])
        cube([width, wall_thickness, height]);
}

module cutout_rect(x, z, w, h) {
    // Rectangular cutter: Box oriented along Y
    eps = 0.1;
    y_start = -eps;
    y_len = wall_thickness + 2*eps;
    
    translate([x - w/2, y_start, z - h/2])
        cube([w, y_len, h]);
}

module design() {
    difference() {
        l_shape_body();
        
        // Cutout 1: Top Left (Rectangle)
        cutout_rect(u_to_x(c1_u), v_to_z(c1_v), w_to_mm(c1_w), h_to_mm(c1_h));
        
        // Cutout 2: Center Rectangle
        cutout_rect(u_to_x(c2_u), v_to_z(c2_v), w_to_mm(c2_w), h_to_mm(c2_h));
        
        // Cutout 3: Bottom Left Rectangle
        cutout_rect(u_to_x(c3_u), v_to_z(c3_v), w_to_mm(c3_w), h_to_mm(c3_h));
        
        // Cutout 4: Bottom Right Rectangle
        cutout_rect(u_to_x(c4_u), v_to_z(c4_v), w_to_mm(c4_w), h_to_mm(c4_h));
    }
}

design();
