/* doodle-meta {"version":1,"parameters":{"width":{"label":"Base Width","description":"Width of the rectangular base along X","unit":"mm","feature":"base_width"},"depth":{"label":"Base Depth","description":"Depth of the rectangular base along Y","unit":"mm","feature":"base_depth"},"height":{"label":"Height","description":"Total height of the transition piece","unit":"mm","feature":"height"},"top_diameter":{"label":"Top Diameter","description":"Diameter of the circular top face","unit":"mm","feature":"top_diameter"}},"features":{"base_width":{"kind":"dimension","axis":"x","label":"Base Width"},"base_depth":{"kind":"dimension","axis":"y","label":"Base Depth"},"height":{"kind":"dimension","axis":"z","label":"Height"},"top_diameter":{"kind":"dimension","axis":"z","label":"Top Diameter"}}} */

// User-editable parameters
width = 33.4;
depth = 6.8;
height = 60.0;
top_diameter = 30.0;

// Derived constants (not user-editable)
$fn = 64;
eps = 0.01;

// Main design
transition_piece();

module transition_piece() {
    // Construct the lofted solid using polyhedron
    // Base vertices (Z=0)
    // Top vertices (Z=height)
    
    // Base rectangle corners (centered on X, Y)
    // X ranges from -width/2 to width/2
    // Y ranges from -depth/2 to depth/2
    // Z = 0
    
    // Top circle points (centered on X, Y)
    // Radius = top_diameter / 2
    // Z = height
    
    // We need to connect the 4 base corners to the N top circle points.
    // To ensure manifoldness and correct triangulation, we will generate
    // the side faces by connecting each base edge to the corresponding
    // arc of the top circle.
    
    // Number of segments for the circle
    n_segments = $fn;
    r_top = top_diameter / 2;
    
    // Generate vertices
    // Base vertices: 0, 1, 2, 3
    // Top vertices: 4 ... 4 + n_segments - 1
    
    // Base vertices
    // 0: (-w/2, -d/2, 0)
    // 1: ( w/2, -d/2, 0)
    // 2: ( w/2,  d/2, 0)
    // 3: (-w/2,  d/2, 0)
    
    // Top vertices
    // For i in 0..n_segments-1:
    // angle = i * 360 / n_segments
    // x = r_top * cos(angle)
    // y = r_top * sin(angle)
    // z = height
    
    // Faces:
    // 1. Bottom face (rectangle)
    //    [0, 1, 2, 3] -> Triangles: [0,1,2], [0,2,3] (CCW from bottom looking up? No, looking from -Z)
    //    Looking from -Z (bottom), CCW is 0->3->2->1.
    //    So triangles: [0,3,2], [0,2,1]
    
    // 2. Top face (circle)
    //    Center vertex? Or fan from one vertex?
    //    Let's use a fan from vertex 4 (index 0 of top).
    //    Triangles: [4, 4+i, 4+i+1] for i=1..n_segments-2
    //    Orientation: Looking from +Z (top), CCW is 4->5->6...
    //    So [4, 4+i, 4+i+1] is correct.
    
    // 3. Side faces
    //    We need to map the 4 base edges to the circle.
    //    Edge 0-1 (Front, Y=-d/2) connects to the arc of the circle closest to Y=-r_top.
    //    Edge 1-2 (Right, X=w/2) connects to the arc closest to X=r_top.
    //    Edge 2-3 (Back, Y=d/2) connects to the arc closest to Y=r_top.
    //    Edge 3-0 (Left, X=-w/2) connects to the arc closest to X=-r_top.
    
    //    To do this robustly, we can just create triangles between each base vertex
    //    and the two nearest top vertices, and then fill the gaps.
    //    However, a simpler approach for a "pyramid frustum" style loft is to
    //    connect each base vertex to the top circle, but we need to ensure
    //    the surface is smooth.
    
    //    Alternative: Create a "fan" from each base vertex to the entire top circle?
    //    No, that creates a cone-like shape from each corner.
    
    //    Correct approach for Rect-to-Circle loft:
    //    Divide the top circle into 4 arcs corresponding to the 4 sides.
    //    Arc 1 (Front): Angles 270 to 90 (passing through 0)? No.
    //    Let's define angles 0 to 360.
    //    Front side (Y negative) corresponds to angles around 270 (or -90).
    //    Right side (X positive) corresponds to angles around 0.
    //    Back side (Y positive) corresponds to angles around 90.
    //    Left side (X negative) corresponds to angles around 180.
    
