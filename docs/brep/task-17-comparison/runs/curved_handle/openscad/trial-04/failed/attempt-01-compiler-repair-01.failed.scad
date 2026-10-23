/* doodle-meta {"version":1,"parameters":{"rod_diameter":{"label":"Rod Diameter","description":"Diameter of the circular cross-section of the handle","unit":"mm","feature":"cross_section"},"bend_radius":{"label":"Bend Radius","description":"Centerline radius of the U-bend","unit":"mm","feature":"bend"},"leg_length":{"label":"Leg Length","description":"Length of the straight legs extending from the bend","unit":"mm","feature":"legs"}},"features":{"cross_section":{"kind":"dimension","axis":"z","label":"Rod Diameter"},"bend":{"kind":"region","label":"Bend","min":[0,0,0],"max":[{"parameter":"rod_diameter","scale":1,"offset":0},{"parameter":"bend_radius","scale":2,"offset":0},{"parameter":"rod_diameter","scale":1,"offset":0}]},"legs":{"kind":"region","label":"Legs","min":[0,0,0],"max":[{"parameter":"rod_diameter","scale":1,"offset":0},{"parameter":"bend_radius","scale":2,"offset":0},{"parameter":"leg_length","scale":1,"offset":0}]}}} */

// Parameters
rod_diameter = 8;
bend_radius = 20;
leg_length = 30;

// Derived constants
rod_radius = rod_diameter / 2;
$fn = 64;

// The handle is oriented with legs pointing down (Z-) and the bend at the top (Z+).
// To sit on the build plate (Z=0), the lowest point (leg tips) must be at Z=0.
// The total height is leg_length + bend_radius + rod_radius.
// We translate the geometry so the bottom of the legs is at Z=0.

module handle() {
    // 1. The Bend (Semicircular Arc)
    // The bend is a torus segment. 
    // Center of the torus is at (0, 0, leg_length + rod_radius) relative to the leg bottom?
    // Let's define the path centerline first.
    // Legs go from Z=0 to Z=leg_length.
    // The bend connects the tops of the legs.
    // The center of the bend arc is at Z = leg_length.
    // The arc goes from X = -bend_radius to X = +bend_radius? 
    // No, standard U-handle:
    // Legs are parallel. Distance between leg centerlines is 2 * bend_radius.
    // Left leg centerline: X = -bend_radius. Right leg centerline: X = +bend_radius.
    // Bend center: (0, 0, leg_length).
    // The bend is a half-torus (180 degrees) in the XZ plane? 
    // Wait, the "top" view constrains the U-shape. Usually, the U-shape is in the XY plane (horizontal) or XZ (vertical).
    // The prompt says: "top view ... defining the bend radius and leg spacing".
    // "front view ... showing the arch height and leg length".
    // If the front view shows the arch, the U-shape is in the XZ plane (vertical).
    // So the legs are vertical (along Z). The bend is in the XZ plane.
    
    // Let's re-read carefully:
    // "top view ... defining the bend radius and leg spacing" -> This implies the U-shape is visible from the top?
    // If the U-shape is visible from the top, the legs are horizontal (along Y or X) and the bend is horizontal.
    // BUT "front view ... showing the arch height and leg length".
    // If the front view shows the arch, the U-shape is in the XZ plane.
    // If the U-shape is in the XZ plane, the top view would show two parallel lines (the legs) and the bend would be a line or rectangle depending on orientation.
    // The "top" view description says "Planar geometry of the handle (U-shape)". This strongly suggests the U-shape lies in the XY plane (horizontal).
    // If the U-shape is in the XY plane, the legs are along Y (depth) or X (width).
    // Let's look at the dimensions:
    // max_width (X) = 16.73
    // max_depth (Y) = 26.81
    // max_height (Z) = 54.0
    // The "left" view constrains "Cross-sectional profile (circular) and height of the legs".
    // If the legs are vertical (Z), the left view (YZ plane) would show the legs' length.
    // If the legs are horizontal (Y), the left view (YZ plane) would show the legs' length along Y.
    
