/* doodle-meta {"version":1,"parameters":{"width":{"label":"Base Width","description":"Width of the rectangular base along X","unit":"mm","feature":"base_width"},"depth":{"label":"Base Depth","description":"Depth of the rectangular base along Y","unit":"mm","feature":"base_depth"},"height":{"label":"Height","description":"Total height of the transition piece","unit":"mm","feature":"height"},"top_diameter":{"label":"Top Diameter","description":"Diameter of the circular top face","unit":"mm","feature":"top_circle"}},"features":{"base_width":{"kind":"dimension","axis":"x","label":"Base Width"},"base_depth":{"kind":"dimension","axis":"y","label":"Base Depth"},"height":{"kind":"dimension","axis":"z","label":"Height"},"top_circle":{"kind":"region","label":"Top Circle","min":[15,15,60],"max":[45,25,60]}}} */

// Parameters
width = 60;
depth = 40;
height = 60;
top_diameter = 30;

// Derived parameters
top_radius = top_diameter / 2;
base_radius_x = width / 2;
base_radius_y = depth / 2;

// Number of points for the circle approximation
$fn = 64;

// Number of layers for the loft
layers = 20;

// Module to generate the lofted transition piece
module transition_piece() {
    // We will create a series of slices from Z=0 to Z=height.
    // Each slice is a polygon.
    // The shape at each slice is an interpolation between the base rectangle and the top circle.
    
    // To achieve a smooth "ruled" surface that looks like a loft, we interpolate
    // the radius of the shape at each angle.
    // Base shape (Rectangle): Radius at angle theta is determined by the rectangle boundary.
    // Top shape (Circle): Radius is constant (top_radius).
    
    // Rectangle radius function:
    // For a rectangle with half-width w and half-depth d, the distance from center to edge at angle theta is:
    // r(theta) = min( w / |cos(theta)|, d / |sin(theta)| )
    // However, this creates sharp corners. To make it smooth and match the "inscribed" look,
    // we can use a superellipse or simply interpolate the "radius" in a way that preserves the 
    // flat sides of the rectangle and the roundness of the circle.
    
    // A better approach for "straight sides" (ruled surface) is to interpolate the vertices.
    // But since the number of vertices differs (4 vs N), we need a common parameterization.
    // Let's use N points for both.
    
    // For the rectangle, we distribute N points along the perimeter.
    // For the circle, we distribute N points along the circumference.
    // Then we connect point i at Z=0 to point i at Z=height.
    
    // Let's define the points for the base rectangle.
    // We want the points to correspond to the circle points angularly.
    // So for each angle theta_i, we find the intersection of the ray from origin at theta_i 
    // with the rectangle boundary.
    
    // Function to get radius of rectangle at angle theta
    function rect_radius(theta, w, d) = 
        let(
            c = cos(theta),
            s = sin(theta),
            abs_c = abs(c),
            abs_s = abs(s)
        )
        (abs_c < 1e-6) ? d : 
        (abs_s < 1e-6) ? w : 
        min(w / abs_c, d / abs_s);
        
    // Function to get radius of circle at angle theta
    function circ_radius(theta, r) = r;
    
    // Function to interpolate radius
    function interp_radius(t, theta, w, d, r_top) = 
        let(
            r_base = rect_radius(theta, w, d),
            r_top_val = circ_radius(theta, r_top)
        )
        r_base * (1 - t) + r_top_val * t;
        
