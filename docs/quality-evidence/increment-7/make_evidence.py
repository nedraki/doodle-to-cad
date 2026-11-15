"""Increment-7 evidence: per-axis dimension provenance over the real sweep.

For every case, the registered profile_topology (which views the evaluator
actually measured) is mapped to the CAD axes they constrain, and the sorted
extent ratios vs ground truth are shown beside it. The case that motivated
this (012) gets a detail callout: spec thickness vs GT, under a provenance
label that claimed 'measured ink spans' for a front-view-only drawing.

Usage: make_evidence.py <run_dir> <repo_root> <out_png>
"""
from __future__ import annotations
import json, sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

from doodle_to_cad.evaluation import _unverified_axes

BG, FG, GREEN, RED, AMBER = "#12121a", "#e8e8e8", "#3fbf6f", "#e05c5c", "#e0a83c"
AX_LABELS = {"x": "X width", "y": "Y depth", "z": "Z height"}


def main() -> int:
    run_dir, repo = Path(sys.argv[1]), Path(sys.argv[2])
    out = sys.argv[3]
    cases = sorted(d for d in run_dir.iterdir() if (d / "trial-1" / "result.json").exists())
    rows = []
    for cd in cases:
        v = json.loads((cd / "trial-1" / "verdict.json").read_text())
        r = json.loads((cd / "trial-1" / "result.json").read_text())
        ev = r.get("evaluation") or {}
        pt = ev.get("profile_topology") or {}
        axes_un = _unverified_axes(pt, bool(r.get("mesh_health")))
        ext = sorted((float(x) for x in (v.get("extents_mm") or [])), reverse=True)
        gt = sorted((float(x) for x in (v.get("gt_stl_extents_sorted") or v.get("gt_extents_mm") or [])), reverse=True)
        ratios = [x / y for x, y in zip(ext, gt)] if ext and gt else []
        rows.append((cd.name, sorted(pt.keys()), axes_un, ratios,
                     (v.get("checks") or {}).get("dims_axiswise_pass")))

    fig, ax = plt.subplots(figsize=(11.5, 0.52 * len(rows) + 4.8), facecolor=BG)
    ax.set_facecolor(BG)
    ax.set_xlim(0, 10); ax.set_ylim(-4.6, len(rows) + 3.2)
    ax.axis("off")
    ax.text(0, len(rows) + 2.7, "Dimension provenance per axis — green = a registered view measures this axis, red = zero ink evidence (spec value there is a guess)",
            color=FG, fontsize=10.5, fontweight="bold")
    ax.text(3.1, len(rows) + 2.15, "registered views", color=AMBER, fontsize=9)
    ax.text(5.35, len(rows) + 2.15, "extent ratios vs GT (sorted)", color=AMBER, fontsize=9)
    for i, (case, views, axes_un, ratios, dpass) in enumerate(rows):
        y = len(rows) - i
        ax.text(0, y, case, color=FG, fontsize=8.6, va="center")
        ax.text(3.1, y, ",".join(views) or "none", color="#9ab8d8", fontsize=8.2, va="center")
        for j, axis in enumerate("xyz"):
            col = RED if axis in axes_un else GREEN
            ax.add_patch(mpatches.Rectangle((4.45 + j * 0.28, y - 0.28), 0.22, 0.56, color=col))
        rtxt = "[" + ",".join(f"{r:.2f}" for r in ratios) + "]" if ratios else "-"
        col = GREEN if dpass else (RED if dpass is False else AMBER)
        ax.text(5.35, y, f"{rtxt}  axiswise_pass={dpass}", color=col, fontsize=8.4, va="center")
    # callout for 012 with the actual spec field
    p = run_dir / "012_vent_grille_grid" / "trial-1" / "result.json"
    box = "012 detail:  front-only drawing → depth axis has NO ink.\n"
    if p.exists():
        r = json.loads(p.read_text())
        dims = ((r.get("spec") or {}).get("dimensions")) or {}
        prov = dims.get("size_provenance")
        box += (f"spec plate_thickness={dims.get('plate_thickness')} mm  vs  GT 4.0 mm (2.5x)\n"
                f"provenance label on that number: '{prov}'\n"
                f"v7: profile_topology={{{','.join(repr(k) for k in ((r.get('evaluation') or {}).get('profile_topology') or {}))}}} → unverified_axes=['y']")
    ax.text(0, -4.3, box, color=FG, fontsize=8.6, va="bottom",
            bbox=dict(boxstyle="round,pad=0.6", fc="#1c1c26", ec=AMBER))
    plt.tight_layout()
    fig.savefig(out, dpi=130, facecolor=BG)
    print("wrote", out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