    // Let's assume the standard "Handle" orientation where it sits on a surface.
    // Usually, handles are mounted on a door or drawer.
    // If it's a drawer pull, the legs go into the drawer (Y axis) and the grip is parallel to the drawer face (X axis).
    // In this case:
    // Legs are along Y.
    // Bend is in the XY plane (horizontal).
    // Height (Z) is just the rod diameter? No, max_height is 54.
    // This contradicts the "drawer pull" model if the height is 54mm.
    
    // Alternative: It's a vertical handle, like on a cabinet door or a tool.
    // Legs are vertical (Z).
    // Bend is at the top.
    // Front view (XZ) shows the U-shape.
    // Top view (XY) shows the legs as circles/rectangles?
    // The prompt says "top view ... defining the bend radius and leg spacing".
    // If the U-shape is in XZ, the top view (XY) would show the width (X) and depth (Y).
    // The "leg spacing" is the distance between legs (X). The "bend radius" is visible in the front view (XZ).
    // Why would the top view define the bend radius?
    // Maybe the U-shape is in the XY plane (horizontal), and the "height" of 54mm is the length of the legs?
    // If legs are along Z, and U-shape is in XY, then the legs are vertical.
    // Front view (XZ) would show the legs as vertical lines. The bend would be a horizontal line at the top.
    // This doesn't show the "arch".
    
    // Let's look at the "Left" view: "Cross-sectional profile (circular) and height of the legs".
    // Left view is YZ. If legs are along Z, this view shows the legs' length (Z) and the rod diameter (Y).
    // This fits "height of the legs".
    
    // Let's look at the "Front" view: "Elevation view showing the arch height and leg length".
    // Front view is XZ. If the U-shape is in XZ, this view shows the arch.
    // This fits "arch height".
    
    // So the U-shape is in the XZ plane.
    // Legs are along Z.
    // Bend is in XZ plane.
    // Why does the "Top" view define "bend radius and leg spacing"?
    // In the top view (XY), we see the projection of the U-shape.
    // The legs are vertical (Z), so they project to points/lines in XY? No, they project to their cross-sections?
    // No, if legs are along Z, their projection on XY is just the rod diameter circle (or square).
    // The "leg spacing" is the distance between the legs in X. This is visible in the top view (X extent).
    // The "bend radius" determines the X extent of the bend. This is visible in the top view (X extent).
    // So the top view constrains the X-dimensions (width).
    
    // Dimensions:
    // Width (X) = 16.73 mm.
    // Depth (Y) = 26.81 mm.
    // Height (Z) = 54.0 mm.
    
    // If the U-shape is in XZ:
    // The width of the handle is determined by the bend radius and rod diameter.
    // Total Width = 2 * (bend_radius + rod_radius).
    // 16.73 = 2 * (bend_radius + 4).
    // 8.365 = bend_radius + 4.
    // bend_radius = 4.365 mm.
    // This seems small for a "bend radius" parameter if the default was 20.
    // Let's check the other orientation.
    
    // If the U-shape is in XY (horizontal):
    // Legs are along Z (vertical).
    // Bend is in XY plane.
    // Front view (XZ) shows legs (vertical lines) and the bend (horizontal line at top).
    // This does NOT show the "arch".
    
    // If the U-shape is in YZ (side view):
    // Legs are along Z.
    // Bend is in YZ plane.
    // Front view (XZ) shows legs (vertical lines).
    // Left view (YZ) shows the arch.
    // But the prompt says "Front view ... showing the arch".
    
