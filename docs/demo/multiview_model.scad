// L-shaped bookend
// Derived sizes: width=73.11 (X), depth=47.78 (Y), height=100.0 (Z)
// Right view (view_1) defines the L-profile in YZ plane, extruded along X.
// Front view (view_2) defines four rectangular through-cutouts on the vertical face, cut along Y.

// --- Parameters ---
width = 73.11;      // X
depth = 47.78;      // Y
height = 100.0;     // Z

// L-profile parameters derived from right view polygon
// Right view: u maps to +Y, v maps to -Z
// Polygon points (u,v) -> (Y, Z):
// (0.0462, 0.0157) -> Y=2.21, Z=98.43
// (0.0462, 0.9822) -> Y=2.21, Z=1.78
// (0.9394, 0.9866) -> Y=44.88, Z=1.34
// (0.9441, 0.8594) -> Y=45.11, Z=14.06
// (0.3024, 0.855)  -> Y=14.45, Z=14.50
// (0.3116, 0.0157) -> Y=14.89, Z=98.43

// Simplified L-profile:
// Vertical backplate: Y from 0 to backplate_depth, Z from 0 to height
// Horizontal base: Y from 0 to depth, Z from 0 to base_height
// The inner corner is at (Y=inner_y, Z=inner_z)

backplate_depth = 14.5;  // Y extent of vertical part
base_height = 14.5;      // Z extent of horizontal part

// Cutout parameters from front view (view_2)
// Front view: u maps to +X, v maps to -Z
// Outer profile spans u: 0.0302-0.9665, v: 0.0133-0.9823
// Map to physical: X = u * width, Z = (1-v) * height

// Cutout 1 (contour_8): upper-left window
// center_view_normalized: (0.2689, 0.1968), size: (0.3069, 0.146)
c1_cx = 0.2689 * width;
c1_cz = (1.0 - 0.1968) * height;
c1_w = 0.3069 * width;
c1_h = 0.146 * height;

// Cutout 2 (contour_10): upper-right vertical slot
// center_view_normalized: (0.5577, 0.1968), size: (0.1245, 0.3661)
c2_cx = 0.5577 * width;
c2_cz = (1.0 - 0.1968) * height;
c2_w = 0.1245 * width;
c2_h = 0.3661 * height;

// Cutout 3 (contour_6): lower-right vertical slot
// center_view_normalized: (0.7734, 0.7024), size: (0.1245, 0.4447)
c3_cx = 0.7734 * width;
c3_cz = (1.0 - 0.7024) * height;
c3_w = 0.1245 * width;
c3_h = 0.4447 * height;

// Cutout 4 (contour_4): lower-left vertical slot
// center_view_normalized: (0.1822, 0.7024), size: (0.1245, 0.3661)
c4_cx = 0.1822 * width;
c4_cz = (1.0 - 0.7024) * height;
c4_w = 0.1245 * width;
c4_h = 0.3661 * height;

eps = 0.01;

// --- Modules ---

module l_profile() {
    // L-shape in YZ plane, extruded along X
    // Vertical backplate: Y [0, backplate_depth], Z [0, height]
    // Horizontal base: Y [0, depth], Z [0, base_height]
    // Union of two boxes
    translate([0, 0, 0])
        cube([width, backplate_depth, height]);
    translate([0, 0, 0])
        cube([width, depth, base_height]);
}

module cutout_cutter(cx, cz, w, h) {
    // Rectangular through-cutout on vertical face (front face at Y=0)
    // Cut along Y axis. The cutter spans Y from -eps to backplate_depth+eps
    // Centered at (cx, cz) in XZ plane
    translate([cx - w/2, -eps, cz - h/2])
        cube([w, backplate_depth + 2*eps, h]);
}

// --- Main Design ---

difference() {
    l_profile();
    
    // Cutout 1: upper-left window
    cutout_cutter(c1_cx, c1_cz, c1_w, c1_h);
    
    // Cutout 2: upper-right vertical slot
    cutout_cutter(c2_cx, c2_cz, c2_w, c2_h);
    
    // Cutout 3: lower-right vertical slot
    cutout_cutter(c3_cx, c3_cz, c3_w, c3_h);
    
    // Cutout 4: lower-left vertical slot
    cutout_cutter(c4_cx, c4_cz, c4_w, c4_h);
}