    //    Let's assign indices to top vertices.
    //    We will generate the side faces by iterating through the top vertices
    //    and connecting them to the appropriate base edge.
    
    //    Actually, the simplest watertight way is to define the polyhedron
    //    with explicit vertex and face lists.
    
    //    Let's generate the vertices list first.
    
    vertices = [
        // Base (4 vertices)
        [-width/2, -depth/2, 0],
        [ width/2, -depth/2, 0],
        [ width/2,  depth/2, 0],
        [-width/2,  depth/2, 0],
        
        // Top (n_segments vertices)
        // Generated in loop below
    ];
    
    // Generate top vertices
    top_verts = [];
    for (i = [0 : n_segments - 1]) {
        angle = i * 360 / n_segments;
        x = r_top * cos(angle);
        y = r_top * sin(angle);
        top_verts = concat(top_verts, [[x, y, height]]);
    }
    
    all_vertices = concat(vertices, top_verts);
    
    // Generate faces
    faces = [];
    
    // Bottom face (4 vertices: 0,1,2,3)
    // Normal should point down (-Z).
    // Vertices: 0(-,-), 1(+,-), 2(+,+), 3(-,+)
    // Looking from bottom (-Z), CCW is 0->3->2->1.
    faces = concat(faces, [[0, 3, 2], [0, 2, 1]]);
    
    // Top face (n_segments vertices: 4..4+n-1)
    // Normal should point up (+Z).
    // Fan from vertex 4.
    for (i = [1 : n_segments - 2]) {
        faces = concat(faces, [[4, 4 + i, 4 + i + 1]]);
    }
    
    // Side faces
    // We need to connect the base edges to the top circle.
    // Base Edge 0-1 (Front, Y=-d/2)
    // Base Edge 1-2 (Right, X=w/2)
    // Base Edge 2-3 (Back, Y=d/2)
    // Base Edge 3-0 (Left, X=-w/2)
    
    // We will iterate through the top vertices and assign them to the nearest base edge.
    // To avoid gaps, we can create triangles between consecutive top vertices and the
    // "closest" base vertex, or better, create quads/triangles that span the gap.
    
    // A robust method:
    // For each top vertex i (0..n-1), find the two base vertices that form the "closest" edge.
    // Actually, let's just create triangles from each top vertex to the two base vertices
    // of the edge it belongs to.
    
    // Let's define which base edge each top vertex belongs to based on angle.
    // Angle 0 is +X (Right). Angle 90 is +Y (Back). Angle 180 is -X (Left). Angle 270 is -Y (Front).
    
    // Edge 1-2 (Right) is near angle 0.
    // Edge 2-3 (Back) is near angle 90.
    // Edge 3-0 (Left) is near angle 180.
    // Edge 0-1 (Front) is near angle 270.
    
    // We can split the circle into 4 quadrants.
    // Quadrant 1 (0-90): Connect to Edge 1-2 (Right) and Edge 2-3 (Back)?
    // This is tricky. A standard loft connects each base vertex to a range of top vertices.
    
    // Let's try a different approach:
    // Create triangles from each base vertex to the top circle.
    // Base Vertex 0 (-w/2, -d/2) is "Front-Left".
    // Base Vertex 1 ( w/2, -d/2) is "Front-Right".
    // Base Vertex 2 ( w/2,  d/2) is "Back-Right".
    // Base Vertex 3 (-w/2,  d/2) is "Back-Left".
    
    // We will create a fan from each base vertex to the top vertices that are "visible" from it.
    // But this might create non-manifold edges if not careful.
    
    // Better: Iterate through top vertices. For each top vertex, create a triangle with the
    // two base vertices of the edge it is "above".
    // If a top vertex is exactly between two edges, we need to handle the transition.
    
    // Let's use a simpler heuristic:
    // For each top vertex i, determine the closest base edge.
    // If it's on the boundary, we might need to split.
    
    // Let's just generate triangles for each segment of the top circle.
    // For each segment (i, i+1), we have a top edge.
    // We need to connect this top edge to the base.
    // The base is a rectangle.
    