    // Conclusion: The U-shape is in the XZ plane.
    // The "Top" view description might be slightly misleading or referring to the planar extent (width).
    // Or, the "Top" view in the drawing is actually the Front view?
    // The prompt says: "The 'top' view in the drawing actually depicts the front elevation of the handle (the U-shape)".
    // Ah! The generation notes say: "The 'top' view in the drawing actually depicts the front elevation of the handle (the U-shape)".
    // This means the view labeled "top" in the metadata is actually showing the U-shape.
    // And the view labeled "front" might be something else?
    // Let's trust the "generation_notes" and "views" descriptions.
    // View 5 (Left) constrains "Cross-sectional profile (circular) and height of the legs".
    // View 1 (Front) constrains "Elevation view showing the arch height and leg length".
    // View 4 (Top) constrains "Planar geometry of the handle (U-shape)".
    
    // If View 4 (Top) shows the U-shape, then the U-shape is in the XY plane.
    // If the U-shape is in XY, the legs are along Z?
    // If legs are along Z, the "height" is the leg length.
    // Max Height (Z) = 54.
    // Max Width (X) = 16.73.
    // Max Depth (Y) = 26.81.
    
    // If U-shape is in XY:
    // The bend is in XY.
    // The legs extend along Z.
    // Front View (XZ) would show the legs as vertical rectangles. The bend would be a horizontal bar at the top.
    // This matches "Elevation view showing ... leg length".
    // Does it show "arch height"? The "arch" is the bend. In XZ, the bend is a flat bar.
    // Unless the "arch height" refers to the Z-height of the bend?
    
    // Let's look at the "Left" view (YZ).
    // If U-shape is in XY, the Left view (YZ) shows the legs (vertical) and the bend (horizontal).
    // It constrains "Cross-sectional profile (circular)".
    
    // Let's reconsider the "Top view depicts front elevation" note.
    // If the "Top" view (View 4) shows the U-shape, then the U-shape is in the XY plane.
    // This means the handle is lying flat? Or the legs are vertical?
    // If legs are vertical (Z), and U-shape is in XY, then the handle is like a "U" standing up.
    // The "arch" is the curved part at the top.
    // The "Front" view (XZ) sees the side of the U.
    // The "Left" view (YZ) sees the side of the U.
    // The "Top" view (XY) sees the U-shape itself.
    
    // This fits the "Top view ... defining the bend radius and leg spacing" perfectly.
    // The bend radius is in the XY plane.
    // The leg spacing is in the XY plane.
    
    // So:
    // U-shape is in XY plane.
    // Legs are along Z.
    // Bend is at the top (Z = leg_length).
    // The bend connects the two legs.
    
    // Dimensions:
    // Height (Z) = 54.0 mm. This is the total height.
    // Leg Length = 30 mm (from features).
    // Bend Radius = 20 mm (from features).
    // Rod Diameter = 8 mm.
    
    // Let's check consistency.
    // If legs are 30mm long, and bend is at the top.
    // The bend center is at Z = 30.
    // The top of the bend is at Z = 30 + rod_radius = 34.
    // Total height = 34 mm.
    // But max_height is 54 mm.
    // Contradiction.
    
    // Maybe the legs are longer?
    // Feature "leg_left" length = 30.
    // Feature "leg_right" length = 30.
    // Feature "bend" centerline_radius = 20.
    
    // If the U-shape is in XZ (vertical):
    // Legs are along Z.
    // Bend is in XZ.
    // Total Height = Leg Length + Bend Radius + Rod Radius?
    // If legs are 30, and bend radius is 20.
    // Height = 30 + 20 + 4 = 54.
    // This matches max_height = 54.0 exactly!
    
    // So the U-shape IS in the XZ plane.
    // The "Top view" description in the prompt ("defining the bend radius and leg spacing") must be interpreted as:
    // The top view shows the *width* (X) which is determined by the bend radius and leg spacing.
    // And the "generation_notes" saying "top view ... depicts the front elevation" might be a confusion in the prompt's own notes, OR it means the view labeled "top" in the *drawing* is actually the front view.
    // Given the dimension match (30+20+4=54), the U-shape is definitely in the XZ plane.
    
