/* doodle-meta {"version":1,"parameters":{"leg_length":{"label":"Leg Length","description":"Length of the straight vertical legs","unit":"mm","feature":"leg_length"},"bend_radius":{"label":"Bend Radius","description":"Radius of the semi-circular top bend (centerline)","unit":"mm","feature":"bend_radius"},"handle_diameter":{"label":"Handle Diameter","description":"Diameter of the circular cross-section","unit":"mm","feature":"handle_diameter"}},"features":{"leg_length":{"kind":"dimension","axis":"z","label":"Leg Length"},"bend_radius":{"kind":"dimension","axis":"x","label":"Bend Radius"},"handle_diameter":{"kind":"dimension","axis":"y","label":"Handle Diameter"}}} */

// Parameters
leg_length = 33.75;
bend_radius = 20;
handle_diameter = 9;

// Derived constants
handle_radius = handle_diameter / 2;
total_height = leg_length + bend_radius + handle_radius;

// Module for the handle path (skeleton)
// The path consists of two vertical legs and a semi-circular top.
// Origin (0,0,0) is at the bottom center of the handle.
module handle_path() {
    // Left Leg
    // Extends from Z=0 to Z=leg_length
    // Centered at X = -bend_radius
    translate([-bend_radius, 0, 0])
        cube([handle_diameter, handle_diameter, leg_length], center=true);
        
    // Right Leg
    // Extends from Z=0 to Z=leg_length
    // Centered at X = +bend_radius
    translate([bend_radius, 0, 0])
        cube([handle_diameter, handle_diameter, leg_length], center=true);
        
    // Top Bend (Semi-circle)
    // Center of the arc is at (0, 0, leg_length)
    // The arc goes from angle 0 (Right) to 180 (Left) in the XZ plane
    // We use rotate_extrude to create the torus segment
    
    // Define the 2D profile in the XZ plane (relative to the rotation axis Z)
    // The profile is a circle of radius handle_radius centered at (bend_radius, 0)
    // rotate_extrude rotates around Z. 
    // To get a semi-circle in XZ, we rotate the profile around Z by 180 degrees? 
    // No, rotate_extrude creates a full torus. We need to intersect with a half-space or use a partial extrusion.
    // OpenSCAD doesn't have partial rotate_extrude directly.
    // Alternative: Use a torus and intersect with a cube to keep only the top half.
    
    // Let's build the full torus first, then cut it.
    // Torus major radius = bend_radius, minor radius = handle_radius
    // Positioned at Z = leg_length
    translate([0, 0, leg_length])
        rotate([90, 0, 0]) // Rotate so the torus lies in XZ plane (axis along Y)
            rotate_extrude()
                translate([bend_radius, 0])
                    circle(r=handle_radius);
}

// Main Design
union() {
    // 1. The Legs
    // Left Leg
    translate([-bend_radius, 0, leg_length/2])
        cylinder(h=leg_length, r=handle_radius, center=true);
        
    // Right Leg
    translate([bend_radius, 0, leg_length/2])
        cylinder(h=leg_length, r=handle_radius, center=true);
        
    // 2. The Bend
    // Create a full torus and intersect with the upper half (Z >= leg_length)
    // The torus center is at (0, 0, leg_length)
    // The torus lies in the XZ plane (axis along Y)
    
    intersection() {
        // Full Torus
        translate([0, 0, leg_length])
            rotate([90, 0, 0])
                rotate_extrude()
                    translate([bend_radius, 0])
                        circle(r=handle_radius);
                        
        // Keep only the top half (Z >= leg_length)
        // The torus extends from Z = leg_length - handle_radius to leg_length + handle_radius
        // We want to keep Z >= leg_length.
        // However, the legs connect at Z=leg_length. 
        // The torus center is at Z=leg_length.
        // The "top" of the U is the semi-circle above the center line.
        // So we keep Z >= leg_length.
        translate([0, 0, leg_length + handle_radius/2])
            cube([bend_radius*2 + handle_diameter, handle_diameter, handle_radius + 1], center=true);
    }
    
    // Ensure smooth connection between legs and bend
    // The legs end at Z=leg_length. The torus starts at Z=leg_length.
    // They share the same cross-section at the junction.
    // The union should handle this seamlessly.
}

// Adjust position to sit on build plate (Z=0)
// The legs start at Z=0 (centered at leg_length/2 with height leg_length)
// The bend is above.
// The lowest point is Z=0.
