/* doodle-meta {"version":1,"parameters":{"height":{"label":"Overall height","description":"Total height of the vase","unit":"mm","feature":"overall_height"},"max_width":{"label":"Maximum width","description":"Diameter of the widest part of the vase","unit":"mm","feature":"overall_width"},"wall_thickness":{"label":"Wall thickness","description":"Thickness of the vase shell","unit":"mm","feature":"shell_thickness"}},"features":{"overall_height":{"kind":"dimension","axis":"z","label":"Overall height"},"overall_width":{"kind":"dimension","axis":"x","label":"Maximum width"},"shell_thickness":{"kind":"region","label":"Wall thickness","min":[0,0,0],"max":[{"parameter":"max_width","scale":0.5},{"parameter":"max_width","scale":0.5},{"parameter":"height"}]}}} */

// Parameters
height = 120.0;
max_width = 107.53;
wall_thickness = 3.0;

// Derived parameters
max_radius = max_width / 2.0;
eps = 0.01;

// Scaling factor to correct height from 112.51 to 120.0
// The original profile had max height ~112.51mm.
// Scale factor = 120.0 / 112.51 ≈ 1.0666
scale_z = height / 112.51;

// Profile points (radius, height) derived from normalized coordinates
// Original normalized points (u, v) mapped to (r, h) before scaling:
// Top Right: [0.8404, 0.0494] -> r=36.60, h=114.07 -> shifted h=112.51
// Neck:      [0.6985, 0.3012] -> r=21.34, h=83.86  -> shifted h=82.30
// Belly:     [0.971, 0.7636]  -> r=50.65, h=28.37  -> shifted h=26.81
// Lower:     [0.9157, 0.9039] -> r=44.70, h=11.53  -> shifted h=9.97
// Bottom:    [0.4984, 0.987]  -> r=0,     h=1.56   -> shifted h=0.00

// Apply scaling to Z coordinates to reach 120mm total height
// Radii are kept proportional to maintain aspect ratio relative to the new height.

module vase_outer() {
    polygon([
        [0, 0],
        [44.70, 9.97 * scale_z],
        [50.65, 26.81 * scale_z],
        [21.34, 82.30 * scale_z],
        [36.60, 112.51 * scale_z],
        [0, 112.51 * scale_z]
    ]);
}

module vase_inner() {
    // Inner profile offset by wall_thickness
    // Ensure radii don't go negative
    polygon([
        [0, wall_thickness],
        [max(0, 44.70 - wall_thickness), 9.97 * scale_z],
        [max(0, 50.65 - wall_thickness), 26.81 * scale_z],
        [max(0, 21.34 - wall_thickness), 82.30 * scale_z],
        [max(0, 36.60 - wall_thickness), 112.51 * scale_z],
        [0, 112.51 * scale_z]
    ]);
}

// Main design
difference() {
    // Outer solid
    rotate_extrude(angle=360, $fn=64) {
        vase_outer();
    }
    
    // Inner cavity
    rotate_extrude(angle=360, $fn=64) {
        vase_inner();
    }
}
