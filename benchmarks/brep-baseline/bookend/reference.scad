// L-Shaped Bookend — parametric OpenSCAD
// Generated from sketch: front view (back panel face with 4 cutouts) + right view (L-profile)
// Build orientation: flat base on Z=0

// ===== USER PARAMETERS (top-level, named for Modify Design sliders) =====
H = 100;      // Overall height (back panel) [mm]
W = 80;       // Width (panel width = base width) [mm]
D = 50;       // Base depth (front-to-back) [mm]
T = 3;        // Uniform wall thickness [mm]
$fn = 96;     // Circle/arc resolution

// ===== DERIVED / INTERNAL =====
// Cutout proportions (fractions of W and H) — derived from front-view sketch
// Cutout 1: middle-left vertical slot
C1_X_FRAC   = 0.31;   // center X / W
C1_W_FRAC   = 0.16;   // width / W
C1_Z_LO_FRAC = 0.18;  // bottom Z / H
C1_Z_HI_FRAC = 0.59;  // top Z / H

// Cutout 2: top horizontal slot
C2_X_FRAC   = 0.25;
C2_W_FRAC   = 0.32;
C2_Z_LO_FRAC = 0.72;
C2_Z_HI_FRAC = 0.90;

// Cutout 3: center vertical slot
C3_X_FRAC   = 0.53;
C3_W_FRAC   = 0.09;
C3_Z_LO_FRAC = 0.42;
C3_Z_HI_FRAC = 0.73;

// Cutout 4: right vertical slot
C4_X_FRAC   = 0.75;
C4_W_FRAC   = 0.09;
C4_Z_LO_FRAC = 0.20;
C4_Z_HI_FRAC = 0.57;

// Computed cutout geometry (mm)
C1_X = C1_X_FRAC * W;
C1_W = C1_W_FRAC * W;
C1_Z_LO = C1_Z_LO_FRAC * H;
C1_Z_HI = C1_Z_HI_FRAC * H;
C1_H = C1_Z_HI - C1_Z_LO;

C2_X = C2_X_FRAC * W;
C2_W = C2_W_FRAC * W;
C2_Z_LO = C2_Z_LO_FRAC * H;
C2_Z_HI = C2_Z_HI_FRAC * H;
C2_H = C2_Z_HI - C2_Z_LO;

C3_X = C3_X_FRAC * W;
C3_W = C3_W_FRAC * W;
C3_Z_LO = C3_Z_LO_FRAC * H;
C3_Z_HI = C3_Z_HI_FRAC * H;
C3_H = C3_Z_HI - C3_Z_LO;

C4_X = C4_X_FRAC * W;
C4_W = C4_W_FRAC * W;
C4_Z_LO = C4_Z_LO_FRAC * H;
C4_Z_HI = C4_Z_HI_FRAC * H;
C4_H = C4_Z_HI - C4_Z_LO;

// ===== MODULES =====
module back_panel() {
    // Vertical back panel: X=[0,W], Y=[0,T], Z=[0,H]
    // With 4 through-holes subtracted (cut along Y, full thickness T)
    difference() {
        // Solid panel
        cube([W, T, H]);
        
        // Cutout 1: middle-left vertical
        translate([C1_X - C1_W/2, -0.5, C1_Z_LO])
            cube([C1_W, T + 1, C1_H]);
        
        // Cutout 2: top horizontal
        translate([C2_X - C2_W/2, -0.5, C2_Z_LO])
            cube([C2_W, T + 1, C2_H]);
        
        // Cutout 3: center vertical
        translate([C3_X - C3_W/2, -0.5, C3_Z_LO])
            cube([C3_W, T + 1, C3_H]);
        
        // Cutout 4: right vertical
        translate([C4_X - C4_W/2, -0.5, C4_Z_LO])
            cube([C4_W, T + 1, C4_H]);
    }
}

module base() {
    // Horizontal base: X=[0,W], Y=[0,D], Z=[0,T]
    cube([W, D, T]);
}

module bookend() {
    // Union of base + back panel with VOLUMETRIC OVERLAP at the L-corner
    // Overlap region: X=[0,W], Y=[0,T], Z=[0,T] — shared by both parts
    union() {
        base();
        back_panel();
    }
}

// ===== RENDER =====
bookend();