/* doodle-meta {"version":1,"parameters":{"width":{"label":"Overall width","description":"Changes the body width along X","unit":"mm","feature":"body_width"},"depth":{"label":"Overall depth","description":"Changes the body depth along Y","unit":"mm","feature":"body_depth"},"height":{"label":"Overall height","description":"Changes the body height along Z","unit":"mm","feature":"body_height"},"chamfer_size":{"label":"Chamfer size","description":"Size of the 45-degree chamfer on all edges","unit":"mm","feature":"chamfer"}},"features":{"body_width":{"kind":"dimension","axis":"x","label":"Overall width"},"body_depth":{"kind":"dimension","axis":"y","label":"Overall depth"},"body_height":{"kind":"dimension","axis":"z","label":"Overall height"},"chamfer":{"kind":"region","label":"Edge Chamfers","min":[0,0,0],"max":[{"parameter":"width","scale":1,"offset":0},{"parameter":"depth","scale":1,"offset":0},{"parameter":"height","scale":1,"offset":0}]}}} */

// Parameters
width = 60.0;
depth = 40.0;
height = 20.0;
chamfer_size = 2.0;

// Derived constants
eps = 0.01;

// Module for a single chamfer cutter (a triangular prism)
// The prism is oriented such that its triangular cross-section is in the XY plane
// and it extends along Z.
// It cuts the corner at (x_sign * width/2, y_sign * depth/2).
module chamfer_cutter(x_sign, y_sign) {
    // Define the triangle vertices in the local XY plane relative to the corner
    // The corner is at (x_sign * width/2, y_sign * depth/2)
    // The cut removes material inside the triangle defined by:
    // (cx, cy), (cx - x_sign*chamfer_size, cy), (cx, cy - y_sign*chamfer_size)
    
    cx = x_sign * width / 2;
    cy = y_sign * depth / 2;
    
    // Points of the triangle
    p1 = [cx, cy];
    p2 = [cx - x_sign * chamfer_size, cy];
    p3 = [cx, cy - y_sign * chamfer_size];
    
    // Create the polygon and extrude it along Z
    // We need to extend the cutter beyond the block in Z to ensure clean cuts
    translate([0, 0, -eps])
    linear_extrude(height = height + 2*eps)
    polygon([p1, p2, p3]);
}

// Module for a chamfer cutter on a horizontal edge (parallel to X or Y)
// This creates a triangular prism oriented to cut a top or bottom edge.
// axis: 0 for X-axis edge, 1 for Y-axis edge
// sign: +1 or -1 indicating which side of the block the edge is on
module edge_chamfer(axis, sign) {
    // The chamfer is a triangular prism.
    // For an edge parallel to X (axis=0), the triangle is in the YZ plane.
    // For an edge parallel to Y (axis=1), the triangle is in the XZ plane.
    
    if (axis == 0) {
        // Edge parallel to X. Triangle in YZ plane.
        // Edge is at y = sign * depth/2, z = sign * height/2 (top/bottom)
        // Wait, sign determines top/bottom (Z) and front/back (Y).
        // Let's define the triangle vertices in YZ.
        // Corner is at (y=sign_y*depth/2, z=sign_z*height/2).
        // But here 'sign' is passed as +1 for top/front, -1 for bottom/back?
        // Let's simplify: we need to cut 4 top edges and 4 bottom edges.
        
        // Let's use a generic approach: create a cube and rotate it.
        // A 45 deg chamfer can be made by cutting a corner of a cube.
        
        // Let's stick to the previous logic but generalized.
        // We need to cut the corner defined by two faces.
        
        // For Top-Front edge (Y+, Z+):
        // Triangle in YZ plane at Y=depth/2, Z=height/2.
        // Vertices: (depth/2, height/2), (depth/2 - cs, height/2), (depth/2, height/2 - cs)
        
        // Let's implement specific cutters for the 8 horizontal edges.
    }
}

// Helper to cut a corner defined by two axes and signs
// axis1, axis2: 0=X, 1=Y, 2=Z
// s1, s2: +1 or -1
module corner_chamfer_3d(axis1, axis2, s1, s2) {
    // Determine the plane of the triangle and the extrusion axis
    // The extrusion axis is the one NOT in {axis1, axis2}
    ext_axis = 3 - axis1 - axis2; // 0+1+2=3
    
    // Define the triangle in the local 2D plane of axis1, axis2
    // The corner is at (s1 * dim1/2, s2 * dim2/2)
    // The triangle vertices are:
    // (c1, c2)
    // (c1 - s1*cs, c2)
    // (c1, c2 - s2*cs)
    
