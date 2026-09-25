// ============================================================================
// Greek vase, brought to modernity
// From sketch: /tmp/nuclear_veejcs4m/20260830_104508_980d/input.png
// See intent_spec.md — hollow axisymmetric vase, closed bottom, 4 mm wall,
// three raised vertical flutes (the sketch's three wavy vertical lines) cut
// as ~16-degree sectors of a surface-following band, sunk into the wall for
// robust manifold union.
//
// Profile: natural cubic spline through 8 control points measured from the
// sketch silhouette (px->mm scaled so height = 120 mm). The spline segments
// below were derived from those control points; control points are listed in
// the comment for reference.
//   z (mm) : 0     14.3  23.0  33.3  58.5  80.7  97.6  120
//   r (mm) : 35.8  46.9  51.4  47.5  28.6  25.3  30.1  41.4
//   (flat base -> belly max -> waist -> neck -> flared mouth)
//
// Final size: 105.6 x 105.6 x 120 mm (belly + flute). Fits Bambu 256 cube.
// Flat 71.6 mm base on z=0; self-supporting (no overhangs > 45 deg).
// ============================================================================

$fn = 96;

// ---- primary parameters (mm) ---------------------------------------------
H     = 120;   // overall height
WALL  = 4;     // wall thickness
FLOOR = 4;     // closed bottom slab
LIP_H = 1.5;   // rim chamfer band height
LIP   = 0.6;   // extra outward flare at the rim (modern crisp lip)

// flute (ridge) parameters
ZLO   = 8;     // flute bottom (above base transition)
ZHI   = H - 5; // flute top (below rim)
SINK  = 1.0;   // how deep the flute is embedded into the wall (overlap)
RAISE = 1.4;   // how far the flute proud of the surface
RIB_HALF = 8;  // half-width of flute sector (deg) -> ~16 deg flutes at 120 deg
WEDGE_LEN = 60;
WEDGE_W   = 55 * tan(RIB_HALF); // planar sector cutter half-width

// ---- profile function -----------------------------------------------------
// Natural cubic spline R(z) = c0 + c1*t + c2*t^2 + c3*t^3, t = z - z0,
// per segment [z0, z1] (derived from the control points above).
function R_spline(z) =
  z < 14.3 ? 35.8 + 0.786679*z - 0.000051*z^3
  : z < 23.0 ? 46.9 + 0.625823*(z-14.3) - 0.002193*(z-14.3)^2 - 0.001182*(z-14.3)^3
  : z < 33.3 ? 51.4 - 0.128781*(z-23) - 0.033055*(z-23)^2 + 0.000854*(z-23)^3
  : z < 58.5 ? 47.5 - 0.723569*(z-33.3) - 0.006664*(z-33.3)^2 + 0.000223*(z-33.3)^3
  : z < 80.7 ? 28.6 - 0.334254*(z-58.5) + 0.010181*(z-58.5)^2 - 0.000082*(z-58.5)^3
  : z < 97.6 ? 25.3 + 0.212872*(z-80.7) + 0.004719*(z-80.7)^2 - 0.00003*(z-80.7)^3
  : 30.1 + 0.456794*(z-97.6) + 0.003192*(z-97.6)^2 - 0.000048*(z-97.6)^3;

// R(z) with the short modern rim flare on the last LIP_H mm.
function R(z) =
  z > H - LIP_H
    ? R_spline(H - LIP_H)
      + (R_spline(H) - R_spline(H - LIP_H) + LIP) * (z - (H - LIP_H)) / LIP_H
    : R_spline(z);

function Rin(z) = R(z) - WALL;      // inner (cavity) surface
function band_in(z) = R(z) - SINK;  // flute band inner boundary (inside wall)
function band_out(z) = R(z) + RAISE;// flute band outer boundary

// ---- dense sampling of the curves (recursion builds point arrays) ---------
// n interior points strictly between z0 and z1.
function spts(z0, z1, n, i) =
  i >= n ? []
  : concat(
      [[ R(z0 + (i+1)*(z1-z0)/(n+1)), z0 + (i+1)*(z1-z0)/(n+1) ]],
      spts(z0, z1, n, i+1)
    );

function spts_in(z0, z1, n, i) =
  i >= n ? []
  : concat(
      [[ Rin(z0 + (i+1)*(z1-z0)/(n+1)), z0 + (i+1)*(z1-z0)/(n+1) ]],
      spts_in(z0, z1, n, i+1)
    );

function spts_b_in(z0, z1, n, i) =   // flute band, inner edge, z0 -> z1
  i >= n ? []
  : concat(
      [[ band_in(z0 + (i+1)*(z1-z0)/(n+1)), z0 + (i+1)*(z1-z0)/(n+1) ]],
      spts_b_in(z0, z1, n, i+1)
    );

function spts_b_out(z0, z1, n, i) =  // flute band, outer edge, z1 -> z0
  i >= n ? []
  : concat(
      [[ band_out(z1 - (i+1)*(z1-z0)/(n+1)), z1 - (i+1)*(z1-z0)/(n+1) ]],
      spts_b_out(z0, z1, n, i+1)
    );

// Closed 2D profiles in the XZ plane (x = radius).
function outer_pts(n) =
  concat( [[0, 0], [R(0), 0]], spts(0, H, n, 0), [[R(H), H], [0, H]] );

function cavity_pts(n) =
  concat( [[0, FLOOR], [Rin(FLOOR), FLOOR]], spts_in(FLOOR, H, n, 0),
          [[Rin(H), H], [0, H]] );

function band_pts(n) =
  concat(
    [[band_in(ZLO), ZLO]], spts_b_in(ZLO, ZHI, n, 0),
    [[band_in(ZHI), ZHI]], spts_b_out(ZLO, ZHI, n, 0),
    [[band_out(ZLO), ZLO]]
  );

// ---- construction ----------------------------------------------------------
module body() {
  rotate_extrude($fn = 96)
    polygon(points = outer_pts(44));
}

module cavity() {
  rotate_extrude($fn = 96)
    polygon(points = cavity_pts(44));
}

module rib_ring() {
  rotate_extrude($fn = 72)
    polygon(points = band_pts(30));
}

// One flute: the revolved surface band kept to a ~16-degree sector by a
// planar wedge, sunk SINK mm into the wall -> solid volumetric overlap.
module rib(deg) {
  rotate([0, 0, deg])
  intersection() {
    rib_ring();
    translate([-4, -WEDGE_W, -6])
      scale([WEDGE_LEN, 2*WEDGE_W, H + 12])
        cube([1, 1, 1], center = false);
  }
}

module vase() {
  difference() {
    union() {
      body();
      rib(30);
      rib(150);
      rib(270);
    }
    cavity();
  }
}

vase();
