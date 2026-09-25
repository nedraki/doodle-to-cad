"""Hybrid benchmark case: real downloaded STL -> derived hand-style doodle.

Provenance-first: we record the source URL + sha256 of the exact STL bytes and
never edit the mesh. A tiny SCAD wrapper normalizes the mesh into the canonical
frame (max extent -> target dimension mm, lowest point at Z=0), and the pipeline's
own Docker OpenSCAD cameras produce the ground-truth renders. The doodle sheet is
then drawn from those renders: outer silhouette + enclosed openings extracted with
the same CV primitives the evaluator uses, re-inked with the jittered hand style.

Usage:
  PYTHONPATH=<repo> DOODLE_OPENSCAD_DOCKER=openscad/openscad:latest \
    python benchmarks/tools/gen_hybrid_case.py --id 101_bltouch_bracket \
      --url https://.../bracket.STL --object "bltouch mounting bracket" \
      --views front,top,right --target 60 [--keep-stl cache/101.stl]

The wrapper scale is analytic (extent math from trimesh), so ground-truth
extents, STL and renders stay mutually consistent.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import random
import shutil
import sys
import urllib.request
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT.parent))  # repo root for `import doodle_to_cad`

from doodle_to_cad.evaluation import _profile_centroids, _decode  # noqa: E402
from doodle_to_cad.openscad import compile_and_render, mesh_health  # noqa: E402

SHEET_W, SHEET_H = 1024, 768
INK = (18, 18, 18)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def fetch(url: str, dest: Path) -> Path:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists() and dest.stat().st_size > 84:
        return dest
    req = urllib.request.Request(url, headers={"User-Agent": "benchmark-research/1.0"})
    with urllib.request.urlopen(req, timeout=60) as r:
        data = r.read()
    dest.write_bytes(data)
    return dest


def normalize_scad(stl_path: str | Path, import_name: str, target_mm: float) -> str:
    import trimesh
    m = trimesh.load(stl_path, process=False)
    ext = np.asarray(m.extents, float)
    scale = target_mm / float(ext.max())
    zmin = float(m.bounds[0][2])
    # translate so min-Z sits at the build plate; center XY on origin
    tx, ty = -float(m.bounds[0][0] + m.bounds[1][0]) / 2, -float(m.bounds[0][1] + m.bounds[1][1]) / 2
    return (
        f"// normalized wrapper for {import_name}\n"
        f"scale([{scale:.6f},{scale:.6f},{scale:.6f}])\n"
        f"  translate([{tx:.3f},{ty:.3f},{-zmin:.3f}])\n"
        f"    import(\"{import_name}\");\n"
    )


def contours_from_render(png: np.ndarray) -> tuple[np.ndarray, list[np.ndarray], list[tuple[float, float]]]:
    """Outer silhouette polygon + opening polygons/centroids (bbox-normalized)."""
    gray = cv2.cvtColor(png, cv2.COLOR_BGR2GRAY) if png.ndim == 3 else png
    border = np.concatenate((gray[0], gray[-1], gray[:, 0], gray[:, -1]))
    bg = float(np.median(border))
    ink = (np.abs(gray.astype(float) - bg) > 18).astype(np.uint8) * 255
    ink = cv2.morphologyEx(ink, cv2.MORPH_CLOSE, np.ones((3, 3), np.uint8))
    cnts, _ = cv2.findContours(ink, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not cnts:
        raise SystemExit("no silhouette found in render")
    outer_raw = max(cnts, key=cv2.contourArea)          # (N,1,2) int32
    outer = np.asarray(outer_raw).reshape(-1, 2).astype(float)
    x, y, w, h = cv2.boundingRect(outer_raw)
    openings: list[np.ndarray] = []
    sil = np.zeros_like(ink)
    cv2.drawContours(sil, [outer_raw], -1, 255, cv2.FILLED)
    enclosed = cv2.bitwise_and(sil, cv2.bitwise_not(ink))
    n, labels, stats, cents = cv2.connectedComponentsWithStats(enclosed, 8)
    for i in range(1, n):
        if stats[i, cv2.CC_STAT_AREA] < ink.size * 0.0005:
            continue
        if stats[i, cv2.CC_STAT_WIDTH] >= w * 0.95 and stats[i, cv2.CC_STAT_HEIGHT] >= h * 0.95:
            continue
        c = cv2.findContours((labels == i).astype(np.uint8) * 255, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)[0]
        if c:
            openings.append(np.asarray(c[0]).reshape(-1, 2).astype(float))
    return outer.astype(float), openings, []


def jitter_polyline(pts, rng, close=True):
    """Same spirit as gen_cases: resample + noise + slow wobble. pts: (N,2) float."""
    if close and len(pts) > 2:
        pts = np.vstack([pts, pts[:1]])
    d = np.sqrt(((np.diff(pts, axis=0)) ** 2).sum(1))
    total = float(d.sum())
    step = max(6.0, total / 160)
    out = [pts[0]]
    acc = 0.0
    for i in range(1, len(pts)):
        acc += d[i - 1]
        while acc >= step:
            t = 1 - (acc - step) / max(d[i - 1], 1e-6)
            out.append(pts[i - 1] + (pts[i] - pts[i - 1]) * t)
            acc -= step
    out.append(pts[-1])
    p = np.asarray(out, float)
    n = len(p)
    tt = np.linspace(0, 1, n)
    for axis in (0, 1):
        wob = float(rng.uniform(0.6, 1.6)) * np.sin(2 * np.pi * (float(rng.uniform(1, 2.2))) * tt + float(rng.uniform(0, 6.28)))
        p[:, axis] += wob + np.asarray([rng.gauss(0, 0.55) for _ in range(n)])
    return p


def draw_sheet(views: dict[str, dict], rng: random.Random) -> np.ndarray:
    """views: direction -> {outer: (N,2) pts, openings: [(M,2)...], aspect bbox w,h in px}.
    Third-angle style layout: front lower-center; top above; right to the side."""
    sheet = np.full((SHEET_H, SHEET_W, 3), 250, np.uint8)
    dirs = list(views)
    primary = "front" if "front" in views else dirs[0]
    # uniform sheet scale so all views share it (like real drafting)
    _, _, pw, ph = views[primary]["bbox"]
    scale = min(420.0 / max(pw, 1), 380.0 / max(ph, 1))
    # keep the vertical column (secondary above + gap + primary) on the sheet
    tH = max((views[d]["bbox"][3] for d in dirs if d in ("top", "bottom")), default=0.0)
    fH = ph
    budget = (SHEET_H - 60) / max(tH + fH + 130.0, 1.0)
    scale = min(scale, 4.0, budget)
    others = [d for d in dirs if d != primary]
    top_h = tH * scale
    pcy = int(24 + top_h + 130 + fH * scale / 2)
    pcx = SHEET_W // 2
    # fit the horizontal row (primary + right neighbour + margins) BEFORE stamping:
    # a right view whose centre falls off-sheet would be clipped in half.
    right_w = max((views[d]["bbox"][2] for d in others if d == "right"), default=0.0)
    left_w = max((views[d]["bbox"][2] for d in others if d == "left"), default=0.0)
    row_w = (right_w or left_w) and (pw * 0.5 + 150 + (right_w if right_w else left_w) * 1.0 + 24)
    if row_w:
        budget_h = (SHEET_W / 2 - 24) / max(row_w, 1.0)
        scale = min(scale, budget_h)
    # recompute column placement with final scale
    top_h = tH * scale
    pcy = int(24 + top_h + 130 + fH * scale / 2)

    def stamp(direction, cx, cy):
        v = views[direction]
        (bx, by, bw, bh) = v["bbox"]
        ox, oy = cx - bw * scale / 2 - bx * scale, cy - bh * scale / 2 - by * scale
        polys = [v["outer"]] + v["openings"]
        for poly in polys:
            q = poly.copy()
            q[:, 0] = q[:, 0] * scale + ox
            q[:, 1] = q[:, 1] * scale + oy
            cv2.polylines(sheet, [jitter_polyline(q, rng).astype(np.int32)], True, INK,
                          thickness=rng.choice([3, 3, 4]), lineType=cv2.LINE_AA)
        if rng.random() < 0.3:
            x = int(cx + rng.uniform(-30, 30))
            y = int(cy + rng.uniform(-20, 20))
            cv2.line(sheet, (x, y), (x + rng.randint(-9, 9), y + rng.randint(-9, 9)), INK, 2, cv2.LINE_AA)

    stamp(primary, pcx, pcy)
    for d in others:
        bw, bh = views[d]["bbox"][2], views[d]["bbox"][3]
        if d in ("top", "bottom"):
            stamp(d, pcx, int(30 + bh * scale / 2))
        elif d == "right":
            stamp(d, int(pcx + pw * scale / 2 + 150 + bw * scale / 2), pcy)
        elif d == "left":
            stamp(d, int(pcx - pw * scale / 2 - 150 - bw * scale / 2), pcy)
        else:
            stamp(d, 850, int(30 + bh * scale / 2))
    return sheet


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("--id", required=True)
    ap.add_argument("--url", required=True)
    ap.add_argument("--object", required=True)
    ap.add_argument("--views", default="front,top,right")
    ap.add_argument("--target", type=float, default=80.0)
    ap.add_argument("--seed", type=int, default=None)
    ap.add_argument("--family", default="real_mesh_derived")
    args = ap.parse_args(argv)

    case = ROOT / "cases" / args.id
    case.mkdir(parents=True, exist_ok=True)
    (case / "source").mkdir(exist_ok=True)
    (case / "derived").mkdir(exist_ok=True)
    (case / "ground_truth").mkdir(exist_ok=True)

    cache = ROOT / "cache" / f"{args.id}.stl"
    fetch(args.url, cache)
    stl_sha = sha256(cache)
    shutil.copy2(cache, case / "ground_truth" / "source.stl")

    # GT record: wrapper next to ground_truth/source.stl (human-readable twin of
    # what actually gets compiled from derived/ with the Docker OpenSCAD).
    (case / "ground_truth" / "model.scad").write_text(normalize_scad(cache, "source.stl", args.target))
    build_scad = case / "derived" / "model.scad"
    shutil.copy2(cache, case / "derived" / cache.name)
    build_scad.write_text(normalize_scad(cache, cache.name, args.target))
    ok, views_png, log = compile_and_render(build_scad, case / "derived", "openscad")
    gt_stl = case / "derived" / "model.stl"
    if not ok or gt_stl is None or not any(v.exists() for v in views_png.values()):
        print(json.dumps({"id": args.id, "status": "compile_failed", "log": log[-400:]}))
        return 1
    shutil.copy2(gt_stl, case / "ground_truth" / "model.stl")
    health = mesh_health(case / "ground_truth" / "model.stl")

    dirs = [d for d in args.views.split(",") if d in views_png]
    sheet_views = {}
    for d in dirs:
        png = _decode(views_png[d].read_bytes())
        outer, openings, _ = contours_from_render(png)
        x0, y0 = outer.min(0)
        w, h = (outer.max(0) - outer.min(0))
        sil = outer - outer.min(0)
        openings_local = [(o - outer.min(0)) for o in openings]
        sheet_views[d] = {"outer": sil, "openings": openings_local, "bbox": (0, 0, float(w), float(h))}

    rng = random.Random(args.seed if args.seed is not None else abs(hash(args.id)) % (2 ** 31))
    sheet = draw_sheet(sheet_views, rng)
    (case / "source" / "drawing.png").write_bytes(cv2.imencode(".png", sheet)[1].tobytes())

    gt_scad = case / "ground_truth" / "model.scad"
    gt_model = case / "ground_truth" / "model.stl"
    drawing = case / "source" / "drawing.png"
    manifest = {
        "schema_version": 1,
        "id": args.id,
        "split": "development",
        "status": "active",
        "object": args.object,
        "semantic_labels": {"object": args.object, "family": args.family},
        "provenance": {"source_url": args.url, "stl_sha256": stl_sha,
                       "note": "real mesh; doodle derived from pipeline-camera renders of the normalized GT",
                       "sha256": {"drawing.png": sha256(drawing),
                                  "model.scad": sha256(gt_scad),
                                  "model.stl": sha256(gt_model)}},
        "reference": {"dimensions_mm": {"extents_xyz": [round(v, 2) for v in health["extents_mm"]]},
                      "topology": {"watertight": bool(health["watertight"]),
                                   "components": int(health["components"])}},
        "target_dimension_mm": args.target,
        "print_envelope_mm": 256.0,
        "controls": {"primary_view": "front" if "front" in dirs else dirs[0],
                     "projection_standard": "third-angle",
                     "object_type_hint": args.object},
        "views": [{"direction": d, "region": "auto"} for d in dirs],
        "style_note": "hybrid: silhouette+openings lifted from GT renders, re-inked with jittered hand style",
        "files": {"drawing": "source/drawing.png", "gt_scad": "ground_truth/model.scad",
                  "gt_stl": "ground_truth/model.stl", "gt_source_stl": "ground_truth/source.stl"},
    }
    (case / "manifest.json").write_text(json.dumps(manifest, indent=2))
    print(json.dumps({"id": args.id, "status": "active",
                      "extents": manifest["reference"]["dimensions_mm"]["extents_xyz"],
                      "openings": {d: len(v["openings"]) for d, v in sheet_views.items()},
                      "watertight": health["watertight"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
