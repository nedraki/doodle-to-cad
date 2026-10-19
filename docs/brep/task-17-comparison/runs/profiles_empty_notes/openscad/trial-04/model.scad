/* doodle-meta {"version":1,"parameters":{"plate_width":{"label":"Overall width","description":"Changes the body width","unit":"mm","feature":"body_width"},"plate_depth":{"label":"Overall depth","description":"Changes the body depth","unit":"mm","feature":"body_depth"},"plate_thickness":{"label":"Overall thickness","description":"Changes the body thickness","unit":"mm","feature":"body_thickness"},"notch_width":{"label":"Notch width","description":"Changes the width of the top notch","unit":"mm","feature":"notch"},"notch_depth":{"label":"Notch depth","description":"Changes the depth of the top notch","unit":"mm","feature":"notch"},"fillet_radius":{"label":"Fillet radius","description":"Changes the radius of the top-right corner fillet","unit":"mm","feature":"fillet"},"hole_diameter":{"label":"Hole diameter","description":"Changes the diameter of the through hole","unit":"mm","feature":"hole"},"hole_x":{"label":"Hole X position","description":"Changes the X position of the hole from the left edge","unit":"mm","feature":"hole"},"hole_y":{"label":"Hole Y position","description":"Changes the Y position of the hole from the front edge","unit":"mm","feature":"hole"}},"features":{"body_width":{"kind":"dimension","axis":"x","label":"Overall width"},"body_depth":{"kind":"dimension","axis":"y","label":"Overall depth"},"body_thickness":{"kind":"dimension","axis":"z","label":"Overall thickness"},"notch":{"kind":"region","label":"Top Notch","min":[{"parameter":"plate_width","scale":0.5,"offset":-10},{"parameter":"plate_depth","scale":1.0,"offset":0},0],"max":[{"parameter":"plate_width","scale":0.5,"offset":10},{"parameter":"plate_depth","scale":1.0,"offset":0},{"parameter":"plate_thickness","scale":1.0,"offset":0}]},"fillet":{"kind":"region","label":"Top-Right Fillet","min":[{"parameter":"plate_width","scale":1.0,"offset":-6},{"parameter":"plate_depth","scale":1.0,"offset":-6},0],"max":[{"parameter":"plate_width","scale":1.0,"offset":0},{"parameter":"plate_depth","scale":1.0,"offset":0},{"parameter":"plate_thickness","scale":1.0,"offset":0}]},"hole":{"kind":"region","label":"Through Hole","min":[{"parameter":"hole_x","scale":1.0,"offset":-4},{"parameter":"hole_y","scale":1.0,"offset":-4},0],"max":[{"parameter":"hole_x","scale":1.0,"offset":4},{"parameter":"hole_y","scale":1.0,"offset":4},{"parameter":"plate_thickness","scale":1.0,"offset":0}]}}} */

// Top-level parameters
plate_width = 60;
plate_depth = 40;
plate_thickness = 6;
notch_width = 20;
notch_depth = 10;
fillet_radius = 6;
hole_diameter = 8;
hole_x = 12;
hole_y = 15;

// Derived constants (not user-editable)
eps = 0.01;

// Main design
difference() {
    // Positive body: extruded profile with fillet
    translate([0, 0, 0])
        linear_extrude(height = plate_thickness)
            difference() {
                // Base rectangle
                square([plate_width, plate_depth]);
                // Fillet at top-right corner (X=plate_width, Y=plate_depth)
                // Remove the corner square
                translate([plate_width - fillet_radius, plate_depth - fillet_radius])
                    square([fillet_radius + eps, fillet_radius + eps]);
                // Add back the quarter circle
                translate([plate_width - fillet_radius, plate_depth - fillet_radius])
                    circle(r = fillet_radius);
            }
    
    // Subtractive cutters
    
    // 1. Top notch (centered on top edge, Y=plate_depth)
    // Notch spans X from (plate_width/2 - notch_width/2) to (plate_width/2 + notch_width/2)
    // Notch spans Y from (plate_depth - notch_depth) to (plate_depth + eps)
    translate([plate_width/2 - notch_width/2, plate_depth - notch_depth, -eps])
        cube([notch_width, notch_depth + eps, plate_thickness + 2*eps]);
    
    // 2. Through hole (Ø8mm at X=12, Y=15 from bottom-left)
    // Hole axis is along Z (through the plate thickness)
    translate([hole_x, hole_y, -eps])
        cylinder(h = plate_thickness + 2*eps, d = hole_diameter, center = false);
}
