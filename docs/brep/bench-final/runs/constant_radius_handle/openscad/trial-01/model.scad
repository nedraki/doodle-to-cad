/* doodle-meta {"version":1,"parameters":{"arc_radius":{"label":"Arc Radius","description":"Radius of the semicircular bend","unit":"mm","feature":"arc_bend"},"leg_length":{"label":"Leg Length","description":"Length of the straight legs extending from the arc","unit":"mm","feature":"straight_legs"},"rod_diameter":{"label":"Rod Diameter","description":"Diameter of the circular cross-section","unit":"mm","feature":"cross_section"}},"features":{"arc_bend":{"kind":"region","label":"Arc Bend","min":[0,0,0],"max":[{"parameter":"arc_radius","scale":2,"offset":0},{"parameter":"rod_diameter","scale":1,"offset":0},{"parameter":"arc_radius","scale":1,"offset":0}]},"straight_legs":{"kind":"region","label":"Straight Legs","min":[{"parameter":"arc_radius","scale":-1,"offset":0},{"parameter":"rod_diameter","scale":0.5,"offset":0},{"parameter":"arc_radius","scale":1,"offset":0}],"max":[{"parameter":"arc_radius","scale":1,"offset":0},{"parameter":"leg_length","scale":1,"offset":0},{"parameter":"arc_radius","scale":1,"offset":0}]}}} */

// Parameters
arc_radius = 20.0;
leg_length = 33.75;
rod_diameter = 9;

// Derived constants
rod_radius = rod_diameter / 2;
total_height = arc_radius + leg_length;

// Modules
module handle_body() {
    // 1. Semicircular Arc (Top)
    // Centered at Z = arc_radius, spanning Z from 0 to 2*arc_radius
    // Rotated to lie in XZ plane (axis along Y)
    translate([0, 0, arc_radius])
        rotate([90, 0, 0])
            difference() {
                cylinder(h = rod_diameter, r = arc_radius + rod_radius, center = true);
                cylinder(h = rod_diameter + 1, r = arc_radius - rod_radius, center = true);
            }

    // 2. Left Leg
    // Extends from Z=0 to Z=arc_radius at X = -arc_radius
    translate([-arc_radius, 0, arc_radius / 2])
        cylinder(h = arc_radius, r = rod_radius, center = true);

    // 3. Right Leg
    // Extends from Z=0 to Z=arc_radius at X = +arc_radius
    translate([arc_radius, 0, arc_radius / 2])
        cylinder(h = arc_radius, r = rod_radius, center = true);
}

// Main Geometry
// The handle is symmetric about X=0.
// The legs extend downwards. To ensure the part sits on the build plate (Z=0),
// we translate the entire assembly up by the rod radius.
// The lowest point of the legs (cylinder bottom) will be at Z = -rod_radius relative to the leg center.
// Leg center is at Z = arc_radius/2.
// So bottom is at arc_radius/2 - rod_radius.
// We want bottom at 0. So translate Z by -(arc_radius/2 - rod_radius) = rod_radius - arc_radius/2.
// Wait, let's re-evaluate the leg placement.
// If I place the leg cylinder with center=true at Z=arc_radius/2, it spans [0, arc_radius].
// The arc is centered at Z=arc_radius. It spans [0, 2*arc_radius] in Z (if we consider the torus-like shape).
// Actually, the arc module above creates a torus segment centered at Z=arc_radius.
// The torus spans Z from arc_radius - (arc_radius+rod_radius) to arc_radius + (arc_radius+rod_radius)?
// No, the cylinder in the arc module is rotated 90 deg around X.
// Original cylinder axis is Z. Rotated 90 around X -> Axis is Y.
// Height is rod_diameter. So it spans Y from -rod_radius to +rod_radius.
// The radius is arc_radius + rod_radius.
// So in XZ plane, it's a ring of outer radius R_out and inner radius R_in.
// Centered at (0, arc_radius).
// Lowest point of the arc ring is at Z = arc_radius - (arc_radius + rod_radius) = -rod_radius.
// Highest point is at Z = arc_radius + (arc_radius + rod_radius) = 2*arc_radius + rod_radius.
// The legs are cylinders along Z.
// Left leg at X=-arc_radius. Spans Z from 0 to arc_radius (if center=true at arc_radius/2).
// The leg connects to the arc at Z=arc_radius.
// The arc at X=-arc_radius has its center at Z=arc_radius.
// The leg top is at Z=arc_radius. The arc center is at Z=arc_radius.
// The leg is a cylinder of radius rod_radius.
// The arc at X=-arc_radius is a circle of radius rod_radius centered at (X=-arc_radius, Z=arc_radius).
// So the leg (cylinder along Z) and the arc (torus segment) intersect perfectly at the tangent point.
// The lowest point of the leg is Z=0.
// The lowest point of the arc is Z = -rod_radius.
// So the whole assembly currently spans Z from -rod_radius to 2*arc_radius + rod_radius.
// To sit on build plate, we need to shift up by rod_radius.

translate([0, 0, rod_radius])
    handle_body();