    dim1 = (axis1 == 0) ? width : (axis1 == 1) ? depth : height;
    dim2 = (axis2 == 0) ? width : (axis2 == 1) ? depth : height;
    ext_dim = (ext_axis == 0) ? width : (ext_axis == 1) ? depth : height;
    
    c1 = s1 * dim1 / 2;
    c2 = s2 * dim2 / 2;
    
    p1 = [c1, c2];
    p2 = [c1 - s1 * chamfer_size, c2];
    p3 = [c1, c2 - s2 * chamfer_size];
    
    // Create polygon in XY plane (local)
    // Then rotate to align with axis1, axis2
    // Then translate to center
    // Then extrude along ext_axis
    
    // Rotation logic:
    // If ext_axis is Z (2), no rotation needed (polygon is in XY).
    // If ext_axis is Y (1), rotate X by 90. Polygon in XZ -> Y extrusion? 
    //   Standard linear_extrude is along Z.
    //   If we want extrusion along Y, we rotate the object so Z becomes Y.
    //   rotate([90, 0, 0]) maps Z to -Y? No, Z to Y?
    //   Let's just use rotate_extrude or careful rotations.
    
    // Simpler: Create the prism in a standard orientation and rotate/translate.
    // Standard: Triangle in XY, extruded along Z.
    // We want: Triangle in Plane(axis1, axis2), extruded along ext_axis.
    
    // Let's map (axis1, axis2) to (X, Y) and ext_axis to Z.
    
    // Case 1: ext_axis = Z (2). axis1, axis2 are X, Y.
    //   No rotation.
    // Case 2: ext_axis = Y (1). axis1, axis2 are X, Z.
    //   We want triangle in XZ, extruded along Y.
    //   Create triangle in XY (local), extrude along Z (local).
    //   Rotate so local Z -> global Y. rotate([90, 0, 0])? 
    //   rotate([90,0,0]) maps Y->Z, Z->-Y. So extrusion along -Y.
    //   We need to handle signs carefully.
    
    // Let's use a different approach: Minkowski difference or just explicit cutters.
    // Given the complexity of generic rotation, let's write explicit cutters for the 12 edges.
    
    // 4 Vertical Edges (parallel to Z): Triangle in XY, extrude Z.
    // 4 Top Edges (parallel to X/Y): Triangle in YZ/XZ, extrude X/Y.
    // 4 Bottom Edges (parallel to X/Y): Triangle in YZ/XZ, extrude X/Y.
}

// Explicit Cutters

// 1. Vertical Edges (4)
// Already implemented in chamfer_cutter
module vertical_chamfers() {
    chamfer_cutter(1, 1);
    chamfer_cutter(-1, 1);
    chamfer_cutter(1, -1);
    chamfer_cutter(-1, -1);
}

// 2. Top Edges (4)
// Top-Front (Y+, Z+) -> Edge parallel to X. Triangle in YZ.
module top_front_chamfer() {
    // Triangle in YZ plane.
    // Corner at Y=depth/2, Z=height/2.
    // Vertices: (depth/2, height/2), (depth/2 - cs, height/2), (depth/2, height/2 - cs)
    // Extrude along X.
    // Create polygon in XY (local), rotate to YZ, extrude along Z (local) -> X (global).
    
    // Polygon in local XY:
    // p1 = [depth/2, height/2]
    // p2 = [depth/2 - cs, height/2]
    // p3 = [depth/2, height/2 - cs]
    
    // Rotate [90, 0, 0] maps local Y to global Z, local Z to global -Y?
    // Let's use rotate([0, 90, 0])?
    // rotate([0, 90, 0]) maps local X to global Z, local Z to global -X.
    
    // Let's just use linear_extrude and rotate.
    // We want the prism axis along X.
    // So we create the triangle in YZ, and extrude along X.
    // linear_extrude extrudes along Z.
    // So we create triangle in XY, extrude along Z, then rotate so Z->X.
    // rotate([0, 90, 0]) maps Z to -X.
    // So we need to mirror or adjust.
    
    // Let's define the triangle in the plane perpendicular to X.
    // The plane is YZ.
    // We can use `rotate([0, 90, 0])` to make the extrusion direction X.
    // But the triangle coordinates need to be in the plane perpendicular to the extrusion axis.
    
    // Let's try:
    // translate([0, 0, 0])
    // rotate([0, 90, 0])
    // linear_extrude(height=width+2*eps)
    // polygon(...)
    
