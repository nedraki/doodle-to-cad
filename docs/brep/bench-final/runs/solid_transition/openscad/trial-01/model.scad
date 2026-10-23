/* doodle-meta {"version":1,"parameters":{"base_width":{"label":"Base Width","description":"Width of the rectangular base along X","unit":"mm","feature":"base_width"},"base_depth":{"label":"Base Depth","description":"Depth of the rectangular base along Y","unit":"mm","feature":"base_depth"},"top_diameter":{"label":"Top Diameter","description":"Diameter of the circular top","unit":"mm","feature":"top_diameter"},"height":{"label":"Height","description":"Overall height of the transition piece","unit":"mm","feature":"height"}},"features":{"base_width":{"kind":"dimension","axis":"x","label":"Base Width"},"base_depth":{"kind":"dimension","axis":"y","label":"Base Depth"},"top_diameter":{"kind":"dimension","axis":"z","label":"Top Diameter"},"height":{"kind":"dimension","axis":"z","label":"Height"}}} */

// Parameters
base_width = 60.0;
base_depth = 40.0;
top_diameter = 30.0;
height = 60.0;

// Derived parameters
top_radius = top_diameter / 2.0;
base_half_w = base_width / 2.0;
base_half_d = base_depth / 2.0;

// Module for the lofted transition piece
module transition_piece() {
    // We create a loft by stacking thin slices.
    // To ensure watertightness and smoothness, we use a high number of slices.
    slices = 100;
    slice_height = height / slices;
    
    for (i = [0 : slices - 1]) {
        // Interpolation factor t from 0 (bottom) to 1 (top)
        t = i / (slices - 1);
        
        // Current Z position of the bottom of this slice
        z_pos = i * slice_height;
        
        // Interpolate dimensions
        // Width (X) tapers from base_width to top_diameter
        current_width = base_width * (1 - t) + top_diameter * t;
        // Depth (Y) tapers from base_depth to top_diameter
        current_depth = base_depth * (1 - t) + top_diameter * t;
        
        // Create a rounded rectangle (stadium-like) for the slice
        // To approximate the transition from rect to circle, we use a hull of a box and a cylinder
        // or simply a rounded box where the corner radius interpolates.
        // A simpler robust approach for rect-to-circle loft in OpenSCAD is using hull() between 
        // a box at the bottom and a cylinder at the top, but that creates a single solid.
        // However, hull() between a box and a cylinder creates a shape that is not exactly 
        // a linear interpolation of the cross-sections in the way a loft is, but it is often 
        // acceptable. 
        // For a true loft, we stack slices.
        
        // Let's use a rounded box approach for each slice.
        // The "roundness" increases as we go up.
        // At bottom (t=0), radius is 0 (sharp corners).
        // At top (t=1), it's a circle.
        
        // A better approximation for Rect -> Circle loft is to use a superellipse or 
        // simply hull() the bottom rectangle and top circle. 
        // hull() is the most robust way to get a smooth transition in OpenSCAD without complex math.
        
        // Let's stick to the hull method as it guarantees manifold geometry and smooth transitions.
    }
    
    // Using hull() is the standard OpenSCAD way to loft between two shapes.
    // Shape 1: Rectangular base at Z=0
    // Shape 2: Circular top at Z=height
    
    hull() {
        // Base: Rectangular prism
        translate([0, 0, 0])
            cube([base_width, base_depth, 0.01], center=true);
            
        // Top: Cylindrical prism
        translate([0, 0, height])
            cylinder(h=0.01, r=top_radius, center=true);
    }
}

// Instantiate the design
transition_piece();
