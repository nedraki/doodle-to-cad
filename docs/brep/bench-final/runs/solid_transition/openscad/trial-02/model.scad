/* doodle-meta {"version":1,"parameters":{"base_width":{"label":"Base Width","description":"Width of the rectangular base","unit":"mm","feature":"base_width"},"base_depth":{"label":"Base Depth","description":"Depth of the rectangular base","unit":"mm","feature":"base_depth"},"top_diameter":{"label":"Top Diameter","description":"Diameter of the circular top","unit":"mm","feature":"top_diameter"},"height":{"label":"Height","description":"Total height of the transition piece","unit":"mm","feature":"height"}},"features":{"base_width":{"kind":"dimension","axis":"x","label":"Base Width"},"base_depth":{"kind":"dimension","axis":"y","label":"Base Depth"},"top_diameter":{"kind":"dimension","axis":"x","label":"Top Diameter"},"height":{"kind":"dimension","axis":"z","label":"Height"}}} */

// User-editable parameters
base_width = 60;
base_depth = 40;
top_diameter = 30;
height = 60;

// Derived parameters (not user-editable)
top_radius = top_diameter / 2;
base_half_w = base_width / 2;
base_half_d = base_depth / 2;
$fn = 64;

// Main design
transition_piece();

module transition_piece() {
    // Create the lofted solid by stacking slices
    // We use a high number of slices for smoothness
    slices = 100;
    
    for (i = [0 : slices - 1]) {
        // Interpolate between 0 and height
        z0 = (i / slices) * height;
        z1 = ((i + 1) / slices) * height;
        
        // Calculate dimensions at z0 and z1
        // Linear interpolation factor t from 0 (bottom) to 1 (top)
        t0 = i / slices;
        t1 = (i + 1) / slices;
        
        // Width and depth interpolate from base to top_diameter
        w0 = base_width * (1 - t0) + top_diameter * t0;
        d0 = base_depth * (1 - t0) + top_diameter * t0;
        
        w1 = base_width * (1 - t1) + top_diameter * t1;
        d1 = base_depth * (1 - t1) + top_diameter * t1;
        
        // Create a slice using hull of two shapes
        // Bottom of slice is at z0, top at z1
        // We hull a rectangle at z0 and a circle at z1? 
        // No, standard lofting in OpenSCAD often uses hull of two adjacent slices.
        // To make it watertight and smooth, we hull the slice at z0 and z1.
        // But simply hulling a rect and circle creates a twisted shape if not careful.
        // A better approach for Rect-to-Circle is to use hull of two polygons or shapes.
        // Let's use hull of two shapes: one at z0, one at z1.
        // Shape at z0: Rectangle w0 x d0
        // Shape at z1: Rectangle w1 x d1? No, top is circle.
        
        // Actually, the standard way to loft rect to circle in OpenSCAD is:
        // hull() {
        //   translate([0,0,z0]) square([w0, d0], center=true); // This is 2D, need 3D
        // }
        
        // Let's use the "hull of two shapes" method per slice.
        // Slice i goes from z0 to z1.
        // We define the cross-section at z0 and z1.
        // At z0: Rectangle w0 x d0
        // At z1: Rectangle w1 x d1 (interpolated)
        // Wait, if we interpolate width and depth linearly, the top is a square of size top_diameter.
        // The spec says top is a CIRCLE of diameter 30.
        // So at t=1, the shape is a circle.
        // At t=0, the shape is a rectangle.
        
        // A common trick is to hull a rectangle and a circle.
        // But we need a continuous loft.
        // Let's try hulling two shapes:
        // 1. A rectangle at z0
        // 2. A circle at z1? No, that creates a discontinuity.
        
        // Better approach:
        // For each slice, hull the shape at z0 and the shape at z1.
        // Shape at z:
        // If z is close to 0, it's a rectangle.
        // If z is close to H, it's a circle.
        // How to interpolate shape?
        // We can use a "superellipse" or just hull a rect and circle at the same z? No.
        
        // Let's use the standard "hull of two shapes" for the whole object?
        // hull() {
        //   translate([0,0,0]) cube([base_width, base_depth, 0.1], center=true);
        //   translate([0,0,height]) cylinder(h=0.1, r=top_radius, center=true);
        // }
        // This creates a smooth transition from rect to circle.
        // The "uncertainty" says linear loft. Hulling a rect and circle creates a linear transition of the convex hull.
        // This is the most robust way in OpenSCAD.
        
        // Let's verify the dimensions.
        // Bottom: Rect 60x40.
        // Top: Circle D30.
        // Height: 60.
        
        // The hull of a cube (thin) and a cylinder (thin) will create the loft.
        // To ensure it sits on Z=0, we place the bottom at Z=0.
        
        // Let's refine the hull approach.
        // We need a solid body.
        // hull() {
        //   // Bottom rectangle
        //   translate([0, 0, 0]) 
        //     cube([base_width, base_depth, 0.01], center=true);
        //   // Top circle
        //   translate([0, 0, height]) 
        //     cylinder(h=0.01, r=top_radius, center=true);
        // }
        
        // This creates a solid from Z=0 to Z=height.
        // The bottom face is at Z=0 (approx, due to center=true on thin cube).
        // To be precise, let's use non-centered cubes/cylinders or adjust translation.
        
        // Bottom: Cube from Z=0 to Z=epsilon
        // Top: Cylinder from Z=height-epsilon to Z=height
        
        // Let's use the hull method.
        hull() {
            // Base: Rectangle 60x40 at Z=0
            // Using a thin cube to define the profile
            translate([0, 0, 0.01]) 
                cube([base_width, base_depth, 0.02], center=true);
            
            // Top: Circle D30 at Z=height
            translate([0, 0, height - 0.01]) 
                cylinder(h=0.02, r=top_radius, center=true);
        }
    }
}