    // If we rotate([0, 90, 0]), the local Z becomes global -X.
    // The local XY plane becomes global ZY plane?
    // Local X -> Global Z. Local Y -> Global Y.
    // So the polygon is in Global ZY.
    // We want the triangle in YZ.
    // So we define points in (Y, Z) coordinates?
    // If local X maps to Global Z, and local Y maps to Global Y.
    // Then point (x, y) in polygon becomes (y, x) in (Y, Z)?
    // Let's verify.
    // rotate([0, 90, 0]) * [x, y, z] = [z, y, -x].
    // So local (x, y, 0) -> global (0, y, -x).
    // So local X is Global -Z. Local Y is Global Y.
    // So polygon in local XY maps to Global YZ (with Z flipped).
    
    // We want triangle at Y=depth/2, Z=height/2.
    // Vertices in Global YZ:
    // (depth/2, height/2)
    // (depth/2 - cs, height/2)
    // (depth/2, height/2 - cs)
    
    // Map to Local XY:
    // Global Y = Local Y.
    // Global Z = -Local X.
    // So Local X = -Global Z.
    
    // p1: Y=depth/2, Z=height/2 -> Local ( -height/2, depth/2 )
    // p2: Y=depth/2-cs, Z=height/2 -> Local ( -height/2, depth/2-cs )
    // p3: Y=depth/2, Z=height/2-cs -> Local ( -(height/2-cs), depth/2 )
    
    // Extrude along Local Z (which is Global -X).
    // We need to cover the whole width.
    // Translate to center X.
    
    translate([width/2 + eps, 0, 0]) // Start from +X side?
    // If extrusion is along -X, we start at +X and go to -X.
    // So translate to +X end.
    
    rotate([0, 90, 0])
    translate([0, 0, -eps]) // Extend in local Z (global -X)
    linear_extrude(height = width + 2*eps)
    polygon([
        [-height/2, depth/2],
        [-height/2, depth/2 - chamfer_size],
        [-(height/2 - chamfer_size), depth/2]
    ]);
}

// Top-Back (Y-, Z+) -> Edge parallel to X.
module top_back_chamfer() {
    // Corner at Y=-depth/2, Z=height/2.
    // Vertices in Global YZ:
    // (-depth/2, height/2)
    // (-depth/2 + cs, height/2)
    // (-depth/2, height/2 - cs)
    
    // Map to Local XY (Local X = -Global Z, Local Y = Global Y)
    // p1: (-height/2, -depth/2)
    // p2: (-height/2, -depth/2 + cs)
    // p3: (-(height/2 - cs), -depth/2)
    
    translate([width/2 + eps, 0, 0])
    rotate([0, 90, 0])
    translate([0, 0, -eps])
    linear_extrude(height = width + 2*eps)
    polygon([
        [-height/2, -depth/2],
        [-height/2, -depth/2 + chamfer_size],
        [-(height/2 - chamfer_size), -depth/2]
    ]);
}

// Top-Right (X+, Z+) -> Edge parallel to Y.
module top_right_chamfer() {
    // Corner at X=width/2, Z=height/2.
    // Vertices in Global XZ:
    // (width/2, height/2)
    // (width/2 - cs, height/2)
    // (width/2, height/2 - cs)
    
    // Extrude along Y.
    // Rotate so Z->Y. rotate([90, 0, 0]) maps Z->-Y?
    // rotate([90, 0, 0]) * [x, y, z] = [x, -z, y].
    // Local Z -> Global Y.
    // Local X -> Global X. Local Y -> Global -Z.
    // So polygon in Local XY maps to Global X(-Z).
    // We want triangle in XZ.
    // Global X = Local X. Global Z = -Local Y.
    
    // p1: (width/2, height/2) -> Local (width/2, -height/2)
    // p2: (width/2 - cs, height/2) -> Local (width/2 - cs, -height/2)
    // p3: (width/2, height/2 - cs) -> Local (width/2, -(height/2 - cs))
    
    // Extrude along Local Z (Global Y).
    // Translate to +Y end.
    
    translate([0, depth/2 + eps, 0])
    rotate([90, 0, 0])
    translate([0, 0, -eps])
    linear_extrude(height = depth + 2*eps)
    polygon([
        [width/2, -height/2],
        [width/2 - chamfer_size, -height/2],
        [width/2, -(height/2 - chamfer_size)]
    ]);
}

// Top-Left (X-, Z+) -> Edge parallel to Y.
module top_left_chamfer() {
    // Corner at X=-width/2, Z=height/2.
    // Vertices in Global XZ:
    // (-width/2, height/2)
    // (-width/2 + cs, height/2)
    // (-width/2, height/2 - cs)
    
