"""Increment-9 evidence: adaptive-view quinttyptchs (drawing | built V | GT V |
built iso | GT iso), where V is the most DIAGNOSTIC registered view per case,
chosen by a generic machine rule — never by hand.

Rule (no shape knowledge): for each candidate direction (front, right, top),
score = rendered internal profiles (holes/slots/windows the gate itself
counts) summed over built and GT renders; highest score wins; ties break on
GT silhouette area (more informative outline), then front>right>top. If no
view carries internal features, the largest-GT-silhouette view is used.
The chosen view is printed in the caption so the choice is auditable.

Usage: make_evidence.py <run_dir> <results_root> <repo_root> <out_prefix> [rows_per_fig]
"""
from __future__ import annotations
import json, sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from doodle_to_cad.evaluation import _normalized_profile, _decode

CELL_W, CELL_H, PAD, CAP_H = 250, 220, 8, 78
CANDIDATES = ("front", "right", "top")


def load_font(size: int):
    for p in ("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",):
        if Path(p).exists():
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()


def view_stats(path: Path):
    img = _decode(path.read_bytes()) if path.exists() else None
    if img is None:
        return None
    mask, holes = _normalized_profile(img, render=True)
    import numpy as np
    return {"holes": holes, "area": int(np.count_nonzero(mask))}


def pick_view(built_dir: Path, gt_dir: Path):
    scored = []
    for rank, d in enumerate(CANDIDATES):
        b, g = view_stats(built_dir / f"view-{d}.png"), view_stats(gt_dir / f"view-{d}.png")
        if b is None or g is None:
            continue
        scored.append((b["holes"] + g["holes"], g["area"], -rank, d, b["holes"], g["holes"]))
    if not scored:
        return "front", 0, 0
    scored.sort(reverse=True)
    _, _, _, d, bh, gh = scored[0]
    return d, bh, gh


def fit(img, w, h):
    img = img.convert("RGB"); img.thumbnail((w, h)); return img


def main() -> int:
    run_dir, results_root, repo = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
    out_prefix, per_fig = sys.argv[4], int(sys.argv[5]) if len(sys.argv) > 5 else 6
    f_big, f_small = load_font(15), load_font(13)
    cases = sorted(d for d in run_dir.iterdir() if (d / "trial-1" / "verdict.json").exists())
    rows, chosen = [], {}
    for cd in cases:
        v = json.loads((cd / "trial-1" / "verdict.json").read_text())
        case, run_id = cd.name, v.get("run_id")
        built_dir = results_root / run_id if run_id else Path("/nonexistent")
        gt_dir = repo / "benchmarks" / "cases" / case / "derived"
        drawing = repo / "benchmarks" / "cases" / case / "source" / "drawing.png"
        view, bh, gh = pick_view(built_dir, gt_dir)
        chosen[case] = {"view": view, "built_holes": bh, "gt_holes": gh}
        checks = v.get("checks") or {}
        res = json.loads((cd / "trial-1" / "result.json").read_text()) if (cd / "trial-1" / "result.json").exists() else {}
        built_v = (res.get("mesh_health") or {}).get("volume_mm3")
        gt_stl = repo / "benchmarks" / "cases" / case / "ground_truth" / "model.stl"
        gt_v = None
        if gt_stl.exists():
            import trimesh
            gt_v = float(trimesh.load(str(gt_stl), force="mesh").volume)
        vratio = (built_v / gt_v) if built_v and gt_v else None
        gs = v.get("gates_state") or {}
        fails = [k for k, s in gs.items() if s == "fail"]
        sims = [s for s in (v.get("projection_similarity") or {}).values() if s is not None]
        cap1 = (f"{case}  accepted={v.get('accepted')} verified={v.get('verified_acceptance')}"
                f"  genus {v.get('genus_total')}/{v.get('gt_genus')} genus_pass={checks.get('genus_pass')}")
        cap2 = (f"view '{view}' chosen: built {bh} vs GT {gh} internal profiles  ·"
                f"  failed_gates {fails or '-'}  unmeasured {v.get('unverified_gates') or '-'}")
        vr_txt = ("-" if vratio is None else
                  f"{vratio:.2f}x {'PASS' if abs(vratio-1)<=0.25 else 'FAIL'}")
        cap3 = (f"front_sim {max(sims) if sims else '-'}  volume built/GT {vr_txt}"
                f"  dims_axiswise_pass={checks.get('dims_axiswise_pass')}"
                f"  built_ext {[round(x,1) for x in (v.get('extents_mm') or [])]}"
                f"  gt_ext {[round(x,1) for x in (v.get('gt_stl_extents_sorted') or [])]}")
        panels = [("drawing", drawing), (f"built {view}", built_dir / f"view-{view}.png"),
                  (f"GT {view}", gt_dir / f"view-{view}.png"),
                  ("built iso", built_dir / "view-isometric.png"), ("GT iso", gt_dir / "view-isometric.png")]
        fig = Image.new("RGB", (5 * CELL_W + 6 * PAD, CELL_H + CAP_H + 2 * PAD), (18, 18, 22))
        d = ImageDraw.Draw(fig)
        for i, (label, src) in enumerate(panels):
            if Path(src).exists():
                im = fit(Image.open(src), CELL_W - 6, CELL_H - 24)
            else:
                im = Image.new("RGB", (CELL_W - 6, CELL_H - 24), (24, 24, 28))
                ImageDraw.Draw(im).text((10, 90), f"NO {label}", font=f_small, fill=(240, 120, 120))
            x = PAD + i * (CELL_W + PAD)
            fig.paste(im, (x + (CELL_W - im.width) // 2, PAD + 20))
            d.text((x + 4, 2), label, font=f_small, fill=(150, 200, 255))
        d.text((PAD + 2, CELL_H + PAD), cap1, font=f_big, fill=(235, 235, 235))
        d.text((PAD + 2, CELL_H + PAD + 22), cap2, font=f_small, fill=(170, 220, 255))
        d.text((PAD + 2, CELL_H + PAD + 42), cap3, font=f_small, fill=(255, 200, 120))
        rows.append(fig)
    for i in range(0, len(rows), per_fig):
        chunk = rows[i:i + per_fig]
        canvas = Image.new("RGB", (max(r.width for r in chunk),
                                   sum(r.height for r in chunk) + PAD * (len(chunk) + 1)), (12, 12, 15))
        y = PAD
        for r in chunk:
            canvas.paste(r, (0, y)); y += r.height + PAD
        out = f"{out_prefix}-{i // per_fig + 1}.png"
        canvas.save(out)
        print("wrote", out)
    print("view choices:", json.dumps(chosen, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
