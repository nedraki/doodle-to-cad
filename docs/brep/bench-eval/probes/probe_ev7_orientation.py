# Probe EV-7 (issue #81): orientation-normalized fidelity upper bound.
# For rows where fidelity failed on a correct part, does ANY of the 24 cubic
# rotations of the built STL reach the harness similarity bar (>=0.45) when
# its silhouette is compared against the drawing's assigned view-group crops?
# Rasterization: orthographic silhouette of triangles via PIL polygon fill.
# Comparison: foreground IoU against _normalized_profile(draw crop) mask.
import json, sys
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw
ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
from doodle_to_cad.evaluation import _decode, _normalized_profile, assign_view_groups
from doodle_to_cad.feature_evidence import view_assignment_evidence
import trimesh

RUNS = ROOT / "docs/brep/bench-final/runs"
VIEW_AXES = {  # direction -> (u_axis, v_axis, depth_axis)
    "front": (0, 2, 1), "back": (0, 2, 1),
    "top": (0, 1, 2), "bottom": (0, 1, 2),
    "left": (1, 2, 0), "right": (1, 2, 0),
}

def cube_rotations():
    from itertools import product
    base = [np.array(v, float) for v in (
        (1,0,0),(0,1,0),(0,0,1),(-1,0,0),(0,-1,0),(0,0,-1))]
    seen, uniq = set(), []
    for x, z in product(base, repeat=2):
        if abs(x @ z) > 0.5: continue
        y = np.cross(z, x)
        R = np.stack([x, y, z], axis=1)
        if round(np.linalg.det(R)) != 1: continue
        key = tuple(R.round(3).astype(int).ravel())
        if key not in seen:
            seen.add(key); uniq.append(R)
    return uniq

def silhouette(v, faces, ua, va, size=128):
    span = max((v[:, ua].max() - v[:, ua].min()), (v[:, va].max() - v[:, va].min())) * 1.02
    cu = (v[:, ua].max() + v[:, ua].min()) / 2
    cv = (v[:, va].max() + v[:, va].min()) / 2
    img = Image.new("L", (size, size), 0)
    d = ImageDraw.Draw(img)
    tris = v[:, [ua, va]][faces]
    for tri in tris:
        u = (tri[:, 0] - cu) / span + 0.5
        w_ = (tri[:, 1] - cv) / span + 0.5
        d.polygon([c for uu, ww in zip(u, w_) for c in (uu * size, size - ww * size)], fill=255)
    return np.array(img) > 127

def iou(a, b):
    inter = int(np.logical_and(a, b).sum()); union = int(np.logical_or(a, b).sum())
    return float(inter / union) if union else 0.0

def find_item(o, want):
    if isinstance(o, dict):
        if o.get("id") == want: return o
        for v in o.values():
            r = find_item(v, want)
            if r: return r
    if isinstance(o, list):
        for v in o:
            r = find_item(v, want)
            if r: return r

plan = json.loads((RUNS.parent / "TRIAL-PLAN.json").read_text())
rows = [
    ("004_flat_mounting_plate", "usd-brep", 1),
    ("004_flat_mounting_plate", "openscad", 1),
    ("wheel", "usd-brep", 2),
]
MATS = cube_rotations()
for drawing, backend, trial in rows:
    cell = RUNS / drawing / backend / f"trial-{trial:02d}"
    row = json.loads((cell / "row.json").read_text())
    item = find_item(plan, drawing)
    full = _decode((ROOT / item["drawing"]).read_bytes())
    h, w = full.shape[:2]
    res = json.loads((cell / "result.json").read_text())
    evidence = res.get("geometry")
    if backend == "usd-brep":
        evidence = view_assignment_evidence(json.loads((cell / "geometry.json").read_text()))
    assigned = assign_view_groups(evidence or {}, item["primary_view"], "third-angle")
    m = trimesh.load(str(cell / "stl" / "model.stl"), force="mesh")
    verts = np.asarray(m.vertices, float); faces = np.asarray(m.faces, int)
    parts = [f"{drawing}/{backend}/t{trial} harness_fid={row['checks'].get('fidelity_pass')} "
             f"scores={row['fidelity'].get('scores')} ntri={len(faces)}"]
    for direction, g in assigned.items():
        x, y, gw, gh = g["bbox_normalized"]
        x0, y0 = max(0, int(x * w)), max(0, int(y * h))
        x1, y1 = min(w, int((x + gw) * w)), min(h, int((y + gh) * h))
        ref = np.asarray(_normalized_profile(full[y0:y1, x0:x1], render=False)[0]) > 0
        ua, va, da = VIEW_AXES.get(direction, (0, 2, 1))
        best, mean = 0.0, []
        for R in MATS:
            vr = verts @ R.T
            sm = silhouette(vr, faces, ua, va)
            sm = np.array(Image.fromarray(sm.astype(np.uint8) * 255).resize(
                (ref.shape[1], ref.shape[0]))) > 127
            s = iou(ref, sm); mean.append(s); best = max(best, s)
        parts.append(f"{direction}: harness={row['fidelity']['scores'].get(direction)} "
                     f"best={best:.2f} mean={np.mean(mean):.2f}")
    print(" | ".join(parts))
