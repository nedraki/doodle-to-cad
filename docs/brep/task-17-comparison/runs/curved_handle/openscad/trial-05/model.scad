/* doodle-meta {"version":1,"parameters":{"leg_length":{"label":"Leg Length","description":"Length of the straight vertical legs","unit":"mm","feature":"leg_length"},"bend_radius":{"label":"Bend Radius","description":"Centerline radius of the semi-circular bend","unit":"mm","feature":"bend_radius"},"rod_diameter":{"label":"Rod Diameter","description":"Diameter of the handle cross-section","unit":"mm","feature":"rod_diameter"}},"features":{"leg_length":{"kind":"dimension","axis":"z","label":"Leg Length"},"bend_radius":{"kind":"dimension","axis":"x","label":"Bend Radius"},"rod_diameter":{"kind":"dimension","axis":"x","label":"Rod Diameter"}}} */

// Parameters
leg_length = 30;
bend_radius = 20;
rod_diameter = 8;

// Derived dimensions
rod_radius = rod_diameter / 2;

// Module to create the handle
module handle() {
    // 1. Left Leg
    // Cylinder axis along Z. Centered at X = -bend_radius, Y = 0.
    // Height = leg_length.
    // To ensure watertight connection with the bend, we extend the leg slightly into the bend area or rely on union.
    // Union handles overlaps.
    translate([-bend_radius, 0, 0])
        cylinder(h = leg_length, r = rod_radius, center = false);

    // 2. Right Leg
    translate([bend_radius, 0, 0])
        cylinder(h = leg_length, r = rod_radius, center = false);

    // 3. Bend (Semi-circle)
    // The bend connects the tops of the legs.
    // Center of the semi-circle arc is at (0, 0, leg_length).
    // The arc goes from angle 180 (left) to 0 (right) in the XZ plane?
    // No, the bend is in the XZ plane (since legs are vertical along Z and separated along X).
    // The cross-section is circular, so we sweep a circle along the arc.
    // The arc is in the XZ plane. The circle profile is in the YZ plane (perpendicular to the tangent).
    // Actually, simpler approach:
    // Create a torus segment or use rotate_extrude?
    // Since the path is a semi-circle in the XZ plane, and the profile is a circle perpendicular to the path...
    // The path tangent at the top is along X. The profile is in YZ.
    // The path tangent at the sides is along Z. The profile is in XY.
    // This is a standard sweep.
    // In OpenSCAD, we can approximate this by creating a torus and cutting it, or using rotate_extrude if the axis of rotation is correct.
    // The bend is a semi-circle in the XZ plane.
    // If we rotate_extrude a circle centered at (bend_radius, 0) around the Z axis, we get a torus.
    // But the bend is in the XZ plane, meaning the "hole" of the torus is along the Y axis?
    // Let's visualize:
    // Legs are at X = +/- R. They go up Z.
    // The bend connects them. It curves "over" the Y axis? No, it curves in the XZ plane.
    // The center of curvature is at (0, 0, leg_length).
    // The arc is in the XZ plane.
    // So the "tube" follows this arc.
    // This is equivalent to a torus with major radius bend_radius and minor radius rod_radius,
    // centered at (0, 0, leg_length), with the torus axis along Y.
    // A standard torus in OpenSCAD (rotate_extrude) has its axis along Z.
    // So we need to rotate the torus 90 degrees around X to make its axis along Y.
    
    // Create Torus:
    // Major radius = bend_radius.
    // Minor radius = rod_radius.
    // Centered at origin initially.
    // Then translate to (0, 0, leg_length).
    // Then rotate 90 deg around X to align the torus axis with Y.
    // Then cut it in half to keep only the top half (Z > leg_length).
    
    // Wait, the legs connect to the bend.
    // The legs are cylinders along Z.
    // The bend is a semi-torus.
    // The connection points are at ( +/- bend_radius, 0, leg_length ).
    // The torus center is at (0, 0, leg_length).
    // The torus axis is along Y.
    // The torus lies in the XZ plane (locally).
    // We want the upper half of the torus (Z > leg_length).
    
    difference() {
        // Full Torus
        translate([0, 0, leg_length])
            rotate([90, 0, 0])
                rotate_extrude()
                    translate([bend_radius, 0])
                        circle(r = rod_radius);
        
        // Cut off the bottom half of the torus
        // The torus center is at Z = leg_length.
        // We want to keep Z > leg_length.
        // So we subtract a box that covers Z < leg_length.
        // The box should be large enough to cover the entire torus width and depth.
        // Torus extent in X: +/- (bend_radius + rod_radius).
        // Torus extent in Y: +/- rod_radius.
        // Torus extent in Z: leg_length +/- (bend_radius + rod_radius).
        // We cut everything below Z = leg_length.
        // Box dimensions:
        // Width (X): 2 * (bend_radius + rod_radius) + margin
        // Depth (Y): 2 * rod_radius + margin
        // Height (Z): (bend_radius + rod_radius) + margin (to cover from center down)
        // Position: Centered in X and Y, bottom at Z = leg_length - (bend_radius + rod_radius) - margin, top at Z = leg_length.
        
        translate([0, 0, leg_length - (bend_radius + rod_radius) - 1])
            cube([2 * (bend_radius + rod_radius) + 2, 2 * rod_radius + 2, (bend_radius + rod_radius) + 1], center = false);
    }
    
    // Note: The legs are cylinders from Z=0 to Z=leg_length.
    // The torus is centered at Z=leg_length.
    // The union of legs and the top-half torus will form the handle.
    // The legs end at Z=leg_length. The torus starts at Z=leg_length (equator).
    // They touch at the equator.
    // To ensure a solid connection, the legs should overlap with the torus slightly or the torus should extend down.
    // However, the "leg_length" parameter usually implies the straight part.
    // If the legs are exactly leg_length, they meet the torus at the tangent point.
    // In OpenSCAD, union of touching solids is fine.
    // But to be safe against rendering artifacts, we can extend the legs slightly into the bend region.
    // Let's extend the legs by rod_radius/2 into the bend area?
    // No, the bend is curved. The legs are straight.
    // The tangent of the torus at the equator (Z=leg_length, X=+/-bend_radius) is vertical (along Z).
    // So the legs align perfectly with the torus at the connection point.
    // Union should work.
}

// Instantiate the handle
handle();
