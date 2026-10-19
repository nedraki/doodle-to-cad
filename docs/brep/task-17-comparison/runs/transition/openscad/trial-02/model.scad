/* doodle-meta {"version":1,"parameters":{"width":{"label":"Base Width","description":"Width of the rectangular base along X","unit":"mm","feature":"base_width"},"depth":{"label":"Base Depth","description":"Depth of the rectangular base along Y","unit":"mm","feature":"base_depth"},"height":{"label":"Height","description":"Total height of the transition piece","unit":"mm","feature":"height"},"diameter":{"label":"Top Diameter","description":"Diameter of the circular top","unit":"mm","feature":"top_diameter"}},"features":{"base_width":{"kind":"dimension","axis":"x","label":"Base Width"},"base_depth":{"kind":"dimension","axis":"y","label":"Base Depth"},"height":{"kind":"dimension","axis":"z","label":"Height"},"top_diameter":{"kind":"dimension","axis":"z","label":"Top Diameter"}}} */

// Parameters
width = 60.0;
depth = 40.0;
height = 60.0;
diameter = 30.0;

// Derived parameters
radius = diameter / 2;
$fn = 64;

// Main design
transition_piece();

module transition_piece() {
    // The object is a loft from a rectangle at Z=0 to a circle at Z=height.
    // We approximate this by stacking thin slices.
    // To ensure watertightness and manifoldness, we use a union of frustums or slices.
    // Using slices with slight overlap is robust.
    
    num_slices = 60;
    slice_height = height / num_slices;
    overlap = 0.1; // Small overlap to ensure union is watertight
    
    for (i = [0 : num_slices - 1]) {
        z_bottom = i * slice_height;
        z_top = (i + 1) * slice_height;
        
        // Interpolate dimensions at z_bottom and z_top
        // t goes from 0 at bottom to 1 at top
        t_bottom = z_bottom / height;
        t_top = z_top / height;
        
        // Width and Depth interpolate from base to diameter
        w_bottom = width * (1 - t_bottom) + diameter * t_bottom;
        d_bottom = depth * (1 - t_bottom) + diameter * t_bottom;
        
        w_top = width * (1 - t_top) + diameter * t_top;
        d_top = depth * (1 - t_top) + diameter * t_top;
        
        // Create a frustum for this slice
        // The slice spans from z_bottom to z_top + overlap to ensure connection with next slice
        // But we must be careful not to overshoot the total height.
        // Actually, simpler: just make each slice a frustum from z_bottom to z_top.
        // To ensure union works, we can make them slightly taller or rely on exact face matching.
        // Exact face matching in OpenSCAD can be tricky. Let's use a small overlap.
        
        // We need to center the geometry.
        // Base is centered at X=0, Y=0. Top is centered at X=0, Y=0.
        
        // Frustum from (w_bottom, d_bottom) at z_bottom to (w_top, d_top) at z_top
        // We extend the top of the slice by 'overlap' to merge with the next one.
        // However, the last slice should not extend beyond height.
        
        actual_z_top = (i == num_slices - 1) ? height : z_top + overlap;
        
        // Interpolate dimensions at actual_z_top
        t_actual_top = actual_z_top / height;
        w_actual_top = width * (1 - t_actual_top) + diameter * t_actual_top;
        d_actual_top = depth * (1 - t_actual_top) + diameter * t_actual_top;
        
        slice_frustum(w_bottom, d_bottom, w_actual_top, d_actual_top, z_bottom, actual_z_top);
    }
}

module slice_frustum(w1, d1, w2, d2, z1, z2) {
    // Creates a frustum connecting a rectangle w1xd1 at z1 to w2xd2 at z2
    // Centered on X and Y axes
    
    // We can construct this by creating a polyhedron or by using hull() of two cubes.
    // hull() is robust for convex shapes.
    
    // Cube 1 at z1
    translate([0, 0, z1]) {
        cube([w1, d1, 0.001], center=true);
    }
    
    // Cube 2 at z2
    translate([0, 0, z2]) {
        cube([w2, d2, 0.001], center=true);
    }
    
    // Hull them
    // Note: hull() of two cubes centered on Z axis creates the frustum.
    // But we need to be careful with the "center=true" and translation.
    // The cubes are thin slabs. Hulling them creates the solid between them.
    
    // Wait, hull() of two thin cubes might not be perfectly watertight if they are just planes.
    // Better to use actual small cubes or just rely on the fact that hull() of two convex polyhedra is convex.
    // Let's use small cubes with height 0.001 centered at z1 and z2.
    
    // Actually, standard practice for loft in OpenSCAD without libraries is often hull() of two shapes.
    // If we hull two cubes, we get the frustum.
    
    // Let's refine the slice approach. Instead of many slices, we can just hull the base and top?
    // No, hull(rect, circle) creates a shape where the sides are straight lines from the corners of the rect to the tangent points of the circle?
    // Actually, hull() of a rectangle and a circle creates a shape that is the convex hull.
    // The convex hull of a rectangle and a concentric circle (where circle is inside the rect's bounding box) 
    // will have flat faces connecting the rectangle corners to the circle.
    // This matches the "linear taper" description if we consider the "sides" as the convex hull faces.
    // However, a true loft usually interpolates the perimeter.
    // The prompt says "linear taper of the sides".
    // If we just hull the base rectangle and the top circle, we get a shape that is the convex hull.
    // Is that what is intended? "Transition piece" usually implies a loft.
    // A loft from rect to circle typically has curved sides if done with NURBS, but "linear taper" suggests ruled surfaces.
    // The convex hull is a ruled surface between the two shapes.
    // Let's try the simple hull first. It's robust and likely what is meant by "linear taper" in a simple CAD context.
    
    // Let's re-evaluate. The prompt mentions "linear taper of the sides in the XZ plane".
    // Front view is a trapezoid. This means the width tapers linearly.
    // If we hull a rectangle and a circle, the front view (projection onto XZ) will be a trapezoid?
    // The rectangle projects to a line of width W. The circle projects to a line of width D.
    // The hull of these two lines is a trapezoid. Yes.
    // The side view (projection onto YZ) will be a trapezoid from Depth to Diameter. Yes.
    // The top view is the circle. Yes.
    // The bottom view is the rectangle. Yes.
    
    // So, a simple hull() of the base rectangle and the top circle is sufficient and correct.
    
    // Let's implement the simple hull.
    
    // Base Rectangle
    translate([0, 0, 0]) {
        cube([width, depth, 0.001], center=true);
    }
    
    // Top Circle
    translate([0, 0, height]) {
        cylinder(h=0.001, r=radius, center=true);
    }
    
    // Hull them
    // We need to wrap the two shapes in a hull() call.
    // But we can't hull() inside a module call easily if we want to keep it clean.
    // Let's just put the hull at the top level or in a module.
    
    // Wait, the previous slice approach was also valid. Hull is simpler.
    // Let's use hull.
    
    // Correction: The previous code block had a loop. I will replace it with the hull approach.
    // But wait, I already wrote the loop. I should stick to one method.
    // The hull method is much cleaner.
    
    // Let's rewrite the module to use hull.
}

// Redefining the main module to use hull
module transition_piece() {
    hull() {
        // Base: Rectangle 60x40 at Z=0
        translate([0, 0, 0]) {
            cube([width, depth, 0.001], center=true);
        }
        
        // Top: Circle diameter 30 at Z=height
        translate([0, 0, height]) {
            cylinder(h=0.001, r=radius, center=true);
        }
    }
}
