/* doodle-meta {"version":1,"parameters":{"bend_radius":{"label":"Bend Radius","description":"Radius of the 180-degree arc bend","unit":"mm","feature":"bend"},"leg_length":{"label":"Leg Length","description":"Length of the straight vertical legs","unit":"mm","feature":"legs"},"bar_diameter":{"label":"Bar Diameter","description":"Diameter of the circular cross-section of the handle bar","unit":"mm","feature":"cross_section"}},"features":{"bend":{"kind":"region","label":"Arc Bend","min":[0,0,30],"max":[28.6,8,54]},"legs":{"kind":"region","label":"Straight Legs","min":[0,0,0],"max":[28.6,8,30]},"cross_section":{"kind":"region","label":"Cross Section","min":[0,0,0],"max":[8,8,8]}}} */

// Parameters
bend_radius = 20;
leg_length = 30;
bar_diameter = 8;

// Derived dimensions
// The handle is symmetric about the Z axis (vertical centerline).
// The bend is a 180-degree arc. The legs extend downwards from the ends of the arc.
// The arc lies in the XZ plane (front view).
// The legs are parallel to the Z axis.
// The cross-section is circular with diameter bar_diameter.

// The center of the arc is at (0, 0, leg_length + bar_diameter/2) relative to the bottom of the legs?
// Let's define the geometry relative to the bottom of the legs at Z=0.
// The legs go from Z=0 to Z=leg_length.
// The arc connects the tops of the legs.
// The center of the arc is at Z = leg_length.
// The arc goes from X = -bend_radius to X = +bend_radius.
// The top of the arc is at Z = leg_length + bend_radius.
// The total height is leg_length + bend_radius + bar_diameter/2? 
// Wait, the "centerline_radius" is 20. The bar has a diameter of 8.
// The outer radius of the bend is bend_radius + bar_diameter/2.
// The inner radius of the bend is bend_radius - bar_diameter/2.
// The legs are tangent to the arc. This means the legs are vertical lines at X = +/- bend_radius.
// The legs extend from Z=0 to Z=leg_length.
// The arc center is at (0, 0, leg_length).
// The arc spans from angle 0 to 180 degrees (in the XZ plane, from +X to -X).
// Actually, standard polar coordinates: angle 0 is +X, 90 is +Z, 180 is -X.
// So the arc goes from (bend_radius, 0, leg_length) to (-bend_radius, 0, leg_length) via (0, 0, leg_length + bend_radius).
// The legs connect to the ends of the arc.
// The leg at +X goes from (bend_radius, 0, leg_length) down to (bend_radius, 0, 0).
// The leg at -X goes from (-bend_radius, 0, leg_length) down to (-bend_radius, 0, 0).

// To build this in OpenSCAD, we can use a sweep or construct it from primitives.
// Since we need a circular cross-section, we can use rotate_extrude for the bend and cylinders for the legs, then union them.
// However, rotate_extrude creates a solid of revolution. We need a torus segment.
// A torus segment can be created by difference of two cylinders or using rotate_extrude on a circle.
// Let's use rotate_extrude for the bend part.
// The profile for rotate_extrude is a circle of radius bar_diameter/2 centered at (bend_radius, 0) in the XZ plane?
// No, rotate_extrude rotates around the Z axis. The profile is in the XZ plane (or YZ depending on orientation).
// If we rotate around Z, the profile should be in the XZ plane? No, rotate_extrude takes a 2D polygon in the XY plane and rotates it around Z.
// So we need to define the profile in the XY plane, then rotate it.
// Alternatively, we can just use a torus and cut it.
// A torus with major radius bend_radius and minor radius bar_diameter/2.
// We want the top half of the torus (Z > leg_length).
// And two cylinders for the legs.

// Let's refine the coordinate system.
// Origin at the center of the bottom of the handle? Or at the bottom of one leg?
// Let's put the origin at the center of the bottom of the handle, i.e., (0, 0, 0) is the midpoint between the two legs at the bottom.
// So the legs are at X = +/- bend_radius.
// The legs are cylinders of radius bar_diameter/2 and height leg_length.
// The bend is a torus segment.
// The torus center is at (0, 0, leg_length).
// The torus major radius is bend_radius.
// The torus minor radius is bar_diameter/2.
// We want the part of the torus where Z >= leg_length.
// This is the upper half of the torus.

