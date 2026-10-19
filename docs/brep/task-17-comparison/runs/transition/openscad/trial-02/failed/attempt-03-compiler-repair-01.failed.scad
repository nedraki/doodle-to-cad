/* doodle-meta {"version":1,"parameters":{"width":{"label":"Base Width","description":"Width of the rectangular base along X","unit":"mm","feature":"base_width"},"depth":{"label":"Base Depth","description":"Depth of the rectangular base along Y","unit":"mm","feature":"base_depth"},"height":{"label":"Height","description":"Total height of the transition piece","unit":"mm","feature":"height"},"top_diameter":{"label":"Top Diameter","description":"Diameter of the circular top","unit":"mm","feature":"top_diameter"}},"features":{"base_width":{"kind":"dimension","axis":"x","label":"Base Width"},"base_depth":{"kind":"dimension","axis":"y","label":"Base Depth"},"height":{"kind":"dimension","axis":"z","label":"Height"},"top_diameter":{"kind":"dimension","axis":"x","label":"Top Diameter"}}} */

// Parameters
width = 33.4;
depth = 6.8;
height = 60.0;
top_diameter = 30.0;

// Derived parameters
top_radius = top_diameter / 2;
base_half_w = width / 2;
base_half_d = depth / 2;

// Number of segments for the loft interpolation
$fn = 64;

// Main module
module transition_piece() {
    // We construct the loft by stacking thin slices from Z=0 to Z=height.
    // Each slice is a polygon that interpolates between the rectangle at Z=0 
    // and the circle at Z=height.
    
    // To ensure watertightness and smoothness, we use a linear interpolation 
    // of the boundary points.
    
    // Define the rectangle corners (normalized to unit square for interpolation logic)
    // Rectangle: x in [-1, 1], y in [-1, 1]
    // Circle: x in [-1, 1], y in [-1, 1] (unit circle)
    
    // We will generate the solid using a polyhedron or by stacking cubes/cylinders?
    // Stacking thin cylinders/cubes is robust.
    // However, a single polyhedron is cleaner if we generate the vertices correctly.
    
    // Let's use a stack of thin slices for simplicity and robustness in OpenSCAD.
    // Slice thickness
    slice_h = 0.5;
    num_slices = ceil(height / slice_h);
    
    for (i = [0 : num_slices - 1]) {
        z = i * slice_h;
        t = z / height; // 0 at bottom, 1 at top
        
        // Interpolate dimensions
        // At t=0: width=width, depth=depth
        // At t=1: width=top_diameter, depth=top_diameter (since it's a circle)
        
        current_w = width * (1 - t) + top_diameter * t;
        current_d = depth * (1 - t) + top_diameter * t;
        
        // We need to blend the shape from rectangle to circle.
        // A simple superellipse interpolation works well for rect-to-circle.
        // Equation: |x/a|^n + |y/b|^n = 1
        // At t=0 (rect), n -> infinity (or large number like 10)
        // At t=1 (circle), n = 2
        
        // Let's use a superellipse with exponent n varying from 10 to 2.
        // n = 10 * (1-t) + 2 * t
        
        n = 10 * (1 - t) + 2 * t;
        
        // Generate points for the superellipse slice
        // We need to create a polygon for this slice and extrude it slightly.
        
        // Create the slice polygon
        slice_points = [];
        steps = 64;
        for (j = [0 : steps - 1]) {
            angle = 360 * j / steps;
            rad = angle * PI / 180;
            
            // Parametric superellipse
            // x = a * cos(t)^(2/n) * sign(cos(t))
            // y = b * sin(t)^(2/n) * sign(sin(t))
            
            cos_val = cos(rad);
            sin_val = sin(rad);
            
            // Handle signs and powers
            // If cos_val is 0, x is 0. If sin_val is 0, y is 0.
            
            x_factor = (cos_val == 0) ? 0 : pow(abs(cos_val), 2/n) * (cos_val > 0 ? 1 : -1);
            y_factor = (sin_val == 0) ? 0 : pow(abs(sin_val), 2/n) * (sin_val > 0 ? 1 : -1);
            
            x = (current_w / 2) * x_factor;
            y = (current_d / 2) * y_factor;
            
            slice_points = concat(slice_points, [[x, y]]);
        }
        
        // Extrude the slice
        // We place the slice at z, with height slice_h.
        // To avoid gaps, we can make them overlap slightly or just stack them.
        // Using linear_extrude on a polygon.
        
        // Note: linear_extrude creates a solid from a 2D polygon.
        // We need to translate it to the correct Z position.
        
        translate([0, 0, z])
            linear_extrude(height = slice_h + 0.01) // slight overlap to ensure manifold
                polygon(points = slice_points);
    }
}

// Instantiate the design
transition_piece();
