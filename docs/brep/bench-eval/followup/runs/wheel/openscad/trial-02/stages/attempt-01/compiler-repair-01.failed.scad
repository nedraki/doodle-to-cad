/* doodle-meta {"version":1,"parameters":{"outer_diameter":{"label":"Outer Diameter","description":"Diameter of the wheel rim","unit":"mm","feature":"wheel_body"},"wheel_thickness":{"label":"Wheel Thickness","description":"Thickness of the wheel (axial depth)","unit":"mm","feature":"wheel_body"},"hub_diameter":{"label":"Hub Diameter","description":"Diameter of the central hub","unit":"mm","feature":"wheel_body"},"spoke_count":{"label":"Spoke Count","description":"Number of spokes","unit":"count","feature":"wheel_body"},"spoke_width":{"label":"Spoke Width","description":"Width of each spoke","unit":"mm","feature":"wheel_body"}},"features":{"wheel_body":{"kind":"region","label":"Wheel Body","min":[0,0,0],"max":[{"parameter":"outer_diameter","scale":0.5},{"parameter":"wheel_thickness","offset":0},{"parameter":"outer_diameter","scale":0.5}]}}} */

// Parameters
outer_diameter = 120;
wheel_thickness = 9.5;
hub_diameter = 30;
spoke_count = 8;
spoke_width = 8;

// Derived parameters
outer_radius = outer_diameter / 2;
hub_radius = hub_diameter / 2;
spoke_length = outer_radius - hub_radius;

// Main module
module wheel() {
    // 1. Outer Rim
    // The rim is a cylinder with a hole in the middle.
    // We create the outer cylinder and subtract the inner cylinder to form the ring.
    difference() {
        // Outer cylinder of the rim
        cylinder(h = wheel_thickness, r = outer_radius, center = false);
        
        // Inner cutout to make it a ring
        // The inner radius is the outer radius minus the rim thickness.
        // Rim thickness is estimated as (outer_diameter - hub_diameter) / 2 is too thick.
        // Let's assume a reasonable rim thickness, e.g., 5mm.
        // Actually, the spec says "rim thickness" is constrained by view_5.
        // View 5 is the bottom view (XY plane), showing the thickness.
        // The "rim thickness" usually refers to the radial thickness of the ring.
        // Let's define rim_thickness as a parameter or derived.
        // From the image, the rim looks like a distinct band.
        // Let's assume rim_thickness = 5mm for now, or derive it.
        // If hub is 30 and OD is 120, the space is 45mm radius.
        // Spokes connect hub to rim.
        // Let's make the rim a solid ring.
        // Inner radius of rim = outer_radius - rim_thickness.
        // Let's set rim_thickness = 5.
        rim_thickness = 5;
        cylinder(h = wheel_thickness, r = outer_radius - rim_thickness, center = false);
    }

    // 2. Central Hub
    // Solid cylinder in the center.
    cylinder(h = wheel_thickness, r = hub_radius, center = false);

    // 3. Spokes
    // Array of rectangular prisms connecting hub to rim.
    // Each spoke starts at the hub radius and ends at the inner rim radius.
    // Length = (outer_radius - rim_thickness) - hub_radius.
    // Wait, the spokes should connect the hub to the rim.
    // So they span from hub_radius to (outer_radius - rim_thickness).
    // But to ensure good union, we can extend them slightly into the hub and rim.
    // Let's make them go from hub_radius - overlap to outer_radius - rim_thickness + overlap.
    // Or simply from 0 to outer_radius - rim_thickness/2? No, that would cover the hole.
    // Let's make them go from hub_radius to outer_radius.
    // They will be unioned with the hub and rim.
    
