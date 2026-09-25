"""Coordinate contract probe v3 — measure the TRUE camera mappings.

For each pipeline camera (front/top/right), determine where world +X, +Y, +Z
land on the rendered sheet (u right, v down), using decisive notch markers.
Output feeds a comparison against geometry.py axis_contracts + the camera
strings in openscad.py. No theory, only measurements.
"""
from __future__ import annotations
import sys
from pathlib import Path
import numpy as np
import cv2
sys.path.insert(0, str(Path(__file__).resolve().parent))
from doodle_to_cad.openscad import compile_and_render

# 80(X) x 40(Y) x 20(Z) plate centered at origin.
# M1: notch cutting the +X end, full height, only front half (y=-20..0), 12 deep in X.
#     front view: deficit on u=+X side or -X side (lower half)
#     top view: deficit at u=+X or -X side (half-depth)
M1 = """
difference() {
  cube([80,40,20], center=true);
  translate([16,-21,-11]) cube([25,21,22]);
}
"""
# M2: notch at +Y edge (back), centered in X, full height, 6 deep in Y.
#     top view: deficit at v top or bottom edge -> sign of v mapping
#     right view: deficit at u side -> sign of u mapping
M2 = """
difference() {
  cube([80,40,20], center=true);
  translate([-6,14,-11]) cube([12,8,22]);
}
"""
# M3: notch removing top-back strip (full X, y=+10..20, z=+8..10 top).
#     front view: deficit at v top or bottom edge -> sign of v (Z) mapping
#     right view: L-shape; tells combined orientation
M3 = """
difference() {
  cube([80,40,20], center=true);
  translate([-41,10,8]) cube([82,11,4]);
}
"""
# PLAIN reference for aspect baselines
PLAIN = "cube([80,40,20], center=true);"

def measures(png: Path):
    img = cv2.imread(str(png), cv2.IMREAD_COLOR)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    border = np.concatenate((gray[0], gray[-1], gray[:, 0], gray[:, -1]))
    bg = int(np.median(border))
    ink = (np.abs(gray.astype(int) - bg) > 18).astype(np.uint8) * 255
    contours, _ = cv2.findContours(ink, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours: return None
    outer = max(contours, key=cv2.contourArea)
    x, y, w, h = cv2.boundingRect(outer)
    sil = np.zeros_like(ink); cv2.drawContours(sil, [outer], -1, 255, cv2.FILLED)
    # edge profile: per-column fill height (for top/bottom notch detection) and
    # per-row fill width (for left/right notch detection), sampled at 20 bins
    cols = []
    for i in range(20):
        c0 = x + int(w * i / 20); c1 = x + int(w * (i + 1) / 20)
        band = sil[y:y+h, c0:c1]
        colfill = [ (band[:, j] > 0).mean() for j in range(band.shape[1]) ]
        cols.append(round(float(np.mean(colfill)), 3))
    rows = []
    for i in range(20):
        r0 = y + int(h * i / 20); r1 = y + int(h * (i + 1) / 20)
        band = sil[r0:r1, x:x+w]
        rowfill = [ (band[i2, :] > 0).mean() for i2 in range(band.shape[0]) ]
        rows.append(round(float(np.mean(rowfill)), 3))
    return {"w": w, "h": h, "aspect": round(w / h, 3), "cols_left_to_right": cols, "rows_top_to_bottom": rows}

def main():
    d = Path("/tmp/coord-exp3")
    for tag, scad, expect in (
        ("PLAIN", PLAIN, "aspect baselines: front(=X*Z)=4.0 top(=X*Y)=2.0 right(=Y*Z)=2.0"),
        ("M1", M1, "notch @ +X: which side (cols) loses fill, in front & top renders?"),
        ("M2", M2, "notch @ +Y: which edge (rows in top / cols in right) loses fill?"),
        ("M3", M3, "notch @ +Z+Y: which edge (rows in front / cols+rows in right) loses fill?"),
    ):
        dd = d / tag; dd.mkdir(parents=True, exist_ok=True)
        (dd / "model.scad").write_text(scad)
        stl, views, log = compile_and_render(dd / "model.scad", dd, "openscad")
        if not stl:
            print(f"{tag}: COMPILE FAILED", log[-300:]); continue
        print(f"\n== {tag} :: {expect}")
        for name in ("front", "top", "right"):
            p = dd / f"view-{name}.png"
            m = measures(p) if p.exists() else None
            print(f"  {name}: {m}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