    // Generate the solid by stacking polygons
    // We iterate through layers
    for (i = [0 : layers - 1]) {
        // Define the z-range for this slice
        z0 = height * i / layers;
        z1 = height * (i + 1) / layers;
        
        // We need to create a polyhedron for this slice.
        // A polyhedron needs vertices and faces.
        // Vertices: Bottom ring (at z0) and Top ring (at z1).
        // Faces: Side quads (split into triangles) and caps.
        
        // Let's generate the vertices for the bottom ring (at z0)
        // and top ring (at z1).
        
        // We will use a helper module to create a slice between two z-levels.
        // But OpenSCAD polyhedron requires a list of vertices and faces.
        // We can construct these lists using list comprehensions.
        
        // Let's define the number of points
        n = $fn;
        
        // Generate vertices for the slice
        // Bottom vertices (index 0 to n-1)
        // Top vertices (index n to 2n-1)
        
        // We can't easily assign lists to variables in a way that works with polyhedron directly 
        // without a helper function that returns the lists.
        
        // Let's use a different approach: Union of many thin "frustums".
        // Each frustum is a polyhedron with 2n vertices.
        
        // Helper module to create a single slice
        module slice(z_bottom, z_top, t_bottom, t_top) {
            // t is the interpolation parameter (0 at bottom, 1 at top)
            // We need to generate the vertices for this slice.
            
            // Since we can't assign geometry, we must construct the polyhedron inline.
            // We will use a function to generate the vertex list.
            
            // Function to generate vertices for a ring at height z with interpolation t
            function ring_vertices(z, t) = 
                [ for (i = [0 : n - 1]) 
                    let(
                        theta = 360 * i / n,
                        r = interp_radius(t, theta, base_radius_x, base_radius_y, top_radius)
                    )
                    [ r * cos(theta), r * sin(theta), z ]
                ];
                
            // Generate bottom and top rings
            // Note: We need to pass the lists to polyhedron.
            // We can't call a function that returns a list and use it directly in polyhedron 
            // if the function is complex, but we can try.
            
            // Actually, let's just build the polyhedron manually.
            
            // Vertices:
            // 0..n-1: Bottom ring
            // n..2n-1: Top ring
            
            // Faces:
            // Side faces: For each i, quad (i, (i+1)%n, n+(i+1)%n, n+i)
            // Bottom cap: Fan from center? No, we are stacking slices. 
            // If we stack slices, we don't need caps if they are watertight.
            // But polyhedron needs to be closed.
            // So we need caps for the very bottom and very top.
            // For intermediate slices, the top of slice i is the bottom of slice i+1.
            // So we can just make each slice a closed polyhedron (with caps) and union them.
            // Overlapping caps is fine.
            
            // Let's define the vertices list
            // We need to compute the vertices.
            
            // Let's use a helper to get the vertex list for a given t and z.
            // Since we are in a module, we can't return lists easily.
            // We will use a workaround: generate the polyhedron using a loop over faces?
            // No, polyhedron takes lists.
            
            // Let's try to construct the lists using list comprehensions directly in the polyhedron call.
            
            // Vertices list:
            // [ for (i in [0:n-1]) bottom_vertex(i), for (i in [0:n-1]) top_vertex(i) ]
            
            // Faces list:
            // Side faces + Bottom cap + Top cap
            
            // Let's define the vertices for the bottom ring (at z_bottom, t_bottom)
            // and top ring (at z_top, t_top).
            
            // We will use a function to get the vertex at index i for a given t and z.
            function get_vertex(i, t, z) = 
                let(
                    theta = 360 * i / n,
                    r = interp_radius(t, theta, base_radius_x, base_radius_y, top_radius)
                )
                [ r * cos(theta), r * sin(theta), z ];
                
            // Now we can construct the polyhedron.
            
            // Vertices:
            // Bottom ring: indices 0 to n-1
            // Top ring: indices n to 2n-1
            
            // Faces:
            // Side faces: 
            // For i in 0..n-1:
            //   Triangle 1: [i, (i+1)%n, n+(i+1)%n]
            //   Triangle 2: [i, n+(i+1)%n, n+i]
            // Bottom cap:
            //   Center vertex? No, we can use a fan from vertex 0? 
            //   Or just add a center vertex.
            //   Let's add a center vertex for bottom and top.
            //   This complicates the index mapping.
            
            // Alternative: Just use the rings and assume the slices are thin enough 
            // that the caps are negligible or we just union them.
            // If we union them, we need the caps to be closed.
            
            // Let's add a center vertex for the bottom (index 2n) and top (index 2n+1).
            
            // Vertices:
            // 0..n-1: Bottom ring
            // n..2n-1: Top ring
            // 2n: Bottom center
            // 2n+1: Top center
            
            // Faces:
            // Side faces (as above)
            // Bottom cap: Triangles from center (2n) to each edge of bottom ring.
            //   For i in 0..n-1: [2n, i, (i+1)%n]
            // Top cap: Triangles from center (2n+1) to each edge of top ring.
            //   For i in 0..n-1: [2n+1, n+(i+1)%n, n+i]
            
            // Let's construct the lists.
            
            // We need to be careful with the winding order.
            // Assuming outward normals.
            
            // Let's try to generate the polyhedron.
            
            // Since we are in a loop, we can just call polyhedron.
            
            // We need to pass the vertices and faces.
            // We can't assign them to variables.
            // We have to inline the list comprehensions.
            
            // This is getting complex. Let's simplify.
            // Instead of a single polyhedron per slice, let's use `hull()` between two thin slices?
            // No, hull is convex.
            
            // Let's stick to the polyhedron approach but simplify the code.
            // We will generate the vertices and faces using functions.
            
            // Function to generate all vertices for a slice
            function slice_vertices(z0, t0, z1, t1) = 
                concat(
                    [ for (i = [0 : n - 1]) get_vertex(i, t0, z0) ],
                    [ for (i = [0 : n - 1]) get_vertex(i, t1, z1) ],
                    [ [0, 0, z0] ], // Bottom center
                    [ [0, 0, z1] ]  // Top center
                );
                
            // Function to generate all faces for a slice
            function slice_faces() = 
                concat(
                    // Side faces
                    [ for (i = [0 : n - 1]) 
                        let(
                            i_next = (i + 1) % n
                        )
                        [
                            [i, i_next, n + i_next],
                            [i, n + i_next, n + i]
                        ]
                    ],
                    // Bottom cap
                    [ for (i = [0 : n - 1]) 
                        let(
                            i_next = (i + 1) % n
                        )
                        [2*n, i, i_next]
                    ],
                    // Top cap
                    [ for (i = [0 : n - 1]) 
                        let(
                            i_next = (i + 1) % n
                        )
                        [2*n + 1, n + i_next, n + i]
                    ]
                );
                
            // Now call polyhedron
            polyhedron(
                points = slice_vertices(z_bottom, t_bottom, z_top, t_top),
                faces = slice_faces()
            );
        }
        
        // Generate the slice
        // t0 and t1 are the interpolation parameters for the bottom and top of the slice
        // t = z / height
        t0 = i / layers;
        t1 = (i + 1) / layers;
        
        slice(z0, z1, t0, t1);
    }
}

// Instantiate the design
transition_piece();
