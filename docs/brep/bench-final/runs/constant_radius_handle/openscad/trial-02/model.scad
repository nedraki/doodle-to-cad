/* doodle-meta {"version":1,"parameters":{"bend_radius":{"label":"Bend Radius","description":"Radius of the semi-circular bend","unit":"mm","feature":"bend_radius"},"leg_length":{"label":"Leg Length","description":"Length of the straight vertical legs","unit":"mm","feature":"leg_length"},"rod_diameter":{"label":"Rod Diameter","description":"Diameter of the circular cross-section","unit":"mm","feature":"rod_diameter"}},"features":{"bend_radius":{"kind":"dimension","axis":"x","label":"Bend Radius"},"leg_length":{"kind":"dimension","axis":"z","label":"Leg Length"},"rod_diameter":{"kind":"dimension","axis":"y","label":"Rod Diameter"}}} */

// Parameters
bend_radius = 20.0;
leg_length = 33.75;
rod_diameter = 9;

// Derived constants
rod_radius = rod_diameter / 2;

// Helper module for Torus
// Creates a torus centered at origin, axis along Z by default.
// We will rotate it to align axis with Y.
module torus(major_radius, minor_radius) {
    rotate_extrude(convexity=10)
        translate([major_radius, 0, 0])
            circle(r=minor_radius);
}

// Main module
module handle_body() {
    // 1. Left Leg
    // Vertical cylinder at X = -bend_radius
    // Extends from Z=0 to Z=leg_length
    translate([-bend_radius, 0, leg_length/2])
        cylinder(h=leg_length, r=rod_radius, center=true);

    // 2. Right Leg
    // Vertical cylinder at X = +bend_radius
    // Extends from Z=0 to Z=leg_length
    translate([bend_radius, 0, leg_length/2])
        cylinder(h=leg_length, r=rod_radius, center=true);

    // 3. Semi-circular Bend
    // Centered at (0, 0, leg_length)
    // The torus ring lies in the XZ plane, so its axis is along Y.
    // Default torus axis is Z. Rotate 90 deg around X to make axis Y.
    translate([0, 0, leg_length])
        rotate([90, 0, 0])
            intersection() {
                // Full torus
                torus(major_radius=bend_radius, minor_radius=rod_radius);
                
                // Keep only the upper half (Z > 0 in local frame, which is Z > leg_length in global)
                // The torus is centered at local (0,0,0).
                // We want to keep the part where local Z > 0.
                // Create a cube that covers Z > 0.
                // Dimensions: Large enough to cover the torus.
                // X range: -R-r to R+r. Y range: -r to r. Z range: 0 to R+r.
                translate([0, 0, (bend_radius + rod_radius)/2])
                    cube([2*(bend_radius + rod_radius), 2*rod_radius, bend_radius + rod_radius], center=true);
            }
}

// Final instantiation
handle_body();