    // Geometry Construction:
    // 1. Two vertical cylinders (legs) along Z.
    //    Left leg: Center X = -bend_radius.
    //    Right leg: Center X = +bend_radius.
    //    Radius = rod_radius.
    //    Height = leg_length.
    //    Base at Z=0.
    
    // 2. The Bend.
    //    A torus segment (half-torus) connecting the tops of the legs.
    //    Center of torus: (0, 0, leg_length).
    //    Major radius: bend_radius.
    //    Minor radius: rod_radius.
    //    The torus is in the XZ plane.
    //    We need the upper half (Z > leg_length).
    
    // Implementation:
    // Create the two legs.
    // Create the bend.
    // Union them.
    
    // The bend is a torus.
    // Torus parameters: R = bend_radius, r = rod_radius.
    // Default torus is in XY plane.
    // We need it in XZ plane.
    // Rotate 90 degrees around X axis?
    // If we rotate a torus (in XY) by 90 deg around X, it becomes in XZ.
    // The "hole" of the torus is along Y.
    // We want the "hole" of the torus to be along Y?
    // The bend connects legs at X = +/- R.
    // The path of the bend is a semicircle in XZ.
    // The cross-section is circular.
    // This is exactly a torus segment.
    
    // Torus in OpenSCAD:
    // torus(R, r) creates a torus centered at origin, in XY plane.
    // To get the XZ plane orientation:
    // rotate([90, 0, 0]) torus(R, r);
    // This puts the torus in the XZ plane.
    // The "top" of the torus (positive Z) is the part we want.
    // We need to intersect with a cube to keep only the upper half (Z > 0 relative to torus center).
    // Torus center is at Z = leg_length.
    // So we keep Z > leg_length.
    
    // Wait, the legs go from Z=0 to Z=leg_length.
    // The bend starts at Z=leg_length.
    // So the bend is the upper half of the torus centered at (0,0,leg_length).
    
    // Let's verify the connection.
    // Leg top is at Z=leg_length.
    // Torus center is at Z=leg_length.
    // The torus extends from Z = leg_length - r to Z = leg_length + r.
    // The legs extend to Z = leg_length.
    // The union will be smooth if the torus starts exactly at the leg top.
    // The torus surface at Z=leg_length is the "equator" of the torus.
    // The legs are cylinders ending at Z=leg_length.
    // The union of a cylinder ending at Z=H and a torus centered at Z=H (upper half) will have a sharp edge at the junction?
    // No, the torus tangent at the equator is vertical (parallel to Z).
    // The cylinder side is vertical.
    // So they merge smoothly.
    
    // One detail: The torus "hole" is along Y.
    // The legs are along Z.
    // The bend connects them.
    
    // Code Structure:
    // 1. Define parameters.
    // 2. Module for the handle.
    //    - Union of:
    //      - Left Leg (Cylinder)
    //      - Right Leg (Cylinder)
    //      - Bend (Half Torus)
    
    // Left Leg:
    // translate([-bend_radius, 0, 0]) cylinder(h=leg_length, r=rod_radius);
    
    // Right Leg:
    // translate([bend_radius, 0, 0]) cylinder(h=leg_length, r=rod_radius);
    
    // Bend:
    // translate([0, 0, leg_length])
    // intersection() {
    //   rotate([90, 0, 0]) torus(R=bend_radius, r=rod_radius);
    //   translate([0, 0, 0]) cube([2*bend_radius+2*rod_radius, 2*rod_radius, leg_length+rod_radius], center=true);
    //   // Need to keep only Z > 0 part of the torus.
    //   // The torus is centered at 0,0,0 in its local frame.
    //   // We want Z > 0.
    //   // So intersect with a cube from Z=0 to Z=large.
    // }
    