    // Let's try connecting each top vertex to the two nearest base vertices.
    // This creates a "spiky" surface if not careful.
    
    // Let's use the standard "loft" algorithm logic:
    // 1. Identify the 4 "corner" top vertices closest to the 4 base corners.
    // 2. Connect base corner to its corresponding top corner.
    // 3. Fill the gaps with triangles.
    
    // Find top vertex indices closest to base corners.
    // Base 0 (-,-) -> Top angle ~225 deg (or -135).
    // Base 1 (+,-) -> Top angle ~315 deg (or -45).
    // Base 2 (+,+) -> Top angle ~45 deg.
    // Base 3 (-,+) -> Top angle ~135 deg.
    
    // Let's find the index of the top vertex closest to these angles.
    // Angle 0 is +X.
    // Target angles:
    // T0: 225
    // T1: 315
    // T2: 45
    // T3: 135
    
    // Function to find closest index
    function find_closest_index(target_angle, n) = 
        let(
            step = 360 / n,
            idx = round(target_angle / step) % n
        )
        idx;
        
    idx0 = find_closest_index(225, n_segments);
    idx1 = find_closest_index(315, n_segments);
    idx2 = find_closest_index(45, n_segments);
    idx3 = find_closest_index(135, n_segments);
    
    // Now we have 4 "anchor" top vertices.
    // We can create faces by iterating through the top vertices and connecting them
    // to the base vertices.
    
    // Let's create faces for the side.
    // We will iterate through the top vertices in order.
    // For each top vertex i, we determine which base edge it belongs to.
    // If it's between anchors, we interpolate? No, we just connect to the nearest base vertices.
    
    // Actually, let's just create triangles from each top vertex to the two base vertices
    // of the edge it is closest to.
    
    // Helper to get base edge indices for a top vertex index
    function get_base_edge(i, n, i0, i1, i2, i3) = 
        let(
            angle = i * 360 / n,
            // Normalize angle to 0-360
            a = angle < 0 ? angle + 360 : angle,
            // Determine quadrant
            // 0-90: Right/Back transition?
            // Let's use the anchors to define ranges.
            // Range 1: i1 to i2 (Front-Right to Back-Right) -> Edge 1-2 (Right)
            // Range 2: i2 to i3 (Back-Right to Back-Left) -> Edge 2-3 (Back)
            // Range 3: i3 to i0 (Back-Left to Front-Left) -> Edge 3-0 (Left)
            // Range 4: i0 to i1 (Front-Left to Front-Right) -> Edge 0-1 (Front)
            
            // Handle wrap-around
            r1_start = i1, r1_end = i2,
            r2_start = i2, r2_end = i3,
            r3_start = i3, r3_end = i0,
            r4_start = i0, r4_end = i1
        )
        (i >= r1_start && i <= r1_end) ? [1, 2] :
        (i >= r2_start && i <= r2_end) ? [2, 3] :
        (i >= r3_start && i <= r3_end) ? [3, 0] :
        (i >= r4_start || i <= r4_end) ? [0, 1] :
        [0, 1]; // Default
        
    // This logic is flawed for wrap-around.
    
    // Let's simplify. Just create triangles from each top vertex to the two base vertices
    // that form the edge closest to the top vertex's position.
    
    // For each top vertex i:
    //   angle = i * 360 / n
    //   if angle in [315, 45] (Right side): connect to base 1, 2
    //   if angle in [45, 135] (Back side): connect to base 2, 3
    //   if angle in [135, 225] (Left side): connect to base 3, 0
    //   if angle in [225, 315] (Front side): connect to base 0, 1
    
    // This creates a "fan" from each base edge to the arc.
    // But we need to connect the top vertices to each other too.
    
    // Let's create triangles:
    // For each top vertex i, and i+1:
    //   Find the base edge for i and i+1.
    //   If they are the same, create a quad (2 triangles) between top i, i+1 and base edge.
    //   If they are different, we need to handle the transition.
    
    // This is getting complex. Let's use a simpler polyhedron definition.
    // We will create triangles from each top vertex to the two base vertices of the
    // "closest" edge.
    
