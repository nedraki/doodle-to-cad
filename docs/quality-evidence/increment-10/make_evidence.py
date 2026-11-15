"""Legacy-benchmark (no-GT held-out) evidence: drawing | built front | right | iso.

These cases have no ground truth: every GT-derived field must read None/absent,
never pass. The caption asserts that explicitly so the figure cannot be read
as a GT-verified claim.

Usage: make_evidence.py <run_dir> <results_root> <repo_root> <out_prefix> [rows_per_fig]
"""
from __future__ import annotations
import json, sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

CELL_W, CELL_H, PAD, CAP_H = 280, 240, 8, 78


def load_font(size: int):
    p = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
    return ImageFont.truetype(p, size) if Path(p).exists() else ImageFont.load_default()


def fit(img, w, h):
    img = img.convert("RGB"); img.thumbnail((w, h)); return img


def main() -> int:
    run_dir, results_root, repo = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
    out_prefix, per_fig = sys.argv[4], int(sys.argv[5]) if len(sys.argv) > 5 else 5
    f_big, f_small = load_font(15), load_font(13)
    cells = []
    for cd in sorted(d for d in run_dir.iterdir() if (d / "trial-1" / "verdict.json").exists()):
        for tf in sorted((cd).glob("trial-*")):
            vp = tf / "verdict.json"
            if not vp.exists():
                continue
            v = json.loads(vp.read_text())
            cells.append((cd.name, tf.name, v))
    rows = []
    for case, trial, v in cells:
        built = results_root / (v.get("run_id") or "_missing")
        drawing = repo / "benchmarks" / "cases" / case / "source" / "drawing.png"
        panels = [("drawing", drawing), ("front", built / "view-front.png"),
                  ("right", built / "view-right.png"), ("iso", built / "view-isometric.png")]
        gs = v.get("gates_state") or {}
        cap1 = (f"{case} {trial}  accepted={v.get('accepted')}  "
                f"failed {([k for k, s in gs.items() if s == 'fail'] or '-')}  "
                f"unmeasured {v.get('unverified_gates') or '-'}")
        gt_ok = (v.get("gt_genus") is None and v.get("gt_stl_extents_sorted") is None
                 and v.get("checks", {}).get("volume_ratio_pass") is None)
        cap2 = (f"NO-GT case: gt checks = {('None (correct)' if gt_ok else 'PRESENT — BUG!')}"
                f"  · unverified_axes {v.get('unverified_axes') or '-'}"
                f"  · genus {v.get('genus_total')}  inv {v.get('inverted_solids')}")
        cap3 = f"rev {(v.get('fingerprint') or {}).get('git_rev', '?')[:7]}  cache {v.get('cache_stats')}"
        fig = Image.new("RGB", (4 * CELL_W + 5 * PAD, CELL_H + CAP_H + 2 * PAD), (18, 18, 22))
        d = ImageDraw.Draw(fig)
        for i, (label, src) in enumerate(panels):
            if Path(src).exists():
                im = fit(Image.open(src), CELL_W - 6, CELL_H - 24)
            else:
                im = Image.new("RGB", (CELL_W - 6, CELL_H - 24), (24, 24, 28))
                ImageDraw.Draw(im).text((10, 100), f"NO {label}", font=f_small, fill=(240, 120, 120))
            x = PAD + i * (CELL_W + PAD)
            fig.paste(im, (x + (CELL_W - im.width) // 2, PAD + 20))
            d.text((x + 4, 2), label, font=f_small, fill=(150, 200, 255))
        d.text((PAD + 2, CELL_H + PAD), cap1, font=f_big, fill=(235, 235, 235))
        d.text((PAD + 2, CELL_H + PAD + 22), cap2, font=f_small, fill=(255, 170, 170) if not gt_ok else (170, 220, 255))
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
    print(f"cells={len(rows)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
