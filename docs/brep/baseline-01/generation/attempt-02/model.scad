/* doodle-meta {"version":1,"parameters":{"width":{"label":"Overall width","description":"Changes the body width","unit":"mm","feature":"body_width"},"depth":{"label":"Overall depth","description":"Changes the body depth","unit":"mm","feature":"body_depth"},"height":{"label":"Overall height","description":"Changes the body height","unit":"mm","feature":"body_height"},"backplate_thickness":{"label":"Backplate thickness","description":"Thickness of the vertical backplate","unit":"mm","feature":"backplate"},"base_thickness":{"label":"Base thickness","description":"Thickness of the horizontal base flange","unit":"mm","feature":"base"},"cutout_rect_w":{"label":"Rect cutout width","description":"Width of the top-left rectangular cutout","unit":"mm","feature":"cutout_rect"},"cutout_rect_h":{"label":"Rect cutout height","description":"Height of the top-left rectangular cutout","unit":"mm","feature":"cutout_rect"},"cutout_slot_w":{"label":"Slot width","description":"Width of the vertical slot cutouts","unit":"mm","feature":"cutout_slot"},"cutout_slot_h_top":{"label":"Top slot height","description":"Height of the top-middle slot cutout","unit":"mm","feature":"cutout_slot"},"cutout_slot_h_bot":{"label":"Bottom slot height","description":"Height of the bottom slot cutouts","unit":"mm","feature":"cutout_slot"}},"features":{"body_width":{"kind":"dimension","axis":"x","label":"Overall width"},"body_depth":{"kind":"dimension","axis":"y","label":"Overall depth"},"body_height":{"kind":"dimension","axis":"z","label":"Overall height"},"backplate":{"kind":"region","label":"Vertical backplate","min":[0,0,0],"max":[{"parameter":"backplate_thickness"},{"parameter":"depth"},{"parameter":"height"}]},"base":{"kind":"region","label":"Horizontal base","min":[0,0,0],"max":[{"parameter":"width"},{"parameter":"depth"},{"parameter":"base_thickness"}]},"cutout_rect":{"kind":"region","label":"Top-left rectangle cutout","min":[{"parameter":"width","scale":0.063,"offset":0},{"parameter":"backplate_thickness","offset":-1},{"parameter":"height","scale":0.214,"offset":0}],"max":[{"parameter":"width","scale":0.263,"offset":0},{"parameter":"backplate_thickness","offset":1},{"parameter":"height","scale":0.364,"offset":0}]},"cutout_slot":{"kind":"region","label":"Slot cutouts","min":[{"parameter":"width","scale":0.113,"offset":0},{"parameter":"backplate_thickness","offset":-1},{"parameter":"height","scale":0.088,"offset":0}],"max":[{"parameter":"width","scale":0.838,"offset":0},{"parameter":"backplate_thickness","offset":1},{"parameter":"height","scale":0.866,"offset":0}]}}} */

// --- Parameters ---
width = 73.05;
depth = 47.99;
height = 100.0;
backplate_thickness = 8.0;
base_thickness = 8.0;

// Cutout dimensions (derived from normalized view measurements)
cutout_rect_w = 14.6;
cutout_rect_h = 15.0;
cutout_slot_w = 9.0;
cutout_slot_h_top = 36.0;
cutout_slot_h_bot = 44.0;

// Cutout centers (derived from evaluation missing centroids)
// Front view mapping: X = u * width, Z = (1 - v) * height
rect_cx = 0.163 * width;
rect_cz = (1.0 - 0.726) * height;

slot_top_cx = 0.788 * width;
slot_top_cz = (1.0 - 0.69) * height;

slot_bl_cx = 0.259 * width;
slot_bl_cz = (1.0 - 0.14) * height;

slot_br_cx = 0.561 * width;
slot_br_cz = (1.0 - 0.238) * height;

// --- Modules ---
// Vertical slot (stadium) centered at (cx, cz) in XZ plane, cutting through X (the backplate).
module slot_cutter(w, h, cx, cz) {
    r = w / 2;
    straight = h - w;
    translate([cx, -1, cz])
        rotate([0, 90, 0])
            hull() {
                translate([0, 0,  straight/2]) cylinder(r=r, h=depth+2, center=true);
                translate([0, 0, -straight/2]) cylinder(r=r, h=depth+2, center=true);
            }
}

// Rectangle centered at (cx, cz) in XZ plane, cutting through X (the backplate).
module rect_cutter(w, h, cx, cz) {
    translate([cx, -1, cz])
        rotate([0, 90, 0])
            cube([h, depth + 2, w], center=true);
}

// --- Main Design ---
difference() {
    // 1. Positive Body: L-Shape
    union() {
        // Vertical Backplate (Left side, full height)
        cube([backplate_thickness, depth, height]);
        // Horizontal Base (Bottom, extending right)
        cube([width, depth, base_thickness]);
    }

    // 2. Subtractive Cutouts (Through the backplate, along X)
    rect_cutter(cutout_rect_w, cutout_rect_h, rect_cx, rect_cz);
    slot_cutter(cutout_slot_w, cutout_slot_h_top, slot_top_cx, slot_top_cz);
    slot_cutter(cutout_slot_w, cutout_slot_h_bot, slot_bl_cx, slot_bl_cz);
    slot_cutter(cutout_slot_w, cutout_slot_h_bot, slot_br_cx, slot_br_cz);
}
