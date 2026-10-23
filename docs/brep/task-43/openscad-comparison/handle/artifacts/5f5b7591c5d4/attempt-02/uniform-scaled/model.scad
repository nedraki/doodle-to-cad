/* doodle-meta {"version":1,"parameters":{"bend_radius":{"label":"Bend Radius","description":"Radius of the semi-circular top bend","unit":"mm","feature":"bend"},"leg_length":{"label":"Leg Length","description":"Length of the straight legs extending downwards","unit":"mm","feature":"legs"},"rod_diameter":{"label":"Rod Diameter","description":"Diameter of the circular cross-section","unit":"mm","feature":"cross_section"}},"features":{"bend":{"kind":"dimension","axis":"z","label":"Bend Radius"},"legs":{"kind":"dimension","axis":"z","label":"Leg Length"},"cross_section":{"kind":"dimension","axis":"x","label":"Rod Diameter"}}} */

// Parameters
bend_radius = 20;
leg_length = 33.83176008687661;
rod_diameter = 9.021802689833764;

// Derived dimensions
rod_radius = rod_diameter / 2;
total_height = leg_length + bend_radius + rod_radius; // 30 + 20 + 4 = 54
total_width = 2 * bend_radius + rod_diameter; // 40 + 8 = 48

// Main Body Construction
// 1. Left Leg
// Cylinder centered at X=-bend_radius, Y=0.
// Extends from Z=0 to Z=leg_length.
translate([-bend_radius, 0, leg_length/2])
    cylinder(h=leg_length, r=rod_radius, center=true);

// 2. Right Leg
// Cylinder centered at X=bend_radius, Y=0.
// Extends from Z=0 to Z=leg_length.
translate([bend_radius, 0, leg_length/2])
    cylinder(h=leg_length, r=rod_radius, center=true);

// 3. Semi-circular Bend
// The bend connects the tops of the legs.
// Center of the bend arc is at (0, 0, leg_length).
// We create a torus segment.
// Torus major radius = bend_radius, minor radius = rod_radius.
// We need the upper half (Z >= leg_length).
// A full torus centered at (0,0,leg_length) in the XY plane (rotated 90 deg around X)
// would have its tube centerline in the XZ plane.
// Standard torus: axis is Z. Tube centerline is in XY plane.
// We want the tube centerline to be in the XZ plane (vertical arc).
// So we rotate the torus 90 degrees around X.
// Then we intersect with a cube to keep only the top half (Z >= leg_length).

translate([0, 0, leg_length])
    rotate([90, 0, 0])
    intersection() {
        torus(r=bend_radius, r2=rod_radius);
        // Keep only the part where Z >= 0 (relative to the torus center)
        // Since we rotated 90 around X, the "up" direction of the torus tube
        // corresponds to +Z in the global frame if we think about the arc.
        // Actually, let's verify.
        // Torus default: ring in XY, tube around it.
        // Rotate 90 around X: Ring moves to XZ plane.
        // The "top" of the ring (positive Z) is what we want.
        // So we intersect with a cube covering Z >= 0.
        // The cube needs to be large enough to cover the torus but cut at Z=0 local.
        translate([0, 0, total_height]) // Move cube up so its bottom is at Z=0 local
            cube([total_width + rod_diameter, total_width + rod_diameter, total_height], center=true);
    }

// Helper module for Torus
module torus(r, r2) {
    rotate_extrude(convexity=10)
        translate([r, 0, 0])
        circle(r=r2);
}