    // Wait, the torus after rotate([90,0,0]) is in XZ.
    // The "hole" is along Y.
    // The torus exists for Y in [-r, r].
    // The legs are at X = +/- R.
    // The torus passes through X = +/- R at Z = 0 (local).
    // So the intersection with Z > 0 keeps the upper arch.
    
    // Let's refine the bend cutter/intersection.
    // We want the upper half of the torus.
    // Intersection with a cube that covers Z >= 0.
    
    // Final check on dimensions:
    // Width (X): From -R-r to R+r. Total = 2(R+r).
    // Depth (Y): From -r to r. Total = 2r.
    // Height (Z): From 0 to leg_length + r.
    
    // Given:
    // rod_diameter = 8 -> r = 4.
    // bend_radius = 20 -> R = 20.
    // leg_length = 30.
    
    // Width = 2(20+4) = 48 mm.
    // Depth = 8 mm.
    // Height = 30 + 4 = 34 mm.
    
    // BUT the derived sizes say:
    // width_mm = 16.73
    // depth_mm = 26.81
    // height_mm = 54.0
    
    // My calculated dimensions (48, 8, 34) do not match the derived sizes (16.73, 26.81, 54.0).
    // This implies my orientation assumption is wrong, OR the parameters in the "features" list are not the final ones, OR the "derived_sizes" are the truth.
    
    // The prompt says: "derived_sizes ... lists measured physical sizes ... set the top-level size parameters to exactly those values".
    // So I MUST use width=16.73, depth=26.81, height=54.0.
    
    // Let's re-evaluate the orientation based on these dimensions.
    // Height (Z) = 54.
    // Width (X) = 16.73.
    // Depth (Y) = 26.81.
    
    // If the U-shape is in XZ (vertical):
    // Height = Leg Length + Bend Radius + Rod Radius.
    // Width = 2 * (Bend Radius + Rod Radius).
    // Depth = Rod Diameter.
    
    // If Depth = Rod Diameter = 26.81?
    // Then rod_diameter = 26.81.
    // Then Width = 2 * (R + 13.4).
    // 16.73 = 2R + 26.8.
    // 2R = -10. Impossible.
    
    // So the U-shape is NOT in XZ with Depth=Rod Diameter.
    
    // If the U-shape is in XY (horizontal):
    // Legs are along Z.
    // Height = Leg Length + Rod Radius (if bend is at top) or just Leg Length?
    // If legs are along Z, and bend is in XY at the top.
    // Height = Leg Length + Rod Radius?
    // Width (X) = 2 * (Bend Radius + Rod Radius).
    // Depth (Y) = 2 * (Bend Radius + Rod Radius)? No, the bend is a semicircle.
    // If the U-shape is in XY, the "width" and "depth" depend on the orientation of the U.
    // If the U opens along Y:
    // Width (X) = 2 * (Bend Radius + Rod Radius).
    // Depth (Y) = Bend Radius + Rod Radius + Leg Length? No, legs are along Z.
    // If legs are along Z, the Y-extent is just the rod diameter?
    // No, the bend is in XY. The bend extends in Y.
    // If the U opens along Y, the bend is at Y=0, legs go to Y=Leg Length?
    // No, legs are along Z.
    // So the bend is in XY. The legs are along Z.
    // The "Depth" (Y) would be the extent of the bend in Y.
    // If the U is symmetric about X, the bend goes from Y=0 to Y=Bend Radius?
    // Or is the U oriented such that the legs are parallel to Y?
    // If legs are parallel to Y, then Height (Z) is just Rod Diameter?
    // But Height is 54.
    
    // Let's look at the "Left" view again.
    // "Cross-sectional profile (circular) and height of the legs".
    // Left view is YZ.
    // If it shows the height of the legs, the legs are along Z.
    // So Legs are along Z.
    
    // If Legs are along Z, and Height is 54.
    // Then Leg Length is approx 54.
    
