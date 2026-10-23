/* doodle-meta {"version":1,"parameters":{"bend_radius":{"label":"Bend Radius","description":"Radius of the 180-degree arc bend","unit":"mm","feature":"bend"},"leg_length":{"label":"Leg Length","description":"Length of the straight legs extending in Y","unit":"mm","feature":"legs"},"bar_diameter":{"label":"Bar Diameter","description":"Diameter of the circular cross-section of the handle bar","unit":"mm","feature":"cross_section"}},"features":{"bend":{"kind":"region","label":"Arc Bend","min":[0,0,0],"max":[28.6,8,28.6]},"legs":{"kind":"region","label":"Straight Legs","min":[0,0,0],"max":[28.6,54,8]},"cross_section":{"kind":"region","label":"Cross Section","min":[0,0,0],"max":[8,8,8]}}} */

// Parameters
bend_radius = 20;
leg_length = 31.385978640244247;
bar_diameter = 8.369594304065133;

// Derived dimensions
// The handle is symmetric about the Y axis (depth centerline).
// The bend is a 180-degree arc in the XY plane (Top view).
// The legs extend along the Y axis (depth).
// The cross-section is circular with diameter bar_diameter.
// The arc connects the tops of the legs (at Y = leg_length).
// The arc goes from X = -bend_radius to X = +bend_radius.
// The top of the arc is at Y = leg_length + bend_radius.
// The total depth is leg_length + bend_radius + bar_diameter/2.

module handle_body() {
    // The bend (torus segment)
    // Create a half-torus using rotate_extrude
    // Profile: circle in XY plane, centered at (bend_radius, 0), radius bar_diameter/2
    // Rotate 180 degrees around Z
    // This creates a half-torus in the XY plane, centered at origin, spanning Y > 0.
    // Translate up by leg_length to connect to the legs.
    
    translate([0, 0, leg_length])
        rotate_extrude(angle=180)
            translate([bend_radius, 0])
                circle(r=bar_diameter/2);
    
    // The legs
    // Left leg at X = -bend_radius
    translate([-bend_radius, 0, 0])
        cylinder(h=leg_length, r=bar_diameter/2);
        
    // Right leg at X = +bend_radius
    translate([bend_radius, 0, 0])
        cylinder(h=leg_length, r=bar_diameter/2);
}

handle_body();
