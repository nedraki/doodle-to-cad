/* doodle-meta {"version":1,"parameters":{"width":{"label":"Overall width","description":"Changes the body width","unit":"mm","feature":"body_width"},"depth":{"label":"Overall depth","description":"Changes the body depth","unit":"mm","feature":"body_depth"},"height":{"label":"Overall height","description":"Changes the body height","unit":"mm","feature":"body_height"}},"features":{"body_width":{"kind":"dimension","axis":"x","label":"Overall width"},"body_depth":{"kind":"dimension","axis":"y","label":"Overall depth"},"body_height":{"kind":"dimension","axis":"z","label":"Overall height"}}} */

// Wedge ramp (lofted incline block)
// Front view (looking down Y): right-angled triangle -> vertical back at Y=0,
//   horizontal base at Z=0, sloped hypotenuse descending to the front edge (Y=depth).
// Top view (looking down Z): rectangular footprint of constant width.
// Constructed by extruding the triangular profile (in the YZ plane) along X (width).

width  = 100.0;   // X: width
depth  = 62.62;   // Y: front-to-back depth
height = 32.58;   // Z: height

module wedge() {
    // Triangular profile lies in the YZ plane (local x -> Y, local y -> Z),
    // extruded along the X axis (width).
    // Base sits on the build plate (Z=0). Vertical back at Y=0,
    // sloped hypotenuse descends to the front edge (Y=depth, Z=0).
    rotate([0, 90, 0])
        linear_extrude(height = width, center = false) {
            polygon(points = [
                [0, 0],        // back-bottom  (Y=0, Z=0)
                [depth, 0],    // front-bottom (Y=depth, Z=0)
                [0, height]    // back-top     (Y=0, Z=height)
            ]);
        }
}

// Single positive body, positioned so the lowest geometry rests at Z=0.
translate([0, 0, 0])
    wedge();
