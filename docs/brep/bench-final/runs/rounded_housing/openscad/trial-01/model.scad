/* doodle-meta {"version":1,"parameters":{"width":{"label":"Overall width","description":"Changes the body width","unit":"mm","feature":"body_width"},"depth":{"label":"Overall depth","description":"Changes the body depth","unit":"mm","feature":"body_depth"},"height":{"label":"Overall height","description":"Changes the body height","unit":"mm","feature":"body_height"},"fillet_radius":{"label":"Fillet radius","description":"Radius of the vertical corner fillets","unit":"mm","feature":"corner_fillet"}},"features":{"body_width":{"kind":"dimension","axis":"x","label":"Overall width"},"body_depth":{"kind":"dimension","axis":"y","label":"Overall depth"},"body_height":{"kind":"dimension","axis":"z","label":"Overall height"},"corner_fillet":{"kind":"region","label":"Vertical corner fillets","min":[{"parameter":"width","scale":0.5,"offset":0},{"parameter":"depth","scale":0.5,"offset":0},0],"max":[{"parameter":"width","scale":0.5,"offset":0},{"parameter":"depth","scale":0.5,"offset":0},{"parameter":"height","scale":1,"offset":0}]}}} */

// Overall dimensions (mm)
width  = 90;   // drawing: top view "80x50", front view width 80mm
depth  = 56.25;   // drawing: top view "80x50", right view depth 50mm
height = 33.75;   // drawing: front/right view height 30mm
fillet_radius = 6.0; // drawing: "4 corners: R6"

// Implementation constants (not user-editable)
$fn = 48;

// Rounded-rectangle profile in the XY plane, centred on the origin.
module rounded_rect(w, d, r) {
    hull() {
        translate([ (w/2 - r),  (d/2 - r), 0]) circle(r = r);
        translate([-(w/2 - r),  (d/2 - r), 0]) circle(r = r);
        translate([ (w/2 - r), -(d/2 - r), 0]) circle(r = r);
        translate([-(w/2 - r), -(d/2 - r), 0]) circle(r = r);
    }
}

// Solid block: rounded-rect profile extruded along Z, sitting on the build plate.
module housing_block() {
    linear_extrude(height = height)
        rounded_rect(width, depth, fillet_radius);
}

housing_block();