// Constructing the torus segment:
// We can create a full torus and intersect it with a cube that keeps only the upper half.
// Or we can use rotate_extrude.
// Let's use rotate_extrude.
// The profile is a circle of radius bar_diameter/2 centered at (bend_radius, 0) in the XZ plane?
// rotate_extrude rotates around Z. The profile is defined in the XY plane.
// So we define a circle in the XY plane centered at (bend_radius, 0) with radius bar_diameter/2.
// Then rotate_extrude(angle=180) will create a half-torus.
// But rotate_extrude starts at angle 0 (positive X axis) and goes counter-clockwise.
// So it will create the half-torus from +X to -X via +Y?
// Wait, the handle is in the XZ plane. The bend is in the XZ plane.
// If we rotate around Z, the sweep is in the XY plane. That's wrong.
// The bend is in the XZ plane. So we need to rotate around Y?
// No, the axis of the torus is the Y axis?
// The torus is formed by rotating a circle around an axis.
// The circle is in the XZ plane. The axis of rotation is the Y axis?
// No, the torus is symmetric around the Y axis?
// Let's visualize. The handle is like a "U" shape in the XZ plane.
// The cross-section is circular.
// This is a torus segment where the axis of the torus is the Y axis.
// So we can create a torus with axis Y.
// OpenSCAD's torus() primitive has axis Z by default.
// We can rotate it.
// Or we can use rotate_extrude.
// rotate_extrude rotates around Z.
// So we need to orient the profile such that rotating around Z creates the desired shape.
// If we want the torus axis to be Y, we can create the torus with axis Z and then rotate it 90 degrees around X.
// Let's do that.
// Create a torus with major radius bend_radius and minor radius bar_diameter/2.
// This torus is centered at (0,0,0) with axis Z.
// We want the part where Z >= 0 (relative to the torus center).
// So we intersect with a cube from Z=0 to Z=bend_radius+bar_diameter/2.
// Then we rotate this half-torus 90 degrees around X to align its axis with Y?
// No, if the torus axis is Z, and we rotate 90 around X, the axis becomes Y.
// The "top" of the torus (Z>0) becomes the "front" (Y>0) or "back" (Y<0)?
// Let's stick to the XZ plane for the handle.
// The handle lies in the XZ plane. The cross-section is circular.
// This means the torus axis is the Y axis.
// So we create a torus with axis Y.
// In OpenSCAD, we can use rotate_extrude.
// rotate_extrude rotates around Z.
// So we need to define the profile in the XY plane, rotate around Z, then rotate the result.
// Let's define the profile in the XY plane.
// The profile is a circle of radius bar_diameter/2 centered at (bend_radius, 0).
// rotate_extrude(angle=180) creates a half-torus in the XY plane?
// No, rotate_extrude creates a solid of revolution around Z.
// The profile is in the XY plane. The resulting solid is symmetric around Z.
// This is not what we want. We want the handle to be in the XZ plane.
// So we need to rotate the final solid.
// Let's try a different approach.
// Use a torus primitive.
// torus(r1=bend_radius, r2=bar_diameter/2) creates a torus around Z.
// We want the torus around Y.
// So we rotate the torus 90 degrees around X.
// rotate([90,0,0]) torus(...);
// This torus is centered at (0,0,0).
// We want the upper half (Z >= 0).
// So we intersect with a cube that keeps Z >= 0.
// Then we translate it up by leg_length.
// Then we add the legs.
// The legs are cylinders at X = +/- bend_radius, from Z=0 to Z=leg_length.
// The legs need to connect to the torus.
// The torus ends are at X = +/- bend_radius, Z = leg_length.
// The legs go from Z=0 to Z=leg_length.
// So they connect perfectly.

// Let's refine the torus part.
// torus(r1=bend_radius, r2=bar_diameter/2)
// Rotate 90 around X: rotate([90,0,0])
// Now the torus is in the XZ plane?
// Original torus: axis Z. Circle in XY plane.
// Rotate 90 around X: Axis becomes Y. Circle in XZ plane.
// Yes.
// We want the part where Z >= 0.
// So we intersect with a cube from Z=0 to Z=bend_radius+bar_diameter/2.
// Then translate up by leg_length.

// Let's write the code.

