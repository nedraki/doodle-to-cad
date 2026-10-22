/* doodle-meta {"version":1,"parameters":{"hex_radius":{"label":"Hexagon Circumradius","description":"Radius from center to vertex of the hexagonal cross-section","unit":"mm","feature":"hex_profile"},"height":{"label":"Prism Height","description":"Extrusion height of the hexagonal prism along Z","unit":"mm","feature":"prism_height"}},"features":{"hex_profile":{"kind":"region","label":"Hexagonal Cross-Section","min":[0,0,0],"max":[{"parameter":"hex_radius","scale":2},{"parameter":"hex_radius","scale":1.732},{"parameter":"height"}]},"prism_height":{"kind":"dimension","axis":"z","label":"Prism Height"}}} */

// Parameters
hex_radius = 35.0; // Circumradius (distance from center to vertex)
height = 61.49;    // Height of the prism (Z-axis)

// Derived dimensions
// For a regular hexagon with circumradius R:
// Width (flat-to-flat) = R * sqrt(3)
// Depth (vertex-to-vertex) = 2 * R
// The front view constrains X (width) and Z (height).
// The right view constrains Y (depth) and Z (height).
// Given max_width = 70, max_depth = 69.51, max_height = 61.49.
// If we orient the hexagon with vertices along X and Y axes (pointy-top in XY plane):
// X extent = 2 * R. If 2*R = 70, R = 35.
// Y extent = R * sqrt(3) = 35 * 1.732 = 60.62. This doesn't match depth 69.51 well.
// If we orient with flats along X and Y axes (flat-top in XY plane):
// X extent = R * sqrt(3). If R*sqrt(3) = 70, R = 40.4.
// Y extent = 2 * R = 80.8. Too big.
// Let's look at the "measured_view_geometry" and "derived_sizes".
// derived_sizes: width_mm=70, depth_mm=69.51, height_mm=61.49.
// The object is described as a "Hex prism handle".
// The front view shows the hexagonal profile. The right view shows the side profile.
// Both views show a hexagon-like shape.
// If the front view is the hexagonal face, then the prism is extruded along Y?
// No, standard convention: Front view looks down Y. Top view looks down Z. Right view looks down X.
// If Front view shows the hexagon, the hexagon is in the XZ plane?
// But the construction plan says: "extrude ... profile_plane: XY ... direction_axis: Z".
// This implies the hexagon is in the XY plane (Top view would show it).
// However, the "views" list says:
// Front view constrains "Cross-sectional profile (XY plane)". This is contradictory to standard projection where Front is XZ.
// Let's re-read carefully: "Front view ... constrains Cross-sectional profile (XY plane)".
// Usually, if Front view shows the cross-section, the object is lying on its side or the view definition is non-standard.
// BUT, the construction plan explicitly says: `profile_plane: "XY"`, `direction_axis: "Z"`.
// This means the hexagon is in the XY plane, and we extrude up Z.
// So the Top view (looking down Z) would show the hexagon.
// The Front view (looking down Y) would show the side of the prism.
// The Right view (looking down X) would show the side of the prism.
// The provided "measured_view_geometry" has `view_1` as "front" and `view_2` as "right".
// Both `view_1` and `view_2` have `outer_profile` with 6 vertices (hexagon).
// If the Front view (looking down Y) shows a hexagon, then the hexagon is in the XZ plane.
// If the Right view (looking down X) shows a hexagon, then the hexagon is in the YZ plane.
// A solid that is a hexagon in Front (XZ) and Hexagon in Right (YZ) is likely a hexagonal prism oriented along Y? Or a complex shape?
// Wait, the `construction_plan` says `profile_plane: "XY"`. This contradicts the view descriptions if the views show hexagons.
// Let's look at `intent_refinements`. It says `outer_profile_ideal: "circle"` for both views.
// And `specification` says "Hex prism handle".
// And `uncertainties` say "The specific orientation of the hexagon... is inferred from the front view geometry."
// If the Front view shows the hexagon, the hexagon is in the XZ plane.
// If the Right view shows the hexagon, the hexagon is in the YZ plane.
// This implies the object might be a hexagonal prism along the Y axis?
// If it's a prism along Y, the Front view (XZ) shows the hexagon. The Right view (YZ) shows the rectangle side.
// But the Right view ALSO shows a hexagon in the measured data.
// This suggests the object is a hexagonal prism where the axis is along... ?
// If Front (XZ) is hex and Right (YZ) is hex, it's not a simple prism along one axis.
// However, `construction_plan` is authoritative for generation: `extrude ... profile_plane: "XY" ... direction_axis: "Z"`.
// This means we create a hexagon in XY and extrude along Z.
// If we do this, the Top view (XY) is the hexagon.
// The Front view (XZ) is a rectangle (or trapezoid depending on orientation).
// The Right view (YZ) is a rectangle.
// The measured views showing hexagons might be misinterpreted or the "Front" view in the data actually corresponds to the Top view in standard terms, or the object is rotated.
// Given the conflict, I will follow the `construction_plan` which is the explicit instruction for geometry generation: Extrude a hexagon from XY along Z.
// The dimensions provided are:
// max_width (X) = 70
// max_depth (Y) = 69.51
// max_height (Z) = 61.49
// If the hexagon is in XY, its extents are X and Y.
// A regular hexagon has width and depth related by sqrt(3).
// If oriented with vertices on X and Y axes (pointy-top):
// X_max = 2*R, Y_max = R*sqrt(3).
// If oriented with flats on X and Y axes (flat-top):
// X_max = R*sqrt(3), Y_max = 2*R.
// Let's check the ratios.
// 70 / 69.51 ≈ 1.007. Almost square.
// A regular hexagon is never square (ratio is 1.732 or 0.577).
// This implies the "hexagon" might be irregular, or the views are not showing the true cross-section, or the "hexagon" is actually a circle (intent_refinements says "circle").
// `intent_refinements` says `outer_profile_ideal: "circle"`.
// If it's a circle, X=70, Y=69.51, Z=61.49.
// But the object name is "Hex prism handle".
// And `specification` says "Regular hexagon shape".
// If it's a regular hexagon, the width/depth ratio must be sqrt(3) or 1/sqrt(3).
// The measured 70/69.51 is very close to 1. This is contradictory for a regular hexagon.
// However, `derived_sizes` says `width_mm: 70.0`, `depth_mm: 69.51`.
// Maybe the hexagon is rotated?
// If we assume the `construction_plan` is correct (Extrude XY along Z), and the intent is a hexagon, but the measurements are nearly square...
// Perhaps the "Front" view in the data is actually the Top view?
// If View 1 (Front) is the hexagon, and View 2 (Right) is the hexagon...
// Let's trust the `construction_plan` for the topology: Hexagon in XY, extruded along Z.
// I will define the hexagon to fit the X and Y bounds.
// Since a regular hexagon cannot have X≈Y, I will prioritize the "Hex prism" description and use a regular hexagon that fits the larger dimension, or scale it.
// Actually, looking at `uncertainties`: "The exact height of the prism is inferred to be equal to the width...".
// Let's assume the standard "Hex Nut" style orientation: Flat sides parallel to X and Y? No, that gives ratio sqrt(3).
// Let's assume the hexagon is defined by the circumradius R.
// If we want to fit 70x69.51, we can't do it with a regular hexagon.
// I will use the `intent_refinements` hint "circle" as a fallback for shape regularization if the hexagon doesn't fit, BUT the prompt says "model ideal_shape forms exactly... circle -> cylinder".
// Wait, `intent_refinements` says `outer_profile_ideal: "circle"`.
// If I model a cylinder, it fits 70x69.51 easily.
// But the object is "Hex prism handle".
// I will model a hexagonal prism. I will orient it such that the vertices align with the axes to maximize the fit, or use the average.
// Let's use a regular hexagon with circumradius R = 35 (so diameter 70).
// If vertices are on X axis: X extent = 70. Y extent = 35*sqrt(3) = 60.6.
// If flats are on X axis: X extent = 35*sqrt(3) = 60.6. Y extent = 70.
// The measured depth is 69.51. This is very close to 70.
// This suggests the hexagon might be "squashed" or it's actually a cylinder.
// Given the conflict between "Hex prism" and "Circle" intent + Square-ish measurements, and the instruction "model ideal_shape forms exactly... circle -> cylinder", I will follow the `intent_refinements` which overrides raw tracing.
// The `intent_refinements` explicitly says `outer_profile_ideal: "circle"`.
// Therefore, I will generate a cylinder.
// Dimensions:
// Diameter X = 70.0
// Diameter Y = 69.51
// Height Z = 61.49
// Since it's a cylinder, X and Y diameters should be equal. I'll use the max or average.
// Max is 70.0.
// I will create a cylinder with d=70, h=61.49.

module hex_prism_handle() {
    // Based on intent_refinements: outer_profile_ideal is "circle".
    // Based on derived_sizes: width=70, depth=69.51, height=61.49.
    // We model a cylinder to satisfy the "circle" intent and the near-square footprint.
    
    // Center the cylinder on Z=0 to Z=height
    translate([0, 0, height/2]) {
        cylinder(h=height, d=width, center=true);
    }
}

// Parameters for the cylinder
width = 70.0;
height = 61.49;

hex_prism_handle();
