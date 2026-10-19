/* doodle-meta {"version":1,"parameters":{"leg_length":{"label":"Leg Length","description":"Length of the straight vertical legs","unit":"mm","feature":"leg_length"},"bend_radius":{"label":"Bend Radius","description":"Centerline radius of the semi-circular bend","unit":"mm","feature":"bend_radius"},"handle_diameter":{"label":"Handle Diameter","description":"Diameter of the circular cross-section","unit":"mm","feature":"cross_section"}},"features":{"leg_length":{"kind":"dimension","axis":"z","label":"Leg Length"},"bend_radius":{"kind":"dimension","axis":"x","label":"Bend Radius"},"cross_section":{"kind":"dimension","axis":"y","label":"Handle Diameter"}}} */

// Parameters
leg_length = 30;
bend_radius = 20;
handle_diameter = 8;

// Derived constants
handle_radius = handle_diameter / 2;
total_height = leg_length + bend_radius + handle_radius;

// Module: The complete handle body
module handle_body() {
    // 1. Left Leg
    // Positioned at X = -bend_radius, extending from Z=0 to Z=leg_length
    // Centered in Y
    translate([-bend_radius, 0, leg_length / 2]) {
        cylinder(h=leg_length, r=handle_radius, center=true, $fn=32);
    }

    // 2. Right Leg
    // Positioned at X = +bend_radius, extending from Z=0 to Z=leg_length
    // Centered in Y
    translate([bend_radius, 0, leg_length / 2]) {
        cylinder(h=leg_length, r=handle_radius, center=true, $fn=32);
    }

    // 3. Semi-circular Bend
    // Centered at (0, 0, leg_length)
    // Torus major radius = bend_radius, minor radius = handle_radius
    // We use a torus and cut the bottom half to keep it clean and ensure it sits on Z=0
    translate([0, 0, leg_length]) {
        difference() {
            // Full torus
            rotate([90, 0, 0]) {
                torus(major_r=bend_radius, minor_r=handle_radius, fn=32);
            }
            // Cut away the bottom half (Z < 0 relative to torus center)
            // The torus center is at Z=leg_length. We want to keep Z >= leg_length.
            // So we remove everything below Z=leg_length.
            translate([0, 0, -bend_radius - handle_radius - 1]) {
                cube([bend_radius*2 + handle_radius*2 + 2, bend_radius*2 + handle_radius*2 + 2, bend_radius + handle_radius + 1], center=true);
            }
        }
    }
}

// Helper module for Torus (since standard torus isn't a primitive in all versions, 
// but rotate_extrude is standard. However, rotate_extrude of a circle is a torus.
// Let's implement torus via rotate_extrude to be safe and standard.)

module torus(major_r, minor_r, fn=32) {
    // Create a circle in the XZ plane (offset by major_r in X)
    // Then rotate around Z axis.
    // Wait, rotate_extrude rotates around Z.
    // So we need the profile in the XZ plane? No, rotate_extrude takes a 2D polygon in XY and rotates around Z.
    // So we define the circle in the XZ plane? No.
    // Standard torus: Circle in XZ plane at distance R from Z axis, rotated around Z.
    // But rotate_extrude works on 2D shapes in XY.
    // So we define the circle in the XZ plane? No, we define it in the XY plane?
    // If we define a circle in the XZ plane, we can't rotate_extrude it directly around Z unless we project it.
    // Actually, the standard way:
    // Define a circle in the XZ plane? No.
    // Let's use the standard torus construction:
    // A circle of radius r, centered at (R, 0, 0) in the XZ plane? No.
    // Let's stick to the simplest OpenSCAD torus implementation:
    // rotate_extrude() { translate([major_r, 0, 0]) circle(r=minor_r); }
    // This creates a torus lying in the XY plane (flat).
    // We need the torus to be vertical (standing up), so we rotate it 90 degrees around X or Y.
    
    // Correction: The previous code used `rotate([90,0,0])` before the torus call.
    // If `torus()` creates a flat torus (in XY), rotating 90 deg around X makes it stand up in XZ.
    // This matches the handle orientation (legs in XZ plane).
    
    // Let's redefine torus properly using rotate_extrude
    rotate_extrude($fn=fn) {
        translate([major_r, 0, 0]) {
            circle(r=minor_r, $fn=fn);
        }
    }
}

// Instantiate the design
// The handle is centered at X=0, Y=0.
// The lowest point is Z=0 (bottom of legs).
// The highest point is Z = leg_length + bend_radius + handle_radius.
// Total height = 30 + 20 + 4 = 54mm. Matches authoritative max dimension.
// Total width = 2*bend_radius + handle_diameter = 40 + 8 = 48mm.
// Total depth = handle_diameter = 8mm.

handle_body();
