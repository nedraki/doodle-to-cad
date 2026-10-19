/* doodle-meta {"version":1,"parameters":{"bend_radius":{"label":"Bend Centreline Radius","description":"Radius of the semi-circular bend path","unit":"mm","feature":"bend_radius"},"leg_length":{"label":"Straight Leg Length","description":"Length of the straight vertical legs","unit":"mm","feature":"leg_length"},"bar_diameter":{"label":"Bar Diameter","description":"Diameter of the handle cross-section","unit":"mm","feature":"bar_diameter"}},"features":{"bend_radius":{"kind":"dimension","axis":"x","label":"Bend Radius"},"leg_length":{"kind":"dimension","axis":"z","label":"Leg Length"},"bar_diameter":{"kind":"dimension","axis":"x","label":"Bar Diameter"}}} */

// Parameters
bend_radius = 20;
leg_length = 30;
bar_diameter = 8;

// Derived dimensions
total_height = leg_length + bend_radius + bar_diameter/2;
total_width = 2 * bend_radius + bar_diameter;

// Positioning to sit on build plate (Z=0)
// The lowest point of the handle is the bottom of the legs.
// The path centerline for the legs starts at Z = bar_diameter/2.
// The path centerline for the arc is at Z = leg_length + bar_diameter/2.

module handle() {
    // 1. Left Straight Leg
    // Cylinder axis is Z. Centered at X = -bend_radius.
    // Bottom at Z = bar_diameter/2 (so bottom face is at Z=0).
    // Top at Z = leg_length + bar_diameter/2.
    // Height = leg_length.
    translate([-bend_radius, 0, bar_diameter/2])
        cylinder(h=leg_length, d=bar_diameter, $fn=32);

    // 2. Right Straight Leg
    // Centered at X = +bend_radius.
    translate([bend_radius, 0, bar_diameter/2])
        cylinder(h=leg_length, d=bar_diameter, $fn=32);

    // 3. Curved Bend (Semi-circle)
    // Torus centered at Z = leg_length + bar_diameter/2.
    // Major radius = bend_radius. Minor radius = bar_diameter/2.
    // We need the top half (Z > center).
    // A full torus is created, then intersected with a cube covering Z >= center.
    translate([0, 0, leg_length + bar_diameter/2])
        intersection() {
            // Full torus
            rotate([90, 0, 0]) // Rotate so torus lies in XY plane (hole along Z)
                torus(major_r=bend_radius, minor_r=bar_diameter/2);
            
            // Keep only the top half (Z >= 0 relative to torus center)
            // The torus center is at local Z=0. We want Z >= 0.
            translate([0, 0, -0.01]) // Small epsilon to ensure overlap
                cube([total_width + bar_diameter, total_width + bar_diameter, total_height], center=true);
        }
}

// Helper module for Torus since OpenSCAD doesn't have a built-in torus primitive in older versions, 
// but standard OpenSCAD has torus() in newer versions. 
// To be safe and compatible, I will implement torus using rotate_extrude or just use the built-in if available.
// Standard OpenSCAD >= 2015 has torus(). I will use it.

// Re-implementing torus usage correctly for the intersection logic above.
// The intersection cube needs to be large enough to cover the whole torus width/depth.
// Torus extent in X/Y is 2*(major_r + minor_r).
// Torus extent in Z is 2*minor_r.
// We want the half where Z >= 0 (relative to torus center).

module handle_v2() {
    // Left Leg
    translate([-bend_radius, 0, bar_diameter/2])
        cylinder(h=leg_length, d=bar_diameter, $fn=32);

    // Right Leg
    translate([bend_radius, 0, bar_diameter/2])
        cylinder(h=leg_length, d=bar_diameter, $fn=32);

    // Bend
    translate([0, 0, leg_length + bar_diameter/2]) {
        // Create a half-torus by intersecting a full torus with a box
        // The torus is centered at origin. We want Z >= 0.
        intersection() {
            torus(major_r=bend_radius, minor_r=bar_diameter/2, $fn=32);
            // Box covering Z from 0 to large positive value
            // X and Y need to cover the torus extent: +/- (bend_radius + bar_diameter/2)
            translate([0, 0, (bend_radius + bar_diameter/2)/2])
                cube([2*(bend_radius + bar_diameter/2), 2*(bend_radius + bar_diameter/2), bend_radius + bar_diameter/2], center=true);
        }
    }
}

// Instantiate
handle_v2();
