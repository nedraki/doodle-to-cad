/* doodle-meta {"version":1,"parameters":{"width":{"label":"Overall width","description":"Changes the body width","unit":"mm","feature":"body_width"},"height":{"label":"Overall height","description":"Changes the body height","unit":"mm","feature":"body_height"},"thickness":{"label":"Plate thickness","description":"Changes the plate thickness","unit":"mm","feature":"body_thickness"},"hole_diameter":{"label":"Hole diameter","description":"Changes the diameter of the vent holes","unit":"mm","feature":"hole_grid"},"hole_spacing_x":{"label":"Horizontal hole spacing","description":"Changes the horizontal distance between hole centers","unit":"mm","feature":"hole_grid"},"hole_spacing_y":{"label":"Vertical hole spacing","description":"Changes the vertical distance between hole centers","unit":"mm","feature":"hole_grid"}},"features":{"body_width":{"kind":"dimension","axis":"x","label":"Overall width"},"body_height":{"kind":"dimension","axis":"z","label":"Overall height"},"body_thickness":{"kind":"dimension","axis":"y","label":"Plate thickness"},"hole_grid":{"kind":"region","label":"Hole Grid","min":[{"parameter":"width","scale":0.34},{"parameter":"thickness","scale":0.0,"offset":0.0},{"parameter":"height","scale":0.3673}],"max":[{"parameter":"width","scale":0.664},{"parameter":"thickness","scale":1.0,"offset":0.0},{"parameter":"height","scale":0.6287}]}}} */

width = 100.0;
height = 61.39;
thickness = 3.0;
hole_diameter = 8.0;
hole_spacing_x = 16.25;
hole_spacing_y = 16.25;

eps = 0.01;

module vent_grille() {
    difference() {
        // Main plate body
        cube([width, thickness, height]);
        
        // Subtract 3x3 grid of holes
        // Center of grid is at (width/2, height/2)
        // Holes are cut along Y axis (front view holes)
        for (i = [-1:1]) {
            for (j = [-1:1]) {
                translate([
                    width/2 + i * hole_spacing_x,
                    -eps,
                    height/2 + j * hole_spacing_y
                ]) {
                    rotate([90, 0, 0]) {
                        cylinder(h = thickness + 2*eps, d = hole_diameter, center = true);
                    }
                }
            }
        }
    }
}

vent_grille();