    // If Legs are along Z, the U-shape must be in XY or XZ.
    // If U-shape is in XZ, Width is determined by Bend Radius.
    // If U-shape is in XY, Width and Depth are determined by Bend Radius.
    
    // Let's assume the U-shape is in XY (Horizontal).
    // Legs are along Z.
    // The bend is in XY.
    // The "Width" (X) and "Depth" (Y) are the extents of the U-shape.
    // If the U-shape is a semicircle in XY:
    // The bounding box of the semicircle is (2R) x (R).
    // Plus rod diameter.
    // So Width = 2R + d. Depth = R + d.
    // Or Width = R + d. Depth = 2R + d.
    
    // Given Width=16.73, Depth=26.81.
    // Depth > Width.
    // So the "long" direction of the U is along Y.
    // This means the U opens along Y?
    // If the U opens along Y, the legs are parallel to Y?
    // But we established legs are along Z.
    
    // Contradiction.
    
    // Let's reconsider the "Left" view.
    // "Left" view is YZ.
    // If the legs are along Y, the Left view shows the legs' length (Y) and rod diameter (Z).
    // If the legs are along Y, then Height (Z) is just the rod diameter?
    // But Height is 54.
    
    // What if the "Height" of 54 is the length of the legs, and the legs are along Y?
    // Then the object is lying on its side?
    // "The part must sit on the build plate: lowest geometry at Z=0".
    // If legs are along Y, and the object sits on Z=0, the rod diameter is the height?
    // No, if legs are along Y, the Z-extent is the rod diameter.
    // Unless the bend is in YZ?
    
    // Let's try: U-shape in YZ plane.
    // Legs are along Y.
    // Bend is in YZ.
    // Height (Z) = Rod Diameter? No.
    // If U-shape is in YZ, the Z-extent is determined by the bend.
    // Height = 2 * (Bend Radius + Rod Radius)?
    // If Height = 54.
    // 54 = 2(R+r).
    // Width (X) = Rod Diameter.
    // Depth (Y) = Leg Length + Bend Radius?
    
    // Let's check the views again.
    // Front (XZ): Shows arch.
    // If U-shape is in YZ, Front (XZ) shows the side of the U (a rectangle).
    // This doesn't show the arch.
    
    // The only view that shows the arch is the one perpendicular to the plane of the U.
    // If Front (XZ) shows the arch, U-shape is in XZ.
    // If Left (YZ) shows the arch, U-shape is in YZ.
    // If Top (XY) shows the arch, U-shape is in XY.
    
    // Prompt: "Front view ... showing the arch".
    // So U-shape is in XZ.
    
    // Why did the dimensions not match?
    // Width=16.73, Depth=26.81, Height=54.
    // If U-shape is in XZ:
    // Height = Leg Length + R + r.
    // Width = 2(R+r).
    // Depth = 2r.
    
    // From Width=16.73:
    // 2(R+r) = 16.73 -> R+r = 8.365.
    // From Depth=26.81:
    // 2r = 26.81 -> r = 13.4.
    // Then R = 8.365 - 13.4 = Negative. Impossible.
    
    // So Depth is NOT 2r.
    // Maybe the handle is not a simple U?
    // Or maybe the "Depth" includes the legs?
    // If the legs are along Y?
    // If legs are along Y, and U-shape is in XZ.
    // Then Depth (Y) = Leg Length.
    // Height (Z) = Leg Length? No.
    
    // Let's look at the "Left" view description again.
    // "Cross-sectional profile (circular) and height of the legs".
    // If Left view (YZ) shows the height of the legs, the legs are along Z.
    
    // Is it possible the U-shape is in XY, and the "Front" view description is wrong?
    // "The 'top' view in the drawing actually depicts the front elevation of the handle (the U-shape)".
    // This note is key.
    // It says the view labeled "top" (View 4) shows the U-shape.
    // View 4 is Top (XY).
    // So the U-shape is in XY.
    
