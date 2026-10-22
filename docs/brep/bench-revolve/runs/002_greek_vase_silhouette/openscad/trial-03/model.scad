/* doodle-meta {"version":1,"parameters":{"height":{"label":"Overall height","description":"Total height of the vase from base to rim","unit":"mm","feature":"overall_height"},"max_width":{"label":"Maximum width","description":"Diameter of the widest part of the vase body","unit":"mm","feature":"body_width"}},"features":{"overall_height":{"kind":"dimension","axis":"z","label":"Overall height"},"body_width":{"kind":"dimension","axis":"x","label":"Maximum width"}}} */

// Parameters
height = 120.0;
max_width = 107.53;

// Derived parameters
max_radius = max_width / 2.0;
$fn = 64;

// Profile points for the vase silhouette (X, Z)
// X is the radius from the center axis, Z is the height
// Points are ordered from bottom to top
profile_points = [
    [0, 0],           // Bottom center
    [max_radius * 0.4, 0], // Base edge
    [max_radius * 0.45, height * 0.05], // Base curve start
    [max_radius * 0.8, height * 0.15],  // Lower body
    [max_radius, height * 0.35],        // Max width (shoulder/belly)
    [max_radius * 0.9, height * 0.55],  // Upper body
    [max_radius * 0.4, height * 0.75],  // Neck base
    [max_radius * 0.3, height * 0.85],  // Neck
    [max_radius * 0.35, height * 0.95], // Neck flare start
    [max_radius * 0.5, height],         // Rim outer
    [max_radius * 0.45, height],        // Rim inner
    [max_radius * 0.25, height * 0.95], // Inner neck
    [max_radius * 0.2, height * 0.85],  // Inner neck
    [max_radius * 0.3, height * 0.75],  // Inner neck base
    [max_radius * 0.7, height * 0.55],  // Inner upper body
    [max_radius * 0.8, height * 0.35],  // Inner max width
    [max_radius * 0.6, height * 0.15],  // Inner lower body
    [max_radius * 0.35, height * 0.05], // Inner base curve
    [max_radius * 0.3, 0],              // Inner base edge
    [0, 0]            // Close profile
];

// Module to create the vase body by revolving the profile
module vase_body() {
    // Create the 2D profile polygon
    // The polygon is defined in the XZ plane (X is radius, Z is height)
    // rotate_extrude expects points in the XZ plane where X >= 0
    polygon(profile_points);
}

// Main design
// The vase is created by revolving the 2D profile around the Z axis
// The profile is defined in the XZ plane
// rotate_extrude rotates around the Z axis by default

// To ensure the vase sits on the build plate (Z=0), the profile starts at Z=0.
// The profile is closed at the bottom (points at Z=0) and open at the top (rim).
// However, rotate_extrude requires a closed polygon for a solid.
// The provided profile_points form a closed loop representing the cross-section of the vase wall.
// The outer boundary goes up, the inner boundary comes down.

// Let's refine the profile to be a single closed loop representing the solid cross-section.
// Outer path: Bottom -> Up -> Top Rim
// Inner path: Top Rim -> Down -> Bottom
// This creates a "C" shape or a closed loop if we connect the ends.

// Revised Profile for a solid vase (closed loop):
// Start at bottom center (0,0), go out to base edge, up the outer wall, across the rim, down the inner wall, back to center.
// Actually, for rotate_extrude, we just need the profile in the XZ plane.
// If we want a hollow vase, the profile should be the cross-section of the material.
// If we want a solid vase (as per "solid (watertight) for 3D printing" in uncertainties, though "top is left open" in notes),
// the notes say "top is left open to represent the vase opening".
// But "solid (watertight)" usually implies no internal voids unless specified.
// A vase with an opening is not watertight in the sense of being a sealed container, but it is a watertight mesh (manifold).
// The profile should define the material.

// Let's define the profile as the outline of the material cross-section.
// Outer contour:
// (0,0) -> (base_r, 0) -> ... -> (rim_outer_r, H)
// Inner contour (if hollow):
// (rim_inner_r, H) -> ... -> (inner_base_r, 0) -> (0,0)

// Given the "solid" note in uncertainties but "open top" in notes, I will model it as a solid body with a recessed top to simulate the opening, or just a solid revolve of the outer silhouette if "solid" means no hollow interior.
// However, a "Greek vase" typically has an opening. The "solid" note might refer to the mesh being watertight (no holes in the mesh surface), not that the interior is filled.
// I will create a hollow vase with a defined wall thickness.

wall_thickness = 3.0;

// Generate outer and inner profiles
outer_profile = [
    [0, 0],
    [max_radius * 0.4, 0],
    [max_radius * 0.45, height * 0.05],
    [max_radius * 0.8, height * 0.15],
    [max_radius, height * 0.35],
    [max_radius * 0.9, height * 0.55],
    [max_radius * 0.4, height * 0.75],
    [max_radius * 0.3, height * 0.85],
    [max_radius * 0.35, height * 0.95],
    [max_radius * 0.5, height]
];

inner_profile = [
    [max_radius * 0.5 - wall_thickness, height],
    [max_radius * 0.35 - wall_thickness, height * 0.95],
    [max_radius * 0.3 - wall_thickness, height * 0.85],
    [max_radius * 0.4 - wall_thickness, height * 0.75],
    [max_radius * 0.9 - wall_thickness, height * 0.55],
    [max_radius - wall_thickness, height * 0.35],
    [max_radius * 0.8 - wall_thickness, height * 0.15],
    [max_radius * 0.45 - wall_thickness, height * 0.05],
    [max_radius * 0.4 - wall_thickness, 0],
    [0, 0]
];

// Combine into a single closed polygon for rotate_extrude
// The polygon must be closed.
// Path: Outer (bottom to top) -> Inner (top to bottom) -> Close
combined_profile = concat(outer_profile, inner_profile);

// Ensure the polygon is valid for rotate_extrude
// rotate_extrude expects the polygon to be in the XZ plane, with X >= 0.
// The points are (x, z).

module vase() {
    rotate_extrude(angle=360) {
        polygon(combined_profile);
    }
}

// Instantiate the vase
vase();
