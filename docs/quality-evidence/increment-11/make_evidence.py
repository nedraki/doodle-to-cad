"""Increment-11 evidence: the interior gate measured on the final sweep.

Left: per registered view, drawing interior features vs render interior
features (the product's OWN _interior_ink/_interior_render). Red bars are the
gate's fail region (drawing >= 3, render == 0) — every one of them belongs to
a case the pipeline already rejected; zero accepted cases have a red bar
(the regression assertion, re-verified from verdicts each run).

Usage: make_evidence.py <run_dir> <repo_root> <out_png>
"""
from __future__ import annotations
import json, sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from doodle_to_cad.evaluation import _decode, _interior_ink, _interior_render, assign_view_groups

K = 3


def main() -> int:
    run_dir, repo, out = Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3]
    rows, accepted_with_red = [], 0
    for cd in sorted(run_dir.iterdir()):
        if not (cd / "trial-1" / "verdict.json").exists():
            continue
        r = json.loads((cd / "trial-1" / "result.json").read_text())
        v = json.loads((cd / "trial-1" / "verdict.json").read_text())
        src = _decode((repo / "benchmarks/cases"/cd.name/"source"/"drawing.png").read_bytes())
        if src is None:
            continue
        h, w = src.shape[:2]
        vg = assign_view_groups(r.get("geometry") or {}, "front", "third-angle")
        run = repo / "results" / v["run_id"]
        for name, g in vg.items():
            bb = g.get("bbox_normalized")
            if not name or not bb:
                continue
            x, y, gw, gh = bb
            crop = src[max(0, int(y*h)):int((y+gh)*h), max(0, int(x*w)):int((x+gw)*w)]
            rp = run / f"view-{name}.png"
            if crop.size == 0 or not rp.exists():
                continue
            ri = _decode(rp.read_bytes())
            if ri is None:
                continue
            ci, rin = _interior_ink(crop), _interior_render(ri)
            fail = ci >= K and rin == 0
            if fail and v.get("accepted"):
                accepted_with_red += 1
            rows.append((f"{cd.name[:18]}·{name}", ci, rin, fail, bool(v.get("accepted"))))
    rows.sort(key=lambda t: (-t[1], t[0]))
    labels = [t[0] for t in rows]
    fig, ax = plt.subplots(figsize=(13, 0.30*len(rows)+2.6), dpi=110)
    y = range(len(rows))
    ax.barh([t-0.2 for t in y], [t[1] for t in rows], height=0.4, color="#7fb3ff", label="drawing interior features")
    ax.barh([t+0.2 for t in y], [t[2] for t in rows], height=0.4, color="#8fffb0", label="render interior features")
    for i, (_, ci, rin, fail, acc) in enumerate(rows):
        if fail:
            ax.text(max(ci, rin)+0.3, i, ("REJECTED " if not acc else "ACCEPTED ")+f"crop={ci} render={rin}",
                    va="center", fontsize=7.5, color="#ff7b7b",
                    weight="bold")
        elif acc and ci >= K:
            ax.text(max(ci, rin)+0.3, i, f"ok crop={ci} render={rin}", va="center", fontsize=7, color="#8fffb0")
    ax.axvline(K-0.5, color="#ff7b7b", ls=":", lw=1)
    ax.set_yticks(list(y)); ax.set_yticklabels(labels, fontsize=7)
    ax.invert_yaxis(); ax.set_xlabel("interior feature components (product gate functions)")
    ax.set_title(f"Interior gate — final sweep {run_dir.name}\n"
                 f"fail region: drawing >= {K} while render == 0 · red = gate fail · "
                 f"accepted-with-red = {accepted_with_red} (must be 0) · "
                 f"regression: 0 verdict flips on 72 re-scored session cells",
                 color="#eaeaea", fontsize=10)
    ax.tick_params(colors="#bbbbbb"); ax.figure.patch.set_facecolor("#121216"); ax.set_facecolor("#121216")
    for s in ax.spines.values(): s.set_color("#444")
    ax.grid(axis="x", color="#333", lw=0.5)
    leg = ax.legend(loc="lower right", fontsize=8); plt.setp(leg.get_texts(), color="#dddddd")
    fig.tight_layout(); fig.savefig(out)
    print("wrote", out, f"rows={len(rows)} accepted_with_red={accepted_with_red}")
    if accepted_with_red:
        print("INTERIOR GATE FALSE-FLAG — INVESTIGATE"); return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
