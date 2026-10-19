/* doodle-meta {"version":1,"parameters":{"base_width":{"label":"Base Width","description":"Width of the rectangular base along X","unit":"mm","feature":"base_width"},"base_depth":{"label":"Base Depth","description":"Depth of the rectangular base along Y","unit":"mm","feature":"base_depth"},"top_diameter":{"label":"Top Diameter","description":"Diameter of the circular top face","unit":"mm","feature":"top_diameter"},"height":{"label":"Height","description":"Total height of the transition piece","unit":"mm","feature":"height"}},"features":{"base_width":{"kind":"dimension","axis":"x","label":"Base Width"},"base_depth":{"kind":"dimension","axis":"y","label":"Base Depth"},"top_diameter":{"kind":"dimension","axis":"x","label":"Top Diameter"},"height":{"kind":"dimension","axis":"z","label":"Height"}}} */

// User-editable parameters
base_width = 60;
base_depth = 40;
top_diameter = 30;
height = 60;

// Derived constants
$fn = 64;
top_radius = top_diameter / 2;

// Module to generate the lofted solid using hull of multiple intermediate profiles
module transition_piece() {
    // Number of intermediate slices for smooth transition
    num_slices = 20;
    
    hull() {
        // Bottom slice: rectangular base
        translate([0, 0, 0]) {
            cube([base_width, base_depth, 0.01], center=true);
        }
        
        // Intermediate slices with interpolated rounded-rectangle profiles
        for (i = [1 : num_slices - 1]) {
            t = i / num_slices;
            
            // Interpolate width and depth
            w = base_width * (1 - t) + top_diameter * t;
            d = base_depth * (1 - t) + top_diameter * t;
            
            // Interpolate corner radius: 0 at bottom, top_radius at top
            r = t * top_radius;
            
            // Clamp radius to valid range
            max_r = min(w, d) / 2;
            r = min(r, max_r);
            
            // Create rounded rectangle at this height
            z_pos = t * height;
            
            translate([0, 0, z_pos]) {
                rounded_rect(w, d, r);
            }
        }
        
        // Top slice: circular top
        translate([0, 0, height]) {
            cylinder(h=0.01, r=top_radius, center=true);
        }
    }
}

// Module for a rounded rectangle (flat, thin)
module rounded_rect(w, d, r) {
    if (r <= 0.001) {
        // Sharp rectangle
        cube([w, d, 0.01], center=true);
    } else {
        // Rounded rectangle using hull of inner rect and corner cylinders
        inner_w = w - 2*r;
        inner_d = d - 2*r;
        
        hull() {
            // Central rectangle
            if (inner_w > 0 && inner_d > 0) {
                cube([inner_w, inner_d, 0.01], center=true);
            }
            
            // Four corner cylinders
            translate([inner_w/2, inner_d/2, 0]) cylinder(h=0.01, r=r, center=true);
            translate([-inner_w/2, inner_d/2, 0]) cylinder(h=0.01, r=r, center=true);
            translate([inner_w/2, -inner_d/2, 0]) cylinder(h=0.01, r=r, center=true);
            translate([-inner_w/2, -inner_d/2, 0]) cylinder(h=0.01, r=r, center=true);
        }
    }
}

// Main design
transition_piece();
