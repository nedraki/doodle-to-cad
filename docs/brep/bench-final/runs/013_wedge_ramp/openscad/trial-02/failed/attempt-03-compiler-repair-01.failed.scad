I'll analyze the issue: the current code extrudes the triangular profile along the X-axis (width), which puts the triangle on the Right view. The spec requires the triangle on the Front view (XZ plane), extruded along Y (depth).

Let me verify the fix:
- **Front view** (looking down Y): should show the triangle in XZ plane → aspect = width/height = 100/32.58 ≈ 3.07 ✓
- **Top view** (looking down Z): should show rectangle in XY plane → aspect = width/depth = 100/62.62 ≈ 1.60 ✓

The fix is to define the polygon in the XZ plane (local x→X, local y→Z) and extrude along Y without rotation.

```openscad
/* doodle-meta {"version":1,"parameters":{"width":{"label":"Overall width","description":"Changes the body width","unit":"mm","feature":"body_width"},"depth":{"label":"Overall depth","description":"Changes the body depth","unit":"mm","feature":"body_depth"},"height":{"label":"Overall height","description":"Changes the body height","unit":"mm","feature":"body_height"}},"features":{"body_width":{"kind":"dimension","axis":"x","label":"Overall width"},"body_depth":{"kind":"dimension","axis":"y","label":"Overall depth"},"body_height":{"kind":"dimension","axis":"z","label":"Overall height"}}} */

// Wedge ramp (lofted incline block)
// Front view (looking down Y): right-angled triangle in XZ plane -> vertical back at X=0,
//   horizontal base at Z=0, sloped hypotenuse descending to the front edge (X=width).
// Top view (looking down Z): rectangular footprint of constant width.
// Constructed by extruding the triangular profile (in the XZ plane) along Y (depth).

width  = 100.0;   // X: width
depth  = 62.62;   // Y: front-to-back depth
height = 32.58;   // Z: height

module wedge() {
    // Triangular profile lies in the XZ plane (local x -> X, local y -> Z),
    // extruded along the Y axis (depth).
    // Base sits on the build plate (Z=0). Vertical back at X=0,
    // sloped hypotenuse descends to the front edge (X=width, Z=0).
    linear_extrude(height = depth, center = false) {
        polygon(points = [
            [0, 0],        // back-bottom  (X=0, Z=0)
            [width, 0],    // front-bottom (X=width, Z=0)
            [0, height]    // back-top     (X=0, Z=height)
        ]);
    }
}

// Single positive body, positioned so the lowest geometry rests at Z=0.
translate([0, 0, 0])
    wedge();
