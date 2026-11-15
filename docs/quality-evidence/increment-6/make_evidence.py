"""Increment-6 evidence: per-case triptych (drawing | built front | GT front)
with machine-number captions. Built renders come from the product's own
results/<run_id>/ — never re-rendered by hand; abort on missing run_id.

Usage: make_evidence.py <run_dir> <results_root> <repo_root> <out_prefix> [rows_per_fig]
"""
from __future__ import annotations
import json, sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

CELL_W, CELL_H, PAD, CAP_H = 300, 260, 10, 78

def load_font(size: int):
    for p in ("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
              "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"):
        if Path(p).exists():
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()

def fit(img: Image.Image, w: int, h: int) -> Image.Image:
    img = img.convert("RGB")
    img.thumbnail((w, h))
    return img

def fmt_ratios(ext, gt):
    if not ext or not gt:
        return "-"
    a = sorted((float(v) for v in ext), reverse=True)
    b = sorted((float(v) for v in gt), reverse=True)
    return "[" + ",".join(f"{x/y:.2f}" for x, y in zip(a, b)) + "]"

def main() -> int:
    run_dir, results_root, repo = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
    out_prefix, per_fig = sys.argv[4], int(sys.argv[5]) if len(sys.argv) > 5 else 6
    f_big, f_small = load_font(17), load_font(15)
    cases = sorted(d for d in run_dir.iterdir() if (d / "trial-1" / "verdict.json").exists())
    figs, rows = 0, []
    for cd in cases:
        v = json.loads((cd / "trial-1" / "verdict.json").read_text())
        case = cd.name
        drawing = repo / "benchmarks" / "cases" / case / "source" / "drawing.png"
        gt_view = repo / "benchmarks" / "cases" / case / "derived" / "view-front.png"
        run_id = v.get("run_id")
        built = results_root / run_id / "view-front.png" if run_id else None
        checks = v.get("checks") or {}
        gs = v.get("gates_state") or {}
        fails = [k for k, s in gs.items() if s == "fail"]
        sims = [s for s in (v.get("projection_similarity") or {}).values() if s is not None]
        cap1 = (f"{case}  accepted={v.get('accepted')} verified={v.get('verified_acceptance')}"
                f"  genus {v.get('genus_total')}/{v.get('gt_genus')}"
                f" genus_pass={checks.get('genus_pass')}")
        cap3 = (f"dims_sorted_ratio {fmt_ratios(v.get('extents_mm'), v.get('gt_stl_extents_sorted') or v.get('gt_extents_mm'))}"
                f" dims_axiswise_pass={checks.get('dims_axiswise_pass')}"
                f"  built_ext {[round(x,1) for x in (v.get('extents_mm') or [])]}"
                f"  gt_ext {[round(x,1) for x in (v.get('gt_stl_extents_sorted') or v.get('gt_extents_mm') or [])]}")
        cap2 = (f"front_sim {max(sims) if sims else '-'}"
                f"  failed_gates {fails or '-'}  unmeasured {v.get('unverified_gates') or '-'}"
                f"  inv {v.get('inverted_solids')}  cache hits {(v.get('cache_stats') or {}).get('hits')}")
        panels = []
        for src, label in ((drawing, "drawing"), (built, "built front"), (gt_view, "GT front")):
            if src and Path(src).exists():
                panels.append((label, Image.open(src)))
            else:
                blank = Image.new("RGB", (CELL_W, CELL_H), (24, 24, 28))
                d = ImageDraw.Draw(blank)
                d.text((12, CELL_H // 2 - 10), f"NO {label}", font=f_big, fill=(240, 120, 120))
                panels.append((label, blank))
        fig = Image.new("RGB", (3 * CELL_W + 4 * PAD, CELL_H + CAP_H + 2 * PAD), (18, 18, 22))
        d = ImageDraw.Draw(fig)
        for i, (label, im) in enumerate(panels):
            im = fit(im, CELL_W - 6, CELL_H - 24)
            x = PAD + i * (CELL_W + PAD)
            fig.paste(im, (x + (CELL_W - im.width) // 2, PAD + 20))
            d.text((x + 4, 2), label, font=f_small, fill=(150, 200, 255))
        d.text((PAD + 2, CELL_H + PAD), cap1, font=f_big, fill=(235, 235, 235))
        d.text((PAD + 2, CELL_H + PAD + 24), cap2, font=f_small, fill=(255, 200, 120))
        d.text((PAD + 2, CELL_H + PAD + 46), cap3, font=f_small, fill=(170, 220, 170))
        rows.append(fig)
    for i in range(0, len(rows), per_fig):
        chunk = rows[i:i + per_fig]
        total_h = sum(r.height for r in chunk) + PAD * (len(chunk) + 1)
        canvas = Image.new("RGB", (max(r.width for r in chunk), total_h), (12, 12, 15))
        y = PAD
        for r in chunk:
            canvas.paste(r, (0, y)); y += r.height + PAD
        out = f"{out_prefix}-{i // per_fig + 1}.png"
        canvas.save(out)
        figs += 1
        print("wrote", out)
    print(f"cases={len(rows)} figures={figs}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