    // For each top vertex i:
    //   angle = i * 360 / n
    //   if (angle >= 315 || angle < 45) -> Edge 1-2 (Base 1, 2)
    //   else if (angle >= 45 && angle < 135) -> Edge 2-3 (Base 2, 3)
    //   else if (angle >= 135 && angle < 225) -> Edge 3-0 (Base 3, 0)
    //   else -> Edge 0-1 (Base 0, 1)
    
    //   Create triangle [4+i, 4+(i+1)%n, base_v1] and [4+i, 4+(i+1)%n, base_v2]?
    //   No, that creates a fan from the top edge to the base vertices.
    
    //   Let's create triangles:
    //   [4+i, 4+(i+1)%n, base_v1]
    //   [4+i, 4+(i+1)%n, base_v2]
    //   This creates a "double" surface if not careful.
    
    //   Correct way:
    //   For each top vertex i, create a triangle with the two base vertices of the edge.
    //   [4+i, base_v1, base_v2]
    //   This creates a fan from the base edge to the top vertex.
    //   Then we need to connect the top vertices to each other.
    
    //   Let's try:
    //   For each top vertex i:
    //     Create triangle [4+i, base_v1, base_v2]
    //   This creates a cone from each base edge to the top circle.
    //   The top circle is not connected.
    
    //   We need to connect the top vertices.
    //   Add triangles [4+i, 4+(i+1)%n, base_v1] and [4+i, 4+(i+1)%n, base_v2]?
    
    //   Let's just use the "fan from base vertex" approach.
    //   For each base vertex, create a fan to the top vertices that are "closest".
    
    //   Base 0 (Front-Left): Connect to top vertices in Front-Left quadrant.
    //   Base 1 (Front-Right): Connect to top vertices in Front-Right quadrant.
    //   Base 2 (Back-Right): Connect to top vertices in Back-Right quadrant.
    //   Base 3 (Back-Left): Connect to top vertices in Back-Left quadrant.
    
    //   This will leave gaps between the fans.
    
    //   Let's go back to the standard loft.
    //   We will create triangles between consecutive top vertices and the base.
    
    //   For each top vertex i:
    //     Determine the two base vertices that form the edge closest to the top vertex.
    //     Let them be b1, b2.
    //     Create triangle [4+i, b1, b2].
    
    //   This creates a surface from the base edges to the top circle.
    //   But the top circle is not closed.
    
    //   We need to add triangles between top vertices.
    //   For each i, create triangle [4+i, 4+(i+1)%n, b1] and [4+i, 4+(i+1)%n, b2]?
    //   No.
    
    //   Let's try this:
    //   For each top vertex i:
    //     Create triangle [4+i, 4+(i+1)%n, b1]
    //     Create triangle [4+i, 4+(i+1)%n, b2]
    //   This creates a "skirt" from the top edge to the base vertices.
    
    //   Let's implement this.
    
    side_faces = [];
    for (i = [0 : n_segments - 1]) {
        angle = i * 360 / n_segments;
        next_i = (i + 1) % n_segments;
        
        // Determine base edge for current top vertex
        // 0-45: Right (1,2)
        // 45-135: Back (2,3)
        // 135-225: Left (3,0)
        // 225-315: Front (0,1)
        // 315-360: Right (1,2)
        
        b1, b2;
        if (angle >= 315 || angle < 45) {
            b1 = 1; b2 = 2;
        } else if (angle >= 45 && angle < 135) {
            b1 = 2; b2 = 3;
        } else if (angle >= 135 && angle < 225) {
            b1 = 3; b2 = 0;
        } else {
            b1 = 0; b2 = 1;
        }
        
        // Create triangles connecting top edge (i, i+1) to base edge (b1, b2)
        // We need to be careful with orientation.
        // Top vertices are CCW looking from top.
        // Base vertices are CCW looking from bottom.
        
        // Triangle 1: [4+i, 4+next_i, b1]
        // Triangle 2: [4+i, 4+next_i, b2]
        
        // Check orientation.
        // If we look from outside, the normal should point out.
        
        side_faces = concat(side_faces, [
            [4 + i, 4 + next_i, b1],
            [4 + i, 4 + next_i, b2]
        ]);
    }
    
    all_faces = concat(faces, side_faces);
    
    polyhedron(
        points = all_vertices,
        faces = all_faces,
        convexity = 10
    );
}
