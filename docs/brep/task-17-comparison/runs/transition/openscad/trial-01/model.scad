/* doodle-meta {"version":1,"parameters":{"base_width":{"label":"Base Width","description":"Width of the rectangular base along X","unit":"mm","feature":"base_width"},"base_depth":{"label":"Base Depth","description":"Depth of the rectangular base along Y","unit":"mm","feature":"base_depth"},"top_diameter":{"label":"Top Diameter","description":"Diameter of the circular top face","unit":"mm","feature":"top_diameter"},"height":{"label":"Height","description":"Total height of the transition piece","unit":"mm","feature":"height"}},"features":{"base_width":{"kind":"dimension","axis":"x","label":"Base Width"},"base_depth":{"kind":"dimension","axis":"y","label":"Base Depth"},"top_diameter":{"kind":"dimension","axis":"x","label":"Top Diameter"},"height":{"kind":"dimension","axis":"z","label":"Height"}}} */

// Parameters
base_width = 60;
base_depth = 40;
top_diameter = 30;
height = 60;

// Derived parameters
top_radius = top_diameter / 2;
base_half_w = base_width / 2;
base_half_d = base_depth / 2;

// Module to create the lofted transition piece
// Uses a linear interpolation between a rectangular base and a circular top.
// The geometry is constructed by stacking thin slices (polygons) from Z=0 to Z=height.
module transition_piece() {
    // Number of slices for smooth transition
    slices = 60;
    slice_height = height / slices;
    
    // We build the solid by unioning many thin prisms.
    // Each prism is a polygon extruded by slice_height.
    // To ensure watertightness and manifoldness, we stack them carefully.
    
    for (i = [0 : slices - 1]) {
        // Calculate interpolation factor t (0 at bottom, 1 at top)
        // Center of the slice
        z_center = (i + 0.5) * slice_height;
        t = z_center / height;
        
        // Interpolate dimensions
        // Width (X) goes from base_width to top_diameter
        current_width = base_width * (1 - t) + top_diameter * t;
        // Depth (Y) goes from base_depth to top_diameter
        current_depth = base_depth * (1 - t) + top_diameter * t;
        
        // Create the polygon for this slice
        // The polygon is centered at (0,0) in XY, then translated to z_center
        // We use a high-resolution circle approximation for the top part, 
        // but since it's a loft, the shape morphs from rect to circle.
        // A simple linear interpolation of vertices is complex for rect->circle.
        // Instead, we can use the hull() of a rectangle and a circle at each level? 
        // No, hull() of rect and circle at same Z is just the union.
        // The "loft" implies the sides are straight lines connecting the perimeters.
        
        // A robust way to do rect-to-circle loft in OpenSCAD without external libs 
        // is to use the hull() of the bottom rect and top circle? 
        // hull() of a rect and a circle creates a shape where the sides are 
        // straight lines connecting the convex hull points. 
        // For a rect and a concentric circle, the hull is exactly the transition piece 
        // described (straight sides from corners/edges to the circle).
        
        // Let's verify: 
        // Bottom: Rect 60x40. Top: Circle D30.
        // Hull(Rect, Circle) will connect the extreme points.
        // The front view will be a trapezoid.
        // The side view will be a trapezoid.
        // The top view will be the circle.
        // The bottom view will be the rectangle.
        // This matches the "Solid Rectangular-to-Circular Transition Piece" description perfectly.
        
        // So, we don't need slices. We just need hull().
    }
    
    // Re-implementing with hull() for simplicity and accuracy
    // Bottom rectangle at Z=0
    translate([0, 0, 0])
        cube([base_width, base_depth, 0.01], center=true); // Thin slab to define plane
        
    // Top circle at Z=height
    translate([0, 0, height])
        cylinder(h=0.01, r=top_radius, center=true);
}

// Main design instantiation
// We use hull() to create the solid transition.
// Note: hull() requires the objects to be non-empty.
// We use thin cubes/cylinders to define the profiles at the correct Z levels.

hull() {
    // Bottom Profile: Rectangle 60x40 at Z=0
    // Using a thin cube to define the footprint
    translate([0, 0, 0])
        cube([base_width, base_depth, 0.001], center=true);
        
    // Top Profile: Circle D30 at Z=height
    // Using a thin cylinder to define the footprint
    translate([0, 0, height])
        cylinder(h=0.001, r=top_radius, center=true);
}
