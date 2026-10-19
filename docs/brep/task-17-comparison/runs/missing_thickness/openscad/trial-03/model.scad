/* doodle-meta {"version":1,"parameters":{"overall_length":{"label":"Overall Length","description":"Changes the overall length of the tray along the X axis","unit":"mm","feature":"body_length"},"overall_width":{"label":"Overall Width","description":"Changes the overall width of the tray along the Y axis","unit":"mm","feature":"body_width"},"overall_height":{"label":"Overall Height","description":"Changes the overall height of the tray along the Z axis","unit":"mm","feature":"body_height"},"wall_thickness":{"label":"Wall Thickness","description":"Changes the thickness of the tray walls and floor","unit":"mm","feature":"wall_thickness"},"corner_radius":{"label":"Corner Radius","description":"Changes the radius of the rounded corners","unit":"mm","feature":"corner_radius"}},"features":{"body_length":{"kind":"dimension","axis":"x","label":"Overall Length"},"body_width":{"kind":"dimension","axis":"y","label":"Overall Width"},"body_height":{"kind":"dimension","axis":"z","label":"Overall Height"},"wall_thickness":{"kind":"region","label":"Wall Thickness","min":[0,0,0],"max":[{"parameter":"wall_thickness","scale":1,"offset":0},{"parameter":"overall_width","scale":0.5,"offset":0},{"parameter":"overall_height","scale":1,"offset":0}]},"corner_radius":{"kind":"region","label":"Corner Radius","min":[{"parameter":"overall_length","scale":0.5,"offset":0},{"parameter":"overall_width","scale":0.5,"offset":0},0],"max":[{"parameter":"overall_length","scale":1,"offset":0},{"parameter":"overall_width","scale":1,"offset":0},{"parameter":"overall_height","scale":1,"offset":0}]}}} */

// Top-level parameters (user-editable)
overall_length = 60.0;
overall_width = 40.0;
overall_height = 20.0;
wall_thickness = 2.0;
corner_radius = 6.0;

// Derived parameters (not user-editable)
inner_length = overall_length - 2 * wall_thickness;
inner_width = overall_width - 2 * wall_thickness;
inner_height = overall_height - wall_thickness;
inner_radius = corner_radius - wall_thickness;

// Helper module for a rounded rectangle centered at origin in XY plane
module rounded_rect(l, w, r, h) {
    // Ensure radius is valid
    r_safe = min(r, l/2, w/2);
    
    // Create the shape using hull of 4 cylinders and a central box
    // Or simpler: offset approach isn't available in standard lib without libraries.
    // Standard approach: Hull of 4 cylinders at corners + box? 
    // Actually, standard OpenSCAD way for rounded rect is often hull of 4 cylinders.
    // But for a solid extrusion, we can use a polygon or hull.
    // Let's use hull of 4 cylinders for the base shape.
    
    // Corner positions
    x = l/2 - r_safe;
    y = w/2 - r_safe;
    
    hull() {
        translate([x, y, 0]) cylinder(h=h, r=r_safe, center=true);
        translate([-x, y, 0]) cylinder(h=h, r=r_safe, center=true);
        translate([-x, -y, 0]) cylinder(h=h, r=r_safe, center=true);
        translate([x, -y, 0]) cylinder(h=h, r=r_safe, center=true);
    }
}

// Main design
difference() {
    // Outer body
    translate([0, 0, overall_height/2]) {
        rounded_rect(overall_length, overall_width, corner_radius, overall_height);
    }
    
    // Inner cavity (subtractive)
    // The cavity starts at Z = wall_thickness and goes up to Z = overall_height
    // Height of cavity = overall_height - wall_thickness
    // Center of cavity Z = wall_thickness + (overall_height - wall_thickness)/2
    translate([0, 0, wall_thickness + inner_height/2]) {
        rounded_rect(inner_length, inner_width, inner_radius, inner_height + 1); // +1 to ensure clean cut at top
    }
}