    // Map to Local XY (Local X = Global X, Local Y = -Global Z)
    // p1: (-width/2, -height/2)
    // p2: (-width/2 + cs, -height/2)
    // p3: (-width/2, -(height/2 - cs))
    
    translate([0, depth/2 + eps, 0])
    rotate([90, 0, 0])
    translate([0, 0, -eps])
    linear_extrude(height = depth + 2*eps)
    polygon([
        [-width/2, -height/2],
        [-width/2 + chamfer_size, -height/2],
        [-width/2, -(height/2 - chamfer_size)]
    ]);
}

// Bottom Edges (4)
// Bottom-Front (Y+, Z-)
module bottom_front_chamfer() {
    // Corner at Y=depth/2, Z=-height/2.
    // Vertices in Global YZ:
    // (depth/2, -height/2)
    // (depth/2 - cs, -height/2)
    // (depth/2, -height/2 + cs)
    
    // Map to Local XY (Local X = -Global Z, Local Y = Global Y)
    // p1: (height/2, depth/2)
    // p2: (height/2, depth/2 - cs)
    // p3: (height/2 - cs, depth/2)
    
    translate([width/2 + eps, 0, 0])
    rotate([0, 90, 0])
    translate([0, 0, -eps])
    linear_extrude(height = width + 2*eps)
    polygon([
        [height/2, depth/2],
        [height/2, depth/2 - chamfer_size],
        [height/2 - chamfer_size, depth/2]
    ]);
}

// Bottom-Back (Y-, Z-)
module bottom_back_chamfer() {
    // Corner at Y=-depth/2, Z=-height/2.
    // Vertices in Global YZ:
    // (-depth/2, -height/2)
    // (-depth/2 + cs, -height/2)
    // (-depth/2, -height/2 + cs)
    
    // Map to Local XY
    // p1: (height/2, -depth/2)
    // p2: (height/2, -depth/2 + cs)
    // p3: (height/2 - cs, -depth/2)
    
    translate([width/2 + eps, 0, 0])
    rotate([0, 90, 0])
    translate([0, 0, -eps])
    linear_extrude(height = width + 2*eps)
    polygon([
        [height/2, -depth/2],
        [height/2, -depth/2 + chamfer_size],
        [height/2 - chamfer_size, -depth/2]
    ]);
}

// Bottom-Right (X+, Z-)
module bottom_right_chamfer() {
    // Corner at X=width/2, Z=-height/2.
    // Vertices in Global XZ:
    // (width/2, -height/2)
    // (width/2 - cs, -height/2)
    // (width/2, -height/2 + cs)
    
    // Map to Local XY (Local X = Global X, Local Y = -Global Z)
    // p1: (width/2, height/2)
    // p2: (width/2 - cs, height/2)
    // p3: (width/2, height/2 - cs)
    
    translate([0, depth/2 + eps, 0])
    rotate([90, 0, 0])
    translate([0, 0, -eps])
    linear_extrude(height = depth + 2*eps)
    polygon([
        [width/2, height/2],
        [width/2 - chamfer_size, height/2],
        [width/2, height/2 - chamfer_size]
    ]);
}

// Bottom-Left (X-, Z-)
module bottom_left_chamfer() {
    // Corner at X=-width/2, Z=-height/2.
    // Vertices in Global XZ:
    // (-width/2, -height/2)
    // (-width/2 + cs, -height/2)
    // (-width/2, -height/2 + cs)
    
    // Map to Local XY
    // p1: (-width/2, height/2)
    // p2: (-width/2 + cs, height/2)
    // p3: (-width/2, height/2 - cs)
    
    translate([0, depth/2 + eps, 0])
    rotate([90, 0, 0])
    translate([0, 0, -eps])
    linear_extrude(height = depth + 2*eps)
    polygon([
        [-width/2, height/2],
        [-width/2 + chamfer_size, height/2],
        [-width/2, height/2 - chamfer_size]
    ]);
}

// Main design
difference() {
    // Base block
    translate([0, 0, height/2])
    cube([width, depth, height], center=true);
    
    // Subtract all 12 chamfers
    vertical_chamfers();
    
    top_front_chamfer();
    top_back_chamfer();
    top_right_chamfer();
    top_left_chamfer();
    
    bottom_front_chamfer();
    bottom_back_chamfer();
    bottom_right_chamfer();
    bottom_left_chamfer();
}