    // If U-shape is in XY:
    // Legs are along Z.
    // Height (Z) = Leg Length + Rod Radius (top of bend).
    // Width (X) and Depth (Y) are the extents of the U-shape.
    
    // If the U-shape is a semicircle in XY:
    // The bounding box is (2R) x (R) plus rod diameter.
    // Let's assume the U opens along Y.
    // Then X-extent = 2(R+r).
    // Y-extent = R + r + Leg Length? No, legs are along Z.
    // The bend is in XY. The legs are along Z.
    // The Y-extent is just the bend's Y-extent.
    // If the U opens along Y, the bend goes from Y=0 to Y=R.
    // So Y-extent = R + r.
    // X-extent = 2(R+r).
    
    // Given Width=16.73, Depth=26.81.
    // If X=16.73, Y=26.81.
    // 2(R+r) = 16.73 -> R+r = 8.365.
    // R+r = 26.81.
    // Contradiction.
    
    // If the U opens along X.
    // X-extent = R+r.
    // Y-extent = 2(R+r).
    // R+r = 16.73.
    // 2(R+r) = 26.81 -> R+r = 13.4.
    // Contradiction.
    
    // Maybe the U-shape is not a semicircle?
    // "bend ... angle: 180". It is a semicircle.
    
    // Maybe the "Width" and "Depth" are swapped in my assumption?
    // Or maybe the legs are not along Z?
    
    // Let's look at the "Left" view (YZ) again.
    // "Height of the legs".
    // If legs are along Y, the Left view (YZ) shows the legs' length (Y) and rod diameter (Z).
    // If legs are along Y, then Height (Z) is just the rod diameter?
    // But Height is 54.
    
    // What if the "Height" of 54 is the length of the legs, and the legs are along Z?
    // And the U-shape is in XY?
    // Then Height = Leg Length + r.
    // 54 = Leg Length + r.
    
    // And Width/Depth are the U-shape extents.
    // We had a contradiction with the semicircle extents.
    // Unless the U-shape is rotated 45 degrees? No.
    
    // Let's trust the "derived_sizes" as the absolute truth for the bounding box.
    // And the "features" for the relative proportions.
    // rod_diameter = 8.
    // bend_radius = 20.
    // leg_length = 30.
    
    // If I use these features:
    // r=4, R=20, L=30.
    // If U-shape is in XZ:
    // Width = 2(20+4) = 48.
    // Depth = 8.
    // Height = 30+4 = 34.
    // This does not match 16.73, 26.81, 54.
    
    // If I scale the features to match the height?
    // Height 54 vs 34. Scale = 1.58.
    // Width 48 * 1.58 = 75. No.
    
    // There is a fundamental mismatch between the "features" parameters and the "derived_sizes".
    // The prompt says: "derived_sizes ... set the top-level size parameters to exactly those values".
    // So I must use Width=16.73, Depth=26.81, Height=54.
    
    // I need to derive the geometry parameters (R, r, L) from these dimensions.
    // Assumption: U-shape is in XZ (Front view shows arch).
    // Height = L + R + r = 54.
    // Width = 2(R + r) = 16.73.
    // Depth = 2r = 26.81.
    
    // From Depth: r = 13.4.
    // From Width: 2(R + 13.4) = 16.73 -> R + 13.4 = 8.365 -> R = -5.
    // Impossible.
    
    // Assumption: U-shape is in XY (Top view shows arch).
    // Legs along Z.
    // Height = L + r = 54.
    // Width = 2(R + r) = 16.73.
    // Depth = R + r = 26.81? (If U opens along Y).
    // Or Depth = 2(R+r) and Width = R+r?
    
    // If Width = 16.73 and Depth = 26.81.
    // Case 1: U opens along Y.
    // X-extent = 2(R+r) = 16.73 -> R+r = 8.365.
    // Y-extent = R+r = 26.81.
    // Contradiction.
    
    // Case 2: U opens along X.
    // X-extent = R+r = 16.73.
