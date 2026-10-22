/* doodle-meta {"version":1,"parameters":{"height":{"label":"Overall height","description":"Total height of the vase","unit":"mm","feature":"overall_height"},"max_width":{"label":"Overall width","description":"Maximum diameter of the vase body","unit":"mm","feature":"overall_width"}},"features":{"overall_height":{"kind":"dimension","axis":"z","label":"Overall height"},"overall_width":{"kind":"dimension","axis":"x","label":"Overall width"}}} */

height = 120.0;
max_width = 107.53;

// Derived parameters
max_radius = max_width / 2.0;

// Profile points from measured view geometry
// u is normalized 0..1 across width, v is normalized 0..1 down height
// X = (u - 0.5) * max_width
// Z = (1 - v) * height
// We take the right half (u >= 0.5) to define the radius profile for rotation

// Raw points from polygon_view_normalized (right side only, sorted by Z descending)
// [u, v] -> [X, Z]
// [0.8404, 0.0494] -> X = (0.8404-0.5)*107.53 = 36.63, Z = (1-0.0494)*120 = 114.07
// [0.6985, 0.3012] -> X = (0.6985-0.5)*107.53 = 21.31, Z = (1-0.3012)*120 = 83.86
// [0.971, 0.7636]  -> X = (0.971-0.5)*107.53 = 50.58, Z = (1-0.7636)*120 = 28.37
// [0.9157, 0.9039] -> X = (0.9157-0.5)*107.53 = 44.64, Z = (1-0.9039)*120 = 11.53
// [0.4984, 0.987]  -> X = (0.4984-0.5)*107.53 = -0.17 ~ 0, Z = (1-0.987)*120 = 1.56

// To create a watertight solid via rotate_extrude, we need a closed polygon in the XZ plane.
// The polygon must start at the axis (X=0) at the bottom, go out to the profile, up to the top, and back to the axis.
// We also need to ensure the bottom is flat at Z=0.

// Define the profile points for the right half (X >= 0)
// We add a point at the bottom center (0,0) and top center (0, height) to close the shape against the axis.
// Note: The measured bottom point is at Z=1.56, but we want the vase to sit on the build plate (Z=0).
// We will extend the bottom to Z=0.

profile_points = [
    [0, 0],           // Bottom center on axis
    [44.64, 0],       // Bottom edge (extrapolated from 11.53 to 0)
    [50.58, 28.37],   // Widest point
    [21.31, 83.86],   // Neck
    [36.63, 114.07],  // Rim
    [36.63, height],  // Top edge
    [0, height]       // Top center on axis
];

module vase_profile() {
    polygon(points=profile_points);
}

module vase_body() {
    rotate_extrude(angle=360) {
        vase_profile();
    }
}

// Main design
vase_body();
