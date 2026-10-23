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
    
// Function to interpolate radius
function interp_radius(t, theta, w, d, r_top) = 
    let(
        r_base = rect_radius(theta, w, d)
    )
    r_base * (1 - t) + r_top * t;

// Function to generate vertices for a ring at height z with interpolation t
function ring_vertices(z, t, n, w, d, r_top) = 
    [ for (i = [0 : n - 1]) 
        let(
            theta = 360 * i / n,
            r = interp_radius(t, theta, w, d, r_top)
        )
        [ r * cos(theta), r * sin(theta), z ]
    ];

// Function to generate all vertices for a slice
function slice_vertices(z0, t0, z1, t1, n, w, d, r_top) = 
    concat(
        ring_vertices(z0, t0, n, w, d, r_top),
        ring_vertices(z1, t1, n, w, d, r_top),
        [ [0, 0, z0] ], // Bottom center
        [ [0, 0, z1] ]  // Top center
    );
    
// Function to generate all faces for a slice
function slice_faces(n) = 
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

// Module to generate the lofted transition piece
module transition_piece() {
    n = $fn;
    
    for (i = [0 : layers - 1]) {
        // Define the z-range for this slice
        z0 = height * i / layers;
        z1 = height * (i + 1) / layers;
        
        // t0 and t1 are the interpolation parameters for the bottom and top of the slice
        t0 = i / layers;
        t1 = (i + 1) / layers;
        
        // Generate the polyhedron for this slice
        polyhedron(
            points = slice_vertices(z0, t0, z1, t1, n, base_radius_x, base_radius_y, top_radius),
            faces = slice_faces(n)
        );
    }
}

// Instantiate the design
transition_piece();
