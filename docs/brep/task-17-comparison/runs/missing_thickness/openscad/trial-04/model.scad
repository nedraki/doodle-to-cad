/* doodle-meta {"version":1,"parameters":{"width":{"label":"Overall width","description":"Changes the body width","unit":"mm","feature":"body_width"},"depth":{"label":"Overall depth","description":"Changes the body depth","unit":"mm","feature":"body_depth"},"height":{"label":"Overall height","description":"Changes the body height","unit":"mm","feature":"body_height"},"corner_radius":{"label":"Corner radius","description":"Changes the outer corner radius","unit":"mm","feature":"body_corner"},"wall_thickness":{"label":"Wall thickness","description":"Changes the side wall thickness","unit":"mm","feature":"wall"},"floor_thickness":{"label":"Floor thickness","description":"Changes the bottom floor thickness","unit":"mm","feature":"floor"}},"features":{"body_width":{"kind":"dimension","axis":"x","label":"Overall width"},"body_depth":{"kind":"dimension","axis":"y","label":"Overall depth"},"body_height":{"kind":"dimension","axis":"z","label":"Overall height"},"body_corner":{"kind":"region","label":"Corner radius","min":[{"parameter":"width","scale":0.5,"offset":0},{"parameter":"depth","scale":0.5,"offset":0},0],"max":[{"parameter":"width","scale":0.5,"offset":0},{"parameter":"depth","scale":0.5,"offset":0},{"parameter":"height","scale":1,"offset":0}]},"wall":{"kind":"region","label":"Wall thickness","min":[0,0,0],[{"parameter":"width","scale":0.5,"offset":0},{"parameter":"depth","scale":0.5,"offset":0},{"parameter":"height","scale":1,"offset":0}]},"floor":{"kind":"region","label":"Floor thickness","min":[0,0,0],[{"parameter":"width","scale":0.5,"offset":0},{"parameter":"depth","scale":0.5,"offset":0},{"parameter":"floor_thickness","scale":1,"offset":0}]}}} */

width = 150.25668850953713;
depth = 100.17112567302475;
height = 50.08556283651237;
corner_radius = 6;
wall_thickness = 5.008556283651237;
floor_thickness = 5.008556283651237;

eps = 0.01;

module rounded_rect(w, d, r, h) {
    hull() {
        translate([ r,  r, 0]) cylinder(h=h, r=r, center=true);
        translate([-r,  r, 0]) cylinder(h=h, r=r, center=true);
        translate([-r, -r, 0]) cylinder(h=h, r=r, center=true);
        translate([ r, -r, 0]) cylinder(h=h, r=r, center=true);
    }
}

module tray() {
    difference() {
        // Outer shell
        translate([0, 0, height/2])
            rounded_rect(width, depth, corner_radius, height);
        
        // Inner cavity
        translate([0, 0, height/2 + floor_thickness/2])
            rounded_rect(width - 2*wall_thickness, depth - 2*wall_thickness, corner_radius - wall_thickness, height);
    }
}

// Center the tray on the XY plane and place it on the build plate (Z=0)
translate([0, 0, height/2])
    tray();