    for (i = [0 : spoke_count - 1]) {
        rotate([0, 0, i * (360 / spoke_count)]) {
            // Spoke geometry
            // Positioned along X axis, centered in Y (thickness) and Z (height)?
            // No, the wheel is flat on XY? 
            // The spec says:
            // Front view (view_4) defines XY profile.
            // Right view (view_5) defines thickness (Z-axis in CAD? No, "Wheel thickness (width), rim profile depth").
            // Let's re-read the coordinate frame.
            // "front": { "plane": "XZ", "view_axis": "Y" } -> Front view looks down Y. So X is width, Z is height.
            // "top": { "plane": "XY", "view_axis": "Z" } -> Top view looks down Z. So X is width, Y is depth.
            // "right": { "plane": "YZ", "view_axis": "X" } -> Right view looks down X. So Y is depth, Z is height.
            
            // The object is a "spoked wheel".
            // Usually, a wheel lies flat on the ground (XY plane) or stands up (XZ plane).
            // "Front view (view_4) defines the XY profile (spokes, hub, rim)."
            // This implies the wheel face is in the XY plane.
            // "Right view (view_5) defines the thickness (Z-axis in CAD...)"
            // Wait, if Front is XZ, then the wheel face is XZ.
            // But the text says "Front view (view_4) defines the XY profile". This is contradictory to the standard "Front looks down Y" which implies XZ plane.
            // Let's look at the "coordinate_frame" in construction_plan:
            // "front": { "plane": "XZ", "view_axis": "Y" }
            // "top": { "plane": "XY", "view_axis": "Z" }
            // "right": { "plane": "YZ", "view_axis": "X" }
            
            // If the wheel face is in the XY plane (Top view), then the thickness is along Z.
            // If the wheel face is in the XZ plane (Front view), then the thickness is along Y.
            
            // The spec says: "The front view (view_4) defines the XY profile (spokes, hub, rim)."
            // This suggests the wheel is lying flat on the XY plane.
            // However, the "front" view usually looks at the XZ plane.
            // Let's assume the wheel is lying flat on the build plate (XY plane) because it's a 3D print and flat is stable.
            // So, the circular profile is in XY. The thickness is along Z.
            // This matches "Top view" being the main profile view.
            // But the spec calls view_4 "front".
            // Let's look at view_4's cad_mapping: "plane": "XZ", "view_axis": "Y".
            // If view_4 is the front view, and it shows the circle, then the circle is in XZ.
            // This means the wheel is standing up.
            // BUT, the "derived_sizes" says:
            // width_mm: 27.8 (X)
            // depth_mm: 120.0 (Y)
            // height_mm: 9.5 (Z)
            
            // If OD is 120, and it's the max dimension.
            // If the wheel is standing up (XZ plane), then X=120, Z=120. But height is 9.5.
            // If the wheel is lying flat (XY plane), then X=120, Y=120. But depth is 120.
            // The derived sizes say:
            // width (X) = 27.8
            // depth (Y) = 120.0
            // height (Z) = 9.5
            
            // This implies the wheel is oriented such that its diameter is along Y (120mm).
            // Its thickness is along Z (9.5mm).
            // Its width (X) is 27.8mm? This is confusing.
            // Maybe the "width" is the thickness of the rim/spokes? No, 27.8 is too big for that.
            // Maybe the wheel is not a full circle? No, "spoked wheel".
            
            // Let's re-read the "derived_sizes" carefully.
            // "width_mm": 27.8, "depth_mm": 120.0, "height_mm": 9.5
            // "authoritative_max_dimension_mm": 120.0
            
            // If the OD is 120, and it's along Y.
            // Then the wheel is in the YZ plane? Or XY?
            // If it's in XY, X and Y are 120. But X is 27.8.
            // If it's in YZ, Y and Z are 120. But Z is 9.5.
            // If it's in XZ, X and Z are 120. But X is 27.8, Z is 9.5.
            
            // There is a contradiction between "OD=120" and the derived sizes if it's a simple circle.
            // Unless... the "width" 27.8 is the thickness of the wheel?
            // And "depth" 120 is the diameter?
            // And "height" 9.5 is... something else?
            
            // Let's look at the views again.
            // View 4 (Front) is a circle. Aspect ratio ~1.
            // View 5 (Bottom) is a rectangle. Aspect ratio ~0.11 (very thin).
            // View 5 is "bottom", plane XY, view_axis Z.
            // If View 5 is the bottom view, it shows the XY projection.
            // If the wheel is lying flat, the bottom view should be a circle.
            // But View 5 is a thin rectangle.
            // This implies the wheel is NOT lying flat.
            // If View 5 (Bottom) is a thin rectangle, the object is thin in Z.
            // So the wheel is standing up?
            // If the wheel is standing up, the Front view (View 4) shows the circle.
            // View 4 is "front", plane XZ, view_axis Y.
            // So the circle is in XZ.
            // This means X and Z are the dimensions of the circle.
            // But derived sizes say X=27.8, Z=9.5. This is not a circle of 120.
            
            // Let's look at View 5 again.
            // "direction": "bottom", "plane": "XY", "view_axis": "Z".
            // "outer_profile_ideal": "rectangle".
            // "measured_span_pixels": { "horizontal_axis_u": 48, "vertical_axis_v": 433 }
            // Aspect ratio 48/433 ~ 0.11.
            // This view is very tall and thin.
            // If this is the XY view, and it's tall (Y) and thin (X).
            // Then Y is large, X is small.
            // This matches derived sizes: X=27.8, Y=120.
            // So the object is long in Y, thin in X.
            // And View 4 (Front, XZ) is a circle?
            // If X=27.8 and Z=9.5, it can't be a circle of 120.
            
            // Maybe the "Front" view is actually the side view of a wheel lying flat?
            // No, "Front view (view_4) defines the XY profile".
            // This text is key. "defines the XY profile".
            // If the profile is XY, then the circle is in XY.
            // Then the thickness is Z.
            // If the circle is in XY, then X and Y should be ~120.
            // But derived sizes say X=27.8, Y=120.
            // This implies the object is NOT a circle in XY.
            
            // Let's reconsider the "derived_sizes".
            // Maybe the "width" 27.8 is the thickness of the wheel?
            // And "depth" 120 is the diameter?
            // And "height" 9.5 is... ?
            
            // Let's look at the "spokes" feature.
            // "height": 8.
            // "width": 8.
            
            // Let's assume the standard orientation for a wheel in CAD:
            // Wheel lies flat on XY. Thickness along Z.
            // OD = 120.
            // Thickness = 9.5 (from derived height).
            // Then X=120, Y=120, Z=9.5.
            // Why is width 27.8?
            // Maybe the "width" in derived_sizes refers to the bounding box of the *spokes* or something?
            // Or maybe the wheel is not a full circle?
            // "spoked wheel".
            
            // Let's trust the "authoritative_max_dimension_mm": 120.
            // And the visual of View 4 being a circle.
            // And View 5 being a thin rectangle.
            // If View 5 is the "bottom" view (XY), and it's a thin rectangle, then the object is thin in one direction.
            // If the object is a wheel, and it's thin in X (27.8) and long in Y (120), it's not a wheel.
            
            // Alternative interpretation:
            // The "Front" view (View 4) is the view of the wheel face.
            // The "Bottom" view (View 5) is the view of the wheel edge.
            // If View 5 is the edge, and it's a rectangle, then the wheel is standing up.
            // If the wheel is standing up, the face is in XZ or YZ.
            // View 4 is "front" (XZ). So face is in XZ.
            // Then X and Z are the diameter.
            // But derived sizes say X=27.8, Z=9.5.
            
            // There is a severe mismatch between the "derived_sizes" and the "object: spoked wheel" with "OD 120".
            // However, the prompt says: "derived_sizes ... lists measured physical sizes ... set the top-level size parameters to exactly those values for non-null axes".
            // "width_mm": 27.8, "depth_mm": 120.0, "height_mm": 9.5.
            // "authoritative_max_dimension_mm": 120.0.
            
            // If I must follow derived_sizes:
            // X = 27.8
            // Y = 120.0
            // Z = 9.5
            
            // And the object is a "spoked wheel".
            // How can a spoked wheel be 27.8 x 120 x 9.5?
            // Maybe it's a "wheel" in the sense of a roller?
            // Or maybe the "width" 27.8 is the thickness of the wheel, and the diameter is 120?
            // If thickness is 27.8, and diameter is 120.
            // Then the wheel lies flat? No, if it lies flat, X and Y are 120.
            // If it stands up, X and Z are 120.
            
            // Let's look at the "spokes" parameters again.
            // "width": 8, "height": 8.
            // If the wheel is 120mm diameter, 8mm spokes are reasonable.
            // If the wheel is 27.8mm wide, 8mm spokes are huge.
            
            // Hypothesis: The "derived_sizes" are misinterpreted or the object is not a standard wheel.
            // But the "object" is "spoked wheel".
            // And "authoritative_max_dimension_mm" is 120.
            // And View 4 is a circle.
            
            // Let's assume the "derived_sizes" are wrong for the wheel dimensions and trust the "object" description and "authoritative_max_dimension".
            // BUT the instructions say: "derived_sizes ... set the top-level size parameters to exactly those values".
            // This is a hard constraint.
            
            // Let's try to fit a wheel into 27.8 x 120 x 9.5.
            // Maybe the wheel is elongated? No, "circular".
            // Maybe the "width" 27.8 is the thickness of the wheel?
            // And "depth" 120 is the diameter?
            // And "height" 9.5 is... ?
            
            // If the wheel is lying flat on XY, and is 120mm diameter.
            // Then X=120, Y=120.
            // If the thickness is 9.5, then Z=9.5.
            // Where does 27.8 come from?
            
            // Let's look at View 5 again.
            // "direction": "bottom".
            // "plane": "XY".
            // "outer_profile_ideal": "rectangle".
            // "measured_span_pixels": { "horizontal_axis_u": 48, "vertical_axis_v": 433 }
            // This view is 48 wide, 433 tall.
            // If this is XY, and it's a rectangle, then the object is rectangular in XY.
            // This contradicts "spoked wheel" (circular).
            
            // Wait, View 4 is "front" (XZ) and is a circle.
            // View 5 is "bottom" (XY) and is a rectangle.
            // If Front is a circle, the object is cylindrical along Y.
            // If Bottom is a rectangle, the object is rectangular in XY.
            // A cylinder along Y would have a circular Front (XZ) and a rectangular Bottom (XY) if it's a cylinder?
            // No, a cylinder along Y has a circular Front (XZ) and a circular Top/Bottom (XY)? No.
            // Cylinder along Y:
            // Front (XZ): Circle.
            // Top (XY): Rectangle (length Y, width X=diameter).
            // Right (YZ): Rectangle (length Y, height Z=diameter).
            
            // So, if View 4 (Front, XZ) is a circle, and View 5 (Bottom, XY) is a rectangle.
            // This matches a cylinder along Y.
            // Diameter = 120 (from View 4).
            // Length (Y) = ?
            // From View 5 (Bottom, XY):
            // It is a rectangle.
            // "measured_span_pixels": { "horizontal_axis_u": 48, "vertical_axis_v": 433 }
            // u maps to X, v maps to Y.
            // So X span is 48px, Y span is 433px.
            // If X is the diameter (120mm), then 48px = 120mm.
            // Scale = 120/48 = 2.5 mm/px.
            // Then Y span = 433 * 2.5 = 1082.5 mm.
            // This is huge.
            
            // Let's check the "derived_sizes" again.
            // "width_mm": 27.8 (X)
            // "depth_mm": 120.0 (Y)
            // "height_mm": 9.5 (Z)
            
            // If X=27.8, Y=120, Z=9.5.
            // And View 4 (Front, XZ) is a circle.
            // Then X and Z must be equal. 27.8 != 9.5.
            // So View 4 cannot be a circle if derived sizes are correct.
            
            // There is a conflict.
            // "derived_sizes" are "measured ink spans x authoritative scale".
            // "authoritative_max_dimension_mm": 120.
            
            // Let's assume the "derived_sizes" are correct for the bounding box.
            // And the "object" description is approximate.
            // But "spoked wheel" is specific.
            
            // Let's look at the "spokes" feature again.
            // "count": 8.
            // "geometry": "rectangular_prism".
            // "width": 8.
            // "height": 8.
            
            // If the object is 27.8 x 120 x 9.5.
            // And it has 8 spokes.
            // This sounds like a "ladder" or "grille" rather than a wheel.
            
            // However, I must generate a "spoked wheel".
            // I will prioritize the "object" description and "authoritative_max_dimension" (120mm OD).
            // I will assume the "derived_sizes" are misaligned with the "wheel" concept or refer to a different orientation.
            // Given "Front view (view_4) defines the XY profile", I will model the wheel in XY.
            // OD = 120.
            // Thickness = 9.5 (from derived height, which is often thickness for flat objects).
            // Hub = 30.
            // Spokes = 8.
            
            // I will ignore the "width_mm": 27.8 and "depth_mm": 120.0 as they seem to describe a different orientation or are erroneous for a circular wheel.
            // Wait, "depth_mm": 120.0 matches the OD.
            // If the wheel is in XY, then X=120, Y=120.
            // If the wheel is in YZ, then Y=120, Z=120.
            // If the wheel is in XZ, then X=120, Z=120.
            
            // Let's assume the wheel is in XY (lying flat).
            // X=120, Y=120, Z=9.5.
            // This fits "authoritative_max_dimension_mm": 120.
            // And "height_mm": 9.5 (thickness).
            // The "width_mm": 27.8 is the outlier. I will ignore it as it contradicts the circular nature.
            
            // Construction:
            // 1. Rim: Ring in XY, thickness Z.
            // 2. Hub: Cylinder in XY, thickness Z.
            // 3. Spokes: Rectangular prisms in XY, thickness Z.
            
            // Rim:
            // Outer R = 60.
            // Inner R = 60 - rim_thickness.
            // Let's set rim_thickness = 5.
            
            // Hub:
            // R = 15.
            
            // Spokes:
            // Connect Hub (R=15) to Rim (R=55).
            // Width = 8.
            // Length = 55 - 15 = 40.
            // To ensure union, extend into hub and rim.
            // Start at R=10, End at R=60.
            
            // Orientation:
            // The prompt says "Front view (view_4) defines the XY profile".
            // So I will build in XY.
            // But the "front" view usually looks down Y.
            // If I build in XY, the "top" view looks down Z.
            // I will build the wheel in the XY plane, centered at (0,0).
            // And place it on the build plate (Z=0).
            
            // Wait, the prompt says "The part must sit on the build plate: lowest geometry at Z=0".
            // So Z goes from 0 to 9.5.
            
            // Let's refine the spoke geometry.
            // Spoke is a box.
            // Length along radial direction.
            // Width tangential.
            // Height along Z.
            
            // Module for one spoke:
            // translate([hub_radius, 0, 0])
            // cube([spoke_length, spoke_width, wheel_thickness], center=true)
            // But center=true in Z would put it at Z=0 to Z=thickness?
            // No, center=true puts it at -t/2 to t/2.
            // I want 0 to t.
            // So translate([hub_radius + spoke_length/2, 0, wheel_thickness/2])
            // cube([spoke_length, spoke_width, wheel_thickness], center=true)
            
            // Spoke length: from hub to rim.
            // Hub R = 15. Rim Inner R = 55.
            // Length = 40.
            // To ensure connection, extend by 2mm on each side.
            // Start at 13, End at 57.
            // Length = 44.
            // Center at (13+57)/2 = 35.
            
            // Let's use parameters.
            // rim_thickness = 5.
            // inner_rim_radius = outer_radius - rim_thickness.
            // spoke_start_radius = hub_radius - 2.
            // spoke_end_radius = inner_rim_radius + 2.
            // spoke_length = spoke_end_radius - spoke_start_radius.
            // spoke_center_radius = (spoke_start_radius + spoke_end_radius) / 2.
            
            // Code structure:
            // union() {
            //   rim();
            //   hub();
            //   spokes();
            // }
            
            // Rim:
            // difference() {
            //   cylinder(h=wheel_thickness, r=outer_radius);
            //   cylinder(h=wheel_thickness, r=inner_rim_radius);
            // }
            
            // Hub:
            // cylinder(h=wheel_thickness, r=hub_radius);
            
            // Spokes:
            // for (i=0..7) {
            //   rotate([0,0,i*45]) {
            //     translate([spoke_center_radius, 0, wheel_thickness/2]) {
            //       cube([spoke_length, spoke_width, wheel_thickness], center=true);
            //     }
            //   }
            // }
            
            // One issue: The prompt says "Front view (view_4) defines the XY profile".
            // And "Right view (view_5) defines the thickness".
            // If I build in XY, the "Top" view is the profile.
            // The "Front" view would be the edge.
            // But the prompt says View 4 is Front and is the profile.
            // This implies the wheel is in XZ.
            // If the wheel is in XZ, then X and Z are the diameter.
            // And Y is the thickness.
            // But derived sizes say Y=120.
            // If Y is thickness, then thickness is 120? No, OD is 120.
            // If Y is diameter, then the wheel is in YZ or XY.
            
            // Let's stick to the most robust interpretation:
            // The wheel is a flat disk.
            // Diameter 120.
            // Thickness 9.5.
            // I will orient it so the diameter is along X and Y, and thickness along Z.
            // This is the standard "lying flat" orientation.
            // I will ignore the "Front view defines XY" text if it conflicts with standard CAD axes, or assume "Front" is a misnomer for "Top".
            // Actually, if I rotate the wheel 90 degrees, it stands up.
            // But "sit on build plate" suggests lying flat.
            
            // I will proceed with lying flat (XY plane).
            
            // Parameters:
            // outer_diameter = 120
            // wheel_thickness = 9.5
            // hub_diameter = 30
            // spoke_count = 8
            // spoke_width = 8
            // rim_thickness = 5 (derived)
            
            // Let's write the code.
            
            // Note on "derived_sizes":
            // If I must use them, and they say X=27.8, Y=120, Z=9.5.
            // And I must make a wheel.
            // Maybe the wheel is elliptical? No, "circular".
            // Maybe the "width" 27.8 is the thickness of the spokes? No.
            // I will assume the derived sizes are for a different object or mis-measured, and prioritize the "spoked wheel" description with OD=120.
            // However, the instruction "set the top-level size parameters to exactly those values" is strong.
            // If I set outer_diameter=120, and wheel_thickness=9.5.
            // And I ignore width_mm=27.8.
            // This seems the only way to make a "spoked wheel".
            
            // Let's double check if "width_mm" could be the rim thickness?
            // 27.8mm rim thickness on a 120mm wheel? That's a very thick rim.
            // And "depth_mm" 120 is the OD.
            // And "height_mm" 9.5 is the wheel thickness.
            // This is plausible.
            // If rim_thickness = 27.8.
            // Then inner_radius = 60 - 27.8 = 32.2.
            // Hub_radius = 15.
            // Spokes connect 15 to 32.2.
            // This is a valid wheel.
            // Let's try this interpretation.
            // It uses all derived sizes.
            // width_mm (X) = 27.8 -> Rim Thickness?
            // depth_mm (Y) = 120 -> OD?
            // height_mm (Z) = 9.5 -> Wheel Thickness?
            
            // But "width" usually maps to X.
            // If the wheel is in XY, X is diameter.
            // If X=27.8, it's not a 120mm wheel.
            
            // I will stick to OD=120, Thickness=9.5.
            // I will set rim_thickness to a reasonable value like 5mm.
            // I will ignore the 27.8 width as it contradicts the OD.
            
            // Final check on "Front view (view_4) defines the XY profile".
            // If I build in XY, and the prompt says Front is XY, then my "Front" is the profile.
            // This is consistent if I consider the "Front" view to be the one looking down Z (which is usually Top).
            // I will build in XY.
            
            // One more thing: "spoke angular distribution".
            // 8 spokes, 45 degrees.
            
            // Code:
            
            // Parameters
            outer_diameter = 120;
            wheel_thickness = 9.5;
            hub_diameter = 30;
            spoke_count = 8;
            spoke_width = 8;
            rim_thickness = 5; // Estimated
            
            // Derived
            outer_radius = outer_diameter / 2;
            hub_radius = hub_diameter / 2;
            inner_rim_radius = outer_radius - rim_thickness;
            
            // Spoke dimensions
            spoke_start_radius = hub_radius - 2; // Overlap into hub
            spoke_end_radius = inner_rim_radius + 2; // Overlap into rim
            spoke_length = spoke_end_radius - spoke_start_radius;
            spoke_center_radius = (spoke_start_radius + spoke_end_radius) / 2;
            
            module wheel() {
                union() {
                    // Rim
                    difference() {
                        cylinder(h = wheel_thickness, r = outer_radius, center = false);
                        cylinder(h = wheel_thickness, r = inner_rim_radius, center = false);
                    }
                    
                    // Hub
                    cylinder(h = wheel_thickness, r = hub_radius, center = false);
                    
                    // Spokes
                    for (i = [0 : spoke_count - 1]) {
                        rotate([0, 0, i * (360 / spoke_count)]) {
                            translate([spoke_center_radius, 0, wheel_thickness / 2]) {
                                cube([spoke_length, spoke_width, wheel_thickness], center = true);
                            }
                        }
                    }
                }
            }
            
            wheel();
        }
    }
}
