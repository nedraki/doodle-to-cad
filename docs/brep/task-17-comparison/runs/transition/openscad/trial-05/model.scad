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

// Module for the lofted transition piece
module transition_piece() {
    // Define the number of segments for the circular top
    $fn = 64;
    
    // Define the number of layers for the loft
    layers = 20;
    
    // Generate the lofted solid by stacking scaled cylinders
    // We use a union of many thin cylinders to approximate the ruled surface loft
    // from a rectangle to a circle.
    
    // To ensure watertightness and smoothness, we interpolate the shape.
    // The base is a rectangle (width x depth). The top is a circle (diameter).
    // A simple linear interpolation of the "radius" in X and Y directions 
    // from the rectangle corners to the circle radius creates the transition.
    
    // However, standard OpenSCAD doesn't have a native loft. 
    // We approximate it by stacking polygons.
    
    // Let's define the bottom polygon (rectangle) and top polygon (circle).
    // We will create a series of intermediate polygons.
    
    // Bottom rectangle vertices (centered at 0,0)
    // Top circle vertices (centered at 0,0)
    
    // We will use a loop to create slices.
    // For each slice at height z, we interpolate the shape.
    
    // The shape at height z is a superellipse-like transition or simply 
    // interpolating the vertices of the rectangle and circle.
    // A common approach for rect-to-circle is to interpolate the "radius" 
    // function. 
    
    // Let's use a simpler approach: 
    // Create a cylinder for the top part and a pyramid-like structure for the bottom?
    // No, the spec says "lofted surface connecting bottom rectangle to top circle".
    
    // We will construct the solid by unioning many thin slices.
    // Each slice is a polygon.
    
    // Define the number of points for the circle
    n_points = 64;
    
    // Function to get the radius at a given angle for the rectangle
    // This is tricky. A rectangle isn't a function of angle easily.
    // Instead, let's interpolate between the rectangle and circle shapes.
    
    // A better way in OpenSCAD for this specific shape is to use 
    // convex hull of the bottom rectangle and top circle.
    // But convex hull of a rect and circle centered on top of each other 
    // creates a shape that bulges out. 
    // The spec says "straight sides". 
    // A convex hull of the bottom rectangle (at z=0) and top circle (at z=height) 
    // creates a solid with straight edges connecting the vertices of the 
    // bottom rectangle to the vertices of the top circle.
    // This matches "straight sides" and "lofted".
    
    // Let's verify the geometry.
    // Bottom: Rectangle 60x40 at Z=0.
    // Top: Circle D=30 at Z=60.
    // Convex hull of these two sets of points.
    
    // The convex hull will connect the corners of the rectangle to the 
    // tangent points of the circle. This creates a smooth transition 
    // with straight generators (lines).
    
    // Let's implement this using convex_hull().
    
    // We need to define the points for the bottom rectangle and top circle.
    
    // Bottom rectangle points (4 corners)
    // Top circle points (many points for smoothness)
    
    // We will create a module that generates the points and hulls them.
    
    // Note: convex_hull in OpenSCAD works on a set of points.
    
    // Let's generate the points.
    
    // Bottom rectangle corners
    // (-width/2, -depth/2, 0)
    // (width/2, -depth/2, 0)
    // (width/2, depth/2, 0)
    // (-width/2, depth/2, 0)
    
    // Top circle points
    // (r*cos(theta), r*sin(theta), height)
    
    // We need to pass these points to convex_hull.
    // Since we can't assign geometry to variables, we use a module 
    // that constructs the points list and calls convex_hull.
    
    // However, convex_hull takes a list of points.
    // We can construct this list using a loop.
    
    // Let's define the points list.
    
    // Number of points on the circle
    n_circle = 64;
    
    // We will build the list of points.
    // In OpenSCAD, we can use a recursive function or a loop to build a list.
    
    // Let's use a helper module to generate the points and hull them.
    
    // Actually, we can just use the convex_hull module directly if we 
    // can generate the points.
    
    // Let's try a different approach: 
    // Use `hull()` which is similar to convex_hull but works on modules.
    // hull() { bottom_shape(); top_shape(); }
    
    // bottom_shape() is a cube (rectangle) at Z=0.
    // top_shape() is a cylinder (circle) at Z=height.
    
    // hull() {
    //     translate([0,0,0]) cube([width, depth, 0.01], center=true);
    //     translate([0,0,height]) cylinder(h=0.01, r=top_radius, center=true);
    // }
    
    // This creates a solid that is the convex hull of the two shapes.
    // This matches the "straight sides" description perfectly.
    
    // Let's refine the parameters.
    // The bottom is a rectangle 60x40.
    // The top is a circle D=30.
    // Height is 60.
    
    // We need to ensure the part sits on Z=0.
    // The cube should be from Z=0 to Z=epsilon.
    // The cylinder should be from Z=height-epsilon to Z=height.
    
    // Let's use a small epsilon for the thickness of the caps to ensure 
    // the hull works correctly.
    
    epsilon = 0.1;
    
    hull() {
        // Bottom rectangle
        translate([0, 0, epsilon/2]) 
            cube([width, depth, epsilon], center=true);
        
        // Top circle
        translate([0, 0, height - epsilon/2]) 
            cylinder(h=epsilon, r=top_radius, center=true);
    }
}

// Instantiate the design
transition_piece();
