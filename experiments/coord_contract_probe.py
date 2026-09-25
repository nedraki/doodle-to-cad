"""Coordinate contract probe v2 — decisive single-marker measurements.

Part A: 80x40x20 plate, one 8mm hole at X=+25 (through Z).
  - If front-view camera obeys contract (u->+X), the hole centroid appears
    RIGHT of silhouette center; if mirrored, LEFT.
  - Top view likewise should show the hole on the +X side per contract.
Part B: 80x40x20 plate with a 12-wide notch cut into the +Y edge (y=+14..+20).
  - Per contract, top view has v->+Y (down), so the notch must appear at the
    BOTTOM edge of the top render; right view u->+Y => notch on the RIGHT.
"""
from __future__ import annotations
import sys
from pathlib import Path
import numpy as np
import cv2
sys.path.insert(0, str(Path(__file__).resolve().parent))
from doodle_to_cad.openscad import compile_and_render

PART_A = """
difference() {
  cube([80,40,20], center=true);
  translate([25,0,-11]) cylinder(d=8,h=22);
}
"""
PART_B = """
difference() {
  cube([80,40,20], center=true);
  translate([-6,14,-11]) cube([12,10,22]);
}
"""
PART_C = """
// boss only near +Z top face => in front render it must appear on TOP
// (contract v_maps_to -Z means: v increases downward = Z decreases upward)
union() {
  cube([80,40,20], center=true);
  translate([-8,-8,10]) cube([16,16,6]);
}
"""

def silhouette_and_holes(png: Path):
    img = cv2.imread(str(png), cv2.IMREAD_COLOR)
    assert img is not None, png
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    border = np.concatenate((gray[0], gray[-1], gray[:, 0], gray[:, -1]))
    bg = int(np.median(border))
    ink = (np.abs(gray.astype(int) - bg) > 18).astype(np.uint8) * 255
    # outer silhouette = largest contour
    contours, _ = cv2.findContours(ink, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    outer = max(contours, key=cv2.contourArea)
    sil = np.zeros_like(ink); cv2.drawContours(sil, [outer], -1, 255, cv2.FILLED)
    xs, ys = np.nonzero(sil)
    x0, y0, x1, y1 = xs.min(), ys.min(), xs.max(), ys.max()
    w, h = max(x1 - x0, 1), max(y1 - y0, 1)
    # enclosed background inside silhouette = holes
    enclosed = cv2.bitwise_and(sil, cv2.bitwise_not(ink))
    n = cv2.connectedComponentsWithStats(enclosed, 8)
    count, stats, cents = n[0], n[1], n[2]
    holes = []
    for i in range(1, count):
        if stats[i, cv2.CC_STAT_AREA] < (sil.size * 0.0008):
            continue
        cu, cv_ = cents[i]
        holes.append((round((cu - x0) / w, 3), round((cv_ - y0) / h, 3), int(stats[i, cv2.CC_STAT_AREA])))
    return sil, (x0, y0, x1, y1), holes

def edge_deficit(sil, box, side):
    """fraction of missing silhouette pixels along one normalized edge band"""
    x0, y0, x1, y1 = box; w, h = x1 - x0, y1 - y0
    band = max(3, int(h * 0.12)) if side in ("top", "bottom") else max(3, int(w * 0.12))
    if side == "top":    row = sil[y0:y0+band, x0:x1];  ref = w
    if side == "bottom": row = sil[y1-band:y1+1, x0:x1]; ref = w
    if side == "left":   row = sil[y0:y1, x0:x0+band];  ref = h
    if side == "right":  row = sil[y0:y1, x1-band:x1+1]; ref = h
    fill = (row > 0).sum(axis=1).mean()
    return round(1 - fill / (band if side in ("top","bottom") else band), 3), round(fill/ref,3)

def main():
    d = Path("/tmp/coord-exp2")
    for tag, scad, tests in (
        ("A", PART_A, "hole at +X: expect hole centroid u>0.5 in front & top (contract)"),
        ("B", PART_B, "notch at +Y: expect deficit at BOTTOM of top (v->+Y down) and RIGHT of right (u->+Y)"),
        ("C", PART_C, "boss on +Z top: front view must show NARROW rows at TOP of silhouette (boss), wide at bottom"),
    ):
        dd = d / tag; dd.mkdir(parents=True, exist_ok=True)
        (dd / "model.scad").write_text(scad)
        stl, views, log = compile_and_render(dd / "model.scad", dd, "openscad")
        if not stl:
            print(f"PART {tag} COMPILE FAILED:", log[-400:]); continue
        print(f"\n== PART {tag}: {tests}")
        for name in ("front", "top", "right"):
            p = dd / f"view-{name}.png"
            if not p.exists(): print(f"  {name}: MISSING"); continue
            sil, box, holes = silhouette_and_holes(p)
            deficits = {s: edge_deficit(sil, box, s) for s in ("top", "bottom", "left", "right")}
            print(f"  {name}: holes(u,v,area)={holes}  edge_deficits={deficits}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
