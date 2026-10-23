/* doodle-meta {"version":1,"parameters":{"width":{"label":"Overall width","description":"Changes the body width","unit":"mm","feature":"body_width"},"depth":{"label":"Overall depth","description":"Changes the body depth","unit":"mm","feature":"body_depth"},"height":{"label":"Overall height","description":"Changes the body height","unit":"mm","feature":"body_height"}},"features":{"body_width":{"kind":"dimension","axis":"x","label":"Overall width"},"body_depth":{"kind":"dimension","axis":"y","label":"Overall depth"},"body_height":{"kind":"dimension","axis":"z","label":"Overall height"}}} */

width = 127.65957446808511;
depth = 127.65957446808511;
height = 88.29787234042553;

// Section heights derived from front view proportions (sum to height)
h_bottom = height * 0.28;
h_waist = height * 0.44;
h_top = height * 0.28;

// Section widths (X) derived from front view proportions
w_bottom = width * 0.85;
w_waist = width * 0.40;
w_top = width * 0.94;

// Section depths (Y) derived from right view proportions
d_bottom = depth * 0.83;
d_waist = depth * 0.40;
d_top = depth * 0.94;

// Z levels (bottom of each section)
z_bottom = 0;
z_waist = h_bottom;
z_top = h_bottom + h_waist;

// Overlap to ensure manifold connection
eps = 0.1;

module bottom_flange() {
    translate([0, 0, z_bottom + h_bottom/2])
    cube([w_bottom, d_bottom, h_bottom], center=true);
}

module waist() {
    translate([0, 0, z_waist + h_waist/2])
    cube([w_waist, d_waist, h_waist + 2*eps], center=true);
}

module top_flange() {
    translate([0, 0, z_top + h_top/2])
    cube([w_top, d_top, h_top], center=true);
}

module bracket() {
    union() {
        bottom_flange();
        waist();
        top_flange();
    }
}

bracket();