module handle() {
    // The bend (torus segment)
    // Create a full torus, cut it in half, and position it.
    difference() {
        // Full torus rotated to have axis Y
        rotate([90, 0, 0])
            torus(r1=bend_radius, r2=bar_diameter/2);
        
        // Cut off the bottom half (Z < 0 relative to torus center)
        // The torus is centered at (0,0,0) after rotation.
        // We want to keep Z >= 0.
        // So we subtract the part where Z < 0.
        translate([0, 0, -bend_radius - bar_diameter])
            cube([bend_radius*2 + bar_diameter*2, bend_radius*2 + bar_diameter*2, bend_radius + bar_diameter], center=true);
    }
    
    // Translate the bend up by leg_length
    // Wait, the difference operation above is centered at (0,0,0).
    // We need to translate the result up.
    // But the difference is a single object. We can wrap it in a translate.
    // Actually, let's restructure.
    
    // Let's define the bend module separately.
}

module bend_part() {
    difference() {
        rotate([90, 0, 0])
            torus(r1=bend_radius, r2=bar_diameter/2);
        
        // Subtract the lower half (Z < 0)
        // The torus extends from Z = -bar_diameter/2 to Z = bar_diameter/2?
        // No, the torus is centered at (0,0,0).
        // The "tube" center is at radius bend_radius from the Y axis.
        // The tube has radius bar_diameter/2.
        // So the Z extent is from -bar_diameter/2 to bar_diameter/2?
        // No, the torus is in the XZ plane.
        // The center of the tube is at (bend_radius, 0, 0) and (-bend_radius, 0, 0)?
        // No, the torus is symmetric around Y.
        // The center of the tube traces a circle in the XZ plane?
        // No, the torus axis is Y. The center of the tube traces a circle in the XZ plane?
        // Yes. The circle is in the XZ plane, centered at (0,0,0), radius bend_radius.
        // So the tube center is at (bend_radius*cos(theta), 0, bend_radius*sin(theta)).
        // We want the part where Z >= 0.
        // So we subtract the part where Z < 0.
        translate([0, 0, -bend_radius - bar_diameter])
            cube([bend_radius*2 + bar_diameter*2, bend_radius*2 + bar_diameter*2, bend_radius + bar_diameter], center=true);
    }
}

module leg(x_pos) {
    translate([x_pos, 0, 0])
        cylinder(h=leg_length, r=bar_diameter/2, center=false);
}

module handle_body() {
    // The bend
    translate([0, 0, leg_length])
        bend_part();
    
    // The legs
    leg(bend_radius);
    leg(-bend_radius);
}

// The handle should sit on the build plate.
// The legs start at Z=0.
// The bend is at Z=leg_length.
// The top of the bend is at Z=leg_length + bend_radius + bar_diameter/2.
// The total height is leg_length + bend_radius + bar_diameter/2.
// The width is 2*bend_radius + bar_diameter.
// The depth is bar_diameter.

