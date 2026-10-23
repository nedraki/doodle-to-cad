#!/usr/bin/env python3
"""Re-ink a user-supplied doodle from its own ground-truth STL (issue #68 data fix).

User-supplied benchmark drawings can carry ink proportions that contradict the
reference STL (case 003: the edge strip reads ~20 mm thick while the STL is
3 mm). This tool redraws the sheet FROM the trusted STL: a mid-thickness slice
gives the true outer silhouette plus every through-opening; the top view is
the true bounding strip. Both views share one px/mm scale, so the ink and the
reference pair up. Stroke jitter keeps the hand-drawn look; jitter stays
small enough that the evaluator's circularity and profile gates still fire.

Usage:
  PYTHONPATH=<repo> python benchmarks/tools/gen_doodle_from_stl.py \
    --stl ground_truth/model.stl --out derived/drawing-adapted.png \
    [--sheet 706 619] [--scale 4.0] [--seed 3]

The slice is implemented with numpy only (no scipy): intersect triangles with
the plane, then chain segments into closed loops.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import random
from pathlib import Path

import cv2
import numpy as np
import trimesh

INK = (18, 18, 18)


def horizontal_slice(mesh: trimesh.Trimesh, z: float) -> list[np.ndarray]:
    """Return closed loops (N,2 xy arrays) of the mesh cross-section at z."""
    v = mesh.vertices
    f = mesh.faces
    zc = v[f, 2]  # (T,3)
    above, below = zc > z, zc < z
    crossing = (above.any(1) & below.any(1))
    segs = []
    idx = np.nonzero(crossing)[0]
    for t in idx:
        pts = v[f[t]]
        zs = zc[t]
        hits = []
        for a, b in ((0, 1), (1, 2), (2, 0)):
            za, zb = zs[a], zs[b]
            if (za - z) == 0 or (zb - z) == 0:
                continue
            if (za > z) != (zb > z):
                frac = (z - za) / (zb - za)
                hits.append(pts[a] + frac * (pts[b] - pts[a]))
        if len(hits) == 2:
            segs.append((hits[0][:2], hits[1][:2]))
    # chain segments into loops using a rounded-endpoint map
    key = lambda p: (round(float(p[0]), 5), round(float(p[1]), 5))
    # Adjacent triangles sharing an edge on the plane each emit the same cut
    # segment; duplicates make the greedy chain below zig-zag them into
    # back-and-forth scribbles. Dedupe by unordered endpoint pair first.
    seen = set()
    unique = []
    for a, b in segs:
        ka, kb = key(a), key(b)
        sig = (ka, kb) if ka <= kb else (kb, ka)
        if sig in seen or ka == kb:
            continue
        seen.add(sig)
        unique.append((a, b))
    segs = unique
    adj: dict = {}
    for i, (a, b) in enumerate(segs):
        adj.setdefault(key(a), []).append((i, "ab"))
        adj.setdefault(key(b), []).append((i, "ba"))
    used = [False] * len(segs)
    loops = []
    for i in range(len(segs)):
        if used[i]:
            continue
        used[i] = True
        pts = list(segs[i])
        for end in ("b", "a"):
            cur = pts[-1] if end == "b" else pts[0]
            while True:
                nxt = [(j, d) for (j, d) in adj[key(cur)] if not used[j]]
                if not nxt:
                    break
                j, d = nxt[0]
                used[j] = True
                a, b = segs[j]
                add = b if d == "ab" else a
                if end == "b":
                    pts.append(add)
                else:
                    pts.insert(0, add)
                cur = add
        if end == "a":
            pts = pts[::-1]
        loops.append(np.asarray(pts))
    return loops


def jitter(pts: np.ndarray, rng: random.Random, sigma: float) -> np.ndarray:
    n = len(pts)
    if n < 3:
        return pts
    t = np.linspace(0, 1, n)
    out = pts.astype(float).copy()
    amp = sigma * 1.6
    k1 = rng.uniform(1.0, 2.5) * 2 * np.pi
    k2 = rng.uniform(2.5, 4.0) * 2 * np.pi
    p1, p2 = rng.uniform(0, 6.28), rng.uniform(0, 6.28)
    out[:, 0] += amp * np.sin(k1 * t + p1) + rng.gauss(0, sigma) * np.sin(k2 * t + p2)
    out[:, 1] += amp * np.sin(k2 * t + p2) + rng.gauss(0, sigma) * np.sin(k1 * t + p1)
    return out


def resample(pts: np.ndarray, step: float = 6.0) -> np.ndarray:
    d = np.r_[0.0, np.cumsum(np.linalg.norm(np.diff(pts, axis=0), axis=1))]
    n = max(int(d[-1] // step), 8)
    t = np.linspace(0, d[-1], n)
    return np.c_[np.interp(t, d, pts[:, 0]), np.interp(t, d, pts[:, 1])]


def draw(canvas: np.ndarray, loop: np.ndarray, offset, rng, sigma=1.2, color=INK, width=3):
    pts = resample(loop + np.asarray(offset))
    pts = jitter(pts, rng, sigma)
    cv2.polylines(canvas, [np.round(pts).astype(np.int32)], True, color, width, cv2.LINE_AA)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stl", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--sheet", nargs=2, type=int, default=[706, 619])
    ap.add_argument("--scale", type=float, default=4.0)
    ap.add_argument("--seed", type=int, default=3)
    args = ap.parse_args()

    mesh = trimesh.load(args.stl, process=False)
    lo, hi = mesh.bounds
    zmid = (lo[2] + hi[2]) / 2
    loops = horizontal_slice(mesh, zmid)
    assert loops, "empty slice"
    areas = [abs(cv2.contourArea(l.astype(np.float32))) for l in loops]
    outer = int(np.argmax(areas))

    rng = random.Random(args.seed)
    W, H = args.sheet
    sheet = np.full((H, W, 3), 255, np.uint8)
    scale = args.scale

    fw, fh = (hi[0] - lo[0]) * scale, (hi[1] - lo[1]) * scale
    depth = hi[2] - lo[2]

    # FRONT view bottom-centre, TOP-view strip directly above it (same x span).
    fx = (W - fw) / 2
    fy = H - fh - 40
    draw(sheet, (loops[outer] - lo[:2]) * scale + np.array([fx, fy]), (0, 0), rng)
    for i, l in enumerate(loops):
        if i == outer:
            continue
        # thin ink + low jitter: a 3.5 mm GT slot at 4 px/mm is 14 px wide and
        # stays open only if the two 2 px strokes do not merge.
        draw(sheet, (l - lo[:2]) * scale + np.array([fx, fy]), (0, 0), rng,
             sigma=0.6, width=2)

    strip_h = max(round(depth * scale), 3)
    sx, sy = fx, fy - strip_h - 70
    rect = np.array([[0, 0], [fw, 0], [fw, strip_h], [0, strip_h]], float)
    draw(sheet, rect, (sx, sy), rng, sigma=0.5)

    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(args.out, sheet)
    info = {"stl": str(args.stl), "stl_sha256": hashlib.sha256(Path(args.stl).read_bytes()).hexdigest(),
            "scale_px_per_mm": scale, "outer_loops": 1, "inner_loops": len(loops) - 1,
            "sheet": [W, H], "seed": args.seed,
            "through_openings_in_front_view": len(loops) - 1,
            "top_strip_px": [round(fw), strip_h]}
    print(json.dumps(info, indent=2))


if __name__ == "__main__":
    main()
