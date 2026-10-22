/* doodle-meta {"version":1,"parameters":{"max_diameter":{"label":"Overall Diameter","description":"Maximum diameter of the knob (base and cap)","unit":"mm","feature":"overall_diameter"},"total_height":{"label":"Overall Height","description":"Total height of the knob from base to top","unit":"mm","feature":"overall_height"},"neck_diameter":{"label":"Neck Diameter","description":"Diameter of the narrow middle section","unit":"mm","feature":"neck_width"},"base_height":{"label":"Base Height","description":"Height of the bottom flange section","unit":"mm","feature":"base_height"},"cap_height":{"label":"Cap Height","description":"Height of the top cap section","unit":"mm","feature":"cap_height"}},"features":{"overall_diameter":{"kind":"dimension","axis":"x","label":"Overall Diameter"},"overall_height":{"kind":"dimension","axis":"z","label":"Overall Height"},"neck_width":{"kind":"region","label":"Neck","min":[0,0,0],"max":[{"parameter":"neck_diameter","scale":0.5,"offset":0},{"parameter":"neck_diameter","scale":0.5,"offset":0},{"parameter":"total_height","scale":1,"offset":0}]},"base_height":{"kind":"region","label":"Base Flange","min":[0,0,0],"max":[{"parameter":"max_diameter","scale":0.5,"offset":0},{"parameter":"max_diameter","scale":0.5,"offset":0},{"parameter":"base_height","scale":1,"offset":0}]},"cap_height":{"kind":"region","label":"Top Cap","min":[0,0,{"parameter":"total_height","scale":1,"offset":0}],"max":[{"parameter":"max_diameter","scale":0.5,"offset":0},{"parameter":"max_diameter","scale":0.5,"offset":0},{"parameter":"total_height","scale":1,"offset":0}]}}} */

// Parameters
max_diameter = 56.0;
total_height = 38.64;
neck_diameter = 20.0; // Inferred from drawing proportions (approx 1/3 of max)
base_height = 10.0;   // Inferred from drawing proportions
cap_height = 10.0;    // Inferred from drawing proportions

// Derived dimensions
max_radius = max_diameter / 2;
neck_radius = neck_diameter / 2;
neck_height = total_height - base_height - cap_height;

// Chamfer parameters
chamfer_size = 2.0;

// Modules

module knob_body() {
    // Construct the stepped profile using cylinders
    // 1. Base Flange (Bottom)
    // We use a cylinder for the main body of the base.
    // To add a chamfer to the bottom edge, we can subtract a cone or use a specific profile.
    // For simplicity and robustness in OpenSCAD for 3D printing, we will stack cylinders.
    // The "slight chamfer" on the bottom edge is often better handled by a small cone subtraction or just a standard cylinder if the chamfer is minor.
    // Let's create the base as a cylinder.
    
    // 2. Neck (Middle)
    // 3. Top Cap (Top)
    
    // To ensure watertightness and proper union, we overlap slightly or just stack them exactly.
    // Stacking exactly is fine for union.
    
    // Base Flange
    translate([0, 0, 0])
        cylinder(h = base_height, r = max_radius, $fn = 64);
        
    // Neck
    translate([0, 0, base_height])
        cylinder(h = neck_height, r = neck_radius, $fn = 64);
        
    // Top Cap
    translate([0, 0, base_height + neck_height])
        cylinder(h = cap_height, r = max_radius, $fn = 64);
}

module chamfer_bottom() {
    // Subtract a cone to create a chamfer on the bottom edge of the base
    // The cone should be wider at the bottom (Z=0) and narrow up to the chamfer height.
    // Actually, to chamfer the bottom edge (outer edge at Z=0), we subtract a cone that is 
    // wide at Z=0 and narrows to the radius at Z=chamfer_size.
    // Wait, standard chamfer on bottom edge:
    // The material exists at r=max_radius for z > 0.
    // We want to remove material near the corner (r=max_radius, z=0).
    // We subtract a cone that starts at r=max_radius at z=0 and goes to r=max_radius-chamfer_size at z=chamfer_size?
    // No, a chamfer cuts the corner.
    // Let's use a difference operation on the base.
    
    // Cone for bottom chamfer:
    // At Z=0, radius should be max_radius + chamfer_size (to ensure cut)
    // At Z=chamfer_size, radius should be max_radius - chamfer_size? No.
    // Let's think about the profile.
    // Original: Vertical line at r=max_radius from z=0 to z=base_height.
    // Chamfered: Line from (max_radius, chamfer_size) to (max_radius-chamfer_size, 0)? 
    // Usually "chamfer on bottom edge" means the outer bottom corner is cut.
    // So at Z=0, the radius is reduced. At Z=chamfer_size, the radius is full max_radius.
    // So we subtract a cone that is:
    // r1 = max_radius (at Z=0) -> this doesn't cut anything if we subtract from inside.
    // We need to subtract the "corner".
    // The corner is the volume outside the chamfer line.
    // Let's subtract a cone that is wide at the bottom and narrow at the top of the chamfer zone.
    // Cone: r1 = max_radius + 1 (at Z=0), r2 = max_radius - chamfer_size (at Z=chamfer_size).
    // This will cut away the outer bottom corner.
    
    translate([0, 0, 0])
        cylinder(h = chamfer_size, r1 = max_radius + 1, r2 = max_radius - chamfer_size, $fn = 64);
}

module chamfer_top() {
    // Subtract a cone to create a chamfer on the top edge of the cap
    // Top edge is at Z = total_height.
    // We want to cut the outer top corner.
    // At Z = total_height, radius is reduced. At Z = total_height - chamfer_size, radius is full.
    // Subtract a cone:
    // r1 = max_radius - chamfer_size (at Z = total_height - chamfer_size)
    // r2 = max_radius + 1 (at Z = total_height)
    
    translate([0, 0, total_height - chamfer_size])
        cylinder(h = chamfer_size, r1 = max_radius - chamfer_size, r2 = max_radius + 1, $fn = 64);
}

// Main Design
difference() {
    knob_body();
    chamfer_bottom();
    chamfer_top();
}