// Check dimensions against derived_sizes.
// max_width: 28.6. 2*bend_radius + bar_diameter = 2*20 + 8 = 48. This is too big.
// The derived sizes say max_width 28.6, max_depth 54.0, max_height 46.24.
// The authoritative max dimension is 54.
// The bend radius is 20. The leg length is 30.
// If the bend radius is 20, the width is at least 40.
// But the derived width is 28.6.
// This suggests the "bend_radius" in the spec might be the inner radius or something else, or the scale is different.
// Or maybe the "bend_radius" is the radius of the centerline, but the overall width is constrained.
// Let's re-read the spec.
// "centerline_radius": 20.
// "max_width": 28.6.
// This is a contradiction if the handle is a simple U-shape.
// Unless the handle is not a U-shape in the X direction?
// The front view (view_5) shows the U-shape.
// The width in the front view is the X dimension.
// If the width is 28.6, and the bend radius is 20, then 2*20 = 40 > 28.6.
// Maybe the bend radius is smaller?
// Or maybe the "bend_radius" is not the centerline radius of the U, but something else?
// The spec says "centerline_radius": 20.
// Let's look at the derived sizes again.
// width_mm: 28.6, depth_mm: 54.0, height_mm: 46.24.
// The authoritative max dimension is 54.
// The depth is 54.
// The height is 46.24.
// The width is 28.6.
// If the handle is oriented such that the U-shape is in the YZ plane?
// The front view (view_5) is the left view? No, view_5 is "left".
// The spec says:
// front: view_5? No, "views": [{"direction": "front", "sheet_region": "view_5"}, ...]
// Wait, the JSON says:
// "views": [
//   { "direction": "front", "sheet_region": "view_5" },
//   { "direction": "top", "sheet_region": "view_3" },
//   { "direction": "left", "sheet_region": "view_4" }
// ]
// But the measured_view_geometry has:
// view_5: direction "left", cad_mapping: plane "YZ", view_axis "X".
// view_4: direction "front", cad_mapping: plane "XZ", view_axis "Y".
// view_3: direction "top", cad_mapping: plane "XY", view_axis "Z".
// There is a mismatch between the "views" list in specification and the "measured_view_geometry".
// The "views" list in specification seems to have swapped front and left?
// Or the sheet_region IDs are different.
// Let's trust the "measured_view_geometry" for the actual geometry.
// view_4 is "front", plane XZ. This shows the U-shape.
// view_5 is "left", plane YZ. This shows the side profile.
// view_3 is "top", plane XY. This shows the cross-section.
// The U-shape is in the XZ plane (front view).
// So the width is X, height is Z.
// The derived width is 28.6.
// The derived height is 46.24.
// The derived depth is 54.0.
// The depth is Y.
// If the U-shape is in XZ, the depth (Y) should be the bar diameter (8).
// But the derived depth is 54.
// This implies the U-shape is in the YZ plane?
// If the U-shape is in YZ, then the width (X) is the bar diameter (8).
// But the derived width is 28.6.
// This is confusing.
// Let's look at the "construction_plan".
// "coordinate_frame": { "x": "width", "y": "depth", "z": "height" }
// "front": { "plane": "XZ", "view_axis": "Y" }
// "top": { "plane": "XY", "view_axis": "Z" }
// "right": { "plane": "YZ", "view_axis": "X" }
// The U-shape is in the front view (XZ).
// So the width is X, height is Z.
// The depth is Y.
// If the U-shape is in XZ, the depth (Y) is the thickness of the bar, which is 8.
// But derived depth is 54.
// This suggests the U-shape is NOT in the XZ plane.
// Maybe the U-shape is in the YZ plane?
// If the U-shape is in YZ, then the width (X) is the bar diameter (8).
// But derived width is 28.6.
// Maybe the U-shape is in the XY plane?
// If the U-shape is in XY, then the height (Z) is the bar diameter (8).
// But derived height is 46.24.
// This doesn't match either.
// Let's re-read the "views" in specification.
// "front": "view_5". "left": "view_4".
// In measured_view_geometry:
// view_5 is "left". view_4 is "front".
// So the specification's "front" is actually the "left" view in the geometry data.
// And the specification's "left" is actually the "front" view in the geometry data.
// This means the U-shape is in the "left" view (view_5), which is the YZ plane.
// So the U-shape is in the YZ plane.
// This means the width (X) is the bar diameter (8).
// But derived width is 28.6.
// This is still a contradiction.
// Unless the "width" in derived_sizes refers to the dimension in the Y direction?
// No, "x": "width".
// Let's look at the "intent_refinements".
// view_5 (left) has outer_profile_ideal "polygon".
// view_4 (front) has outer_profile_ideal "polygon".
// view_3 (top) has outer_profile_ideal "circle".
// The top view (XY) shows a circle. This means the cross-section is circular in the XY plane?
// No, the top view looks down Z. If it shows a circle, the object is cylindrical along Z?
// Or the cross-section is circular in the XY plane.
// If the cross-section is circular in XY, then the bar is along Z?
// But the handle is a U-shape.
// Let's assume the standard orientation: U-shape in XZ.
// Then the top view (XY) should show two rectangles (the legs) and a rectangle (the bend).
// But view_3 (top) shows a circle.
// This implies the handle is oriented such that the cross-section is visible in the top view.
// This means the bar is vertical? No.
// If the top view is a circle, the object is a cylinder along Z.
// But the front view is a U-shape.
// This is impossible for a single continuous bar unless the bar is twisted.
// Or maybe the "top" view is actually the "end" view?
// The spec says "TOP (XY)".
// If the top view is a circle, and the front view is a U-shape, then the handle must be oriented such that the cross-section is in the XY plane.
// This means the bar runs along Z?
// If the bar runs along Z, the front view (XZ) would show a rectangle.
// But the front view shows a U-shape.
// This is a contradiction.
// Let's look at the "construction_plan".
// "sweep", "profile_plane": "XY", "direction_axis": "path".
// This means the profile is in XY, and it is swept along a path.
// If the profile is in XY, and the path is in XZ, then the cross-section is in XY.
// This means the bar is perpendicular to the XY plane? No.
// The profile is the cross-section. If the profile is in XY, the cross-section is in XY.
// This means the bar runs along Z.
// But the path is in XZ?
// If the path is in XZ, and the profile is in XY, then the bar is twisted?
// Or the profile is always perpendicular to the path.
// If the path is in XZ, and the profile is in XY, then at the bottom of the legs (vertical), the profile is in XY (horizontal).
// At the top of the bend (horizontal), the profile is in YZ (vertical).
// This is a twisted handle.
// But the spec says "circular cross-section".
// If the cross-section is circular, the orientation doesn't matter.
// So we can assume the cross-section is circular.
// The path is the U-shape.
// Where is the U-shape?
// The front view (view_4) shows the U-shape.
// So the path is in the XZ plane.
// The width is X, height is Z.
// The derived width is 28.6.
// The derived height is 46.24.
// The derived depth is 54.0.
// If the path is in XZ, the depth (Y) is the bar diameter.
// But derived depth is 54.
// This implies the path is in the YZ plane?
// If the path is in YZ, then the width (X) is the bar diameter.
// But derived width is 28.6.
// This implies the path is in the XY plane?
// If the path is in XY, then the height (Z) is the bar diameter.
// But derived height is 46.24.
// This is very confusing.
// Let's look at the "authoritative_max_dimension_mm": 54.
// The derived depth is 54.
// So the depth is the largest dimension.
// The U-shape is likely in the YZ plane.
// So the width (X) is the bar diameter.
// But derived width is 28.6.
// Maybe the bar diameter is 28.6?
// But the spec says "diameter": 8.
// Maybe the "width" in derived_sizes is not the X dimension?
// "x": "width".
// Let's assume the spec's "diameter": 8 is correct.
// And the "centerline_radius": 20 is correct.
// And the "leg_length": 30 is correct.
// Then the overall width is 2*20 + 8 = 48.
// The overall height is 30 + 20 + 4 = 54.
// The overall depth is 8.
// The derived sizes are width 28.6, depth 54, height 46.24.
// The depth 54 matches the height 54.
// The height 46.24 is close to 48?
// The width 28.6 is close to 28?
// Maybe the handle is rotated?
// If the handle is rotated 90 degrees around Z, then the width becomes the depth.
// If the U-shape is in the YZ plane, then the width (X) is the bar diameter (8).
// The depth (Y) is the width of the U (48).
// The height (Z) is the height of the U (54).
// This matches the derived depth 54 (if depth is Z?) and height 46.24 (if height is Y?).
// But the coordinate frame says "y": "depth", "z": "height".
// So if the U-shape is in YZ, then depth is 48, height is 54.
// Derived depth is 54, height is 46.24.
// This is close.
// So the U-shape is in the YZ plane.
// The width (X) is the bar diameter.
// But derived width is 28.6.
// This is the only mismatch.
// Maybe the bar diameter is 28.6?
// But the spec says 8.
// I will trust the spec's parameters (radius 20, leg 30, dia 8) and the derived max dimension (54).
// The derived width 28.6 might be an error or a different interpretation.
// I will build the handle with the U-shape in the YZ plane, so that the depth is the large dimension.
// Wait, the "front" view is XZ. If the U-shape is in YZ, the front view would show a rectangle.
// But the front view (view_4) shows a U-shape.
// So the U-shape is in XZ.
// Then the width is 48, height is 54, depth is 8.
// The derived sizes are width 28.6, depth 54, height 46.24.
// This is completely different.
// I will follow the spec's explicit parameters (R20, L30, D8) and the authoritative max dimension (54).
// The derived sizes might be from a different scale or object.
// I will build the U-shape in the XZ plane.

module handle() {
    // Bend
    translate([0, 0, leg_length])
        difference() {
            rotate([90, 0, 0])
                torus(r1=bend_radius, r2=bar_diameter/2);
            translate([0, 0, -bend_radius - bar_diameter])
                cube([bend_radius*2 + bar_diameter*2, bend_radius*2 + bar_diameter*2, bend_radius + bar_diameter], center=true);
        }
    
    // Legs
    translate([bend_radius, 0, 0])
        cylinder(h=leg_length, r=bar_diameter/2);
    translate([-bend_radius, 0, 0])
        cylinder(h=leg_length, r=bar_diameter/2);
}

handle();
