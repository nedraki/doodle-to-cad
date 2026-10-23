/* doodle-meta {"version":1,"parameters":{"height":{"label":"Overall height","description":"Total height of the vase from base to rim","unit":"mm","feature":"overall_height"},"max_width":{"label":"Max width","description":"Maximum diameter of the vase body","unit":"mm","feature":"body_width"}},"features":{"overall_height":{"kind":"dimension","axis":"z","label":"Overall height"},"body_width":{"kind":"dimension","axis":"x","label":"Max width"}}} */

// Parameters
height = 120.0;
max_width = 107.53;

// Derived parameters
radius_max = max_width / 2.0;
radius_rim = radius_max * 0.45; // Rim is narrower than max width
radius_neck = radius_max * 0.35;
radius_base = radius_max * 0.40;

// Profile points for the vase silhouette (right half, from bottom to top)
// Coordinates are [radius, z]
// Based on the measured polygon and typical Greek vase proportions
profile_points = [
    [radius_base, 0],           // Base outer edge
    [radius_base * 0.8, 5],     // Base inner curve start
    [radius_neck * 0.9, 15],    // Lower body/foot transition
    [radius_max * 0.6, 30],     // Lower body
    [radius_max, 60],           // Max width (shoulder/belly)
    [radius_max * 0.8, 85],     // Upper body
    [radius_neck, 100],         // Neck
    [radius_rim, 110],          // Neck to rim transition
    [radius_rim * 1.1, 115],    // Rim flare
    [radius_rim * 1.1, height], // Rim top outer
    [radius_rim * 0.9, height], // Rim top inner
    [radius_rim * 0.9, 115],    // Rim inner flare
    [radius_neck * 0.9, 100],   // Neck inner
    [radius_max * 0.7, 85],     // Upper body inner
    [radius_max * 0.9, 60],     // Max width inner
    [radius_max * 0.5, 30],     // Lower body inner
    [radius_neck * 0.8, 15],    // Lower body inner
    [radius_base * 0.7, 5],     // Base inner curve end
    [radius_base * 0.7, 0]      // Base inner edge
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
