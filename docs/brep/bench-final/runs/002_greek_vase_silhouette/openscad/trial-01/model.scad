/* doodle-meta {"version":1,"parameters":{"height":{"label":"Overall height","description":"Total height of the vase","unit":"mm","feature":"overall_height"},"max_width":{"label":"Maximum width","description":"Diameter at the widest part of the vase","unit":"mm","feature":"max_width"}},"features":{"overall_height":{"kind":"dimension","axis":"z","label":"Overall height"},"max_width":{"kind":"dimension","axis":"x","label":"Maximum width"}}} */

// Parameters
height = 120.0;
max_width = 107.53;

// Derived parameters
max_radius = max_width / 2.0;

// Profile points (radius, z) for the right half of the vase silhouette
// Mapped from normalized coordinates to mm based on the source aspect ratio (~0.9)
// The profile traces the outer boundary from the top rim down to the bottom center.

// 1. Top Rim (Flared)
// Normalized: u ~ 0.84 (right side), v ~ 0.05 (top)
// Radius: 0.84 * max_width / 2? No, u is normalized width. 
// If u=0.5 is center, u=0.84 is 0.34 from center. 
// Wait, the previous code used u * max_width. Let's stick to the visual interpretation of a vase.
// A vase has a flared rim. Let's assume the rim radius is about 40% of max width.
// Let's use explicit proportions for a classic amphora shape to fix the aspect ratio.

// Define key radii as fractions of max_radius
r_rim = max_radius * 0.45;   // Flared rim
r_neck = max_radius * 0.25;  // Narrow neck
r_shoulder = max_radius;     // Widest part (shoulder)
r_base = max_radius * 0.35;  // Foot/base

// Define key heights as fractions of total height
z_rim = height;              // Top
z_neck_bottom = height * 0.75; // Bottom of neck
z_shoulder = height * 0.55;  // Top of shoulder curve (widest)
z_base_top = height * 0.15;  // Top of foot
z_base_bottom = 0.0;         // Bottom

// Construct the 2D profile polygon for rotate_extrude
// The polygon must be in the XZ plane (X=radius, Z=height).
// It must be a closed loop. We trace the outer surface from top to bottom, then close along the axis.

profile_2d = [
    [0.0, z_rim],            // Start at axis, top height
    [r_rim, z_rim],          // Rim outer edge
    [r_neck, z_neck_bottom], // Neck bottom (narrowest)
    [r_shoulder, z_shoulder],// Shoulder (widest)
    [r_base, z_base_top],    // Base top (foot)
    [r_base, z_base_bottom], // Base bottom (foot)
    [0.0, z_base_bottom],    // Bottom center (axis)
    [0.0, z_rim]             // Close loop back to start
];

// Create the vase by revolving the profile
rotate_extrude($fn=100) {
    polygon(profile_2d);
}
