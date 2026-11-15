"""Increment-8 evidence: 7 x 3 variance matrix for the GT-contradicted cases.

Each cell shows accepted / genus-vs-GT / per-axis-dims chips from fresh
(cacheless) generations, so sampling noise is separated from stable defects.

Usage: make_evidence.py <run_dir> <out_png>
"""
from __future__ import annotations
import json, sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

BG, FG, GREEN, RED, AMBER, GREY = "#12121a", "#e8e8e8", "#3fbf6f", "#e05c5c", "#e0a83c", "#555a66"


def chip(ax, x, y, label, ok):
    col = GREEN if ok is True else (RED if ok is False else GREY)
    ax.add_patch(mpatches.FancyBboxPatch((x, y - 0.16), 0.52, 0.34, boxstyle="round,pad=0.03", color=col))
    ax.text(x + 0.26, y, label, color="#0b0b10" if col in (GREEN, RED) else FG,
            fontsize=7.6, ha="center", va="center", fontweight="bold")


def main() -> int:
    run_dir, out = Path(sys.argv[1]), sys.argv[2]
    plant = "--plant-error" in sys.argv  # fixture: force one chip's data to lie
    cases = sorted(d for d in run_dir.iterdir() if (d / "trial-1" / "verdict.json").exists())
    fig, ax = plt.subplots(figsize=(12.0, 0.62 * len(cases) + 2.2), facecolor=BG, dpi=130)
    chips: list[tuple[str, int, str, str, float, float]] = []  # case, trial, kind, expect, x, y
    ax.set_facecolor(BG); ax.axis("off")
    ax.set_xlim(0, 12.0); ax.set_ylim(0, len(cases) + 2.4)
    ax.text(0.1, len(cases) + 1.9, "Trial variance — 7 GT-contradicted cases, fresh generations, cache OFF. Chips: A=accepted, G=genus vs GT, D=per-axis dims vs GT; green=pass, red=fail",
            color=FG, fontsize=10, fontweight="bold")
    for t in (1, 2, 3):
        ax.text(3.1 + (t - 1) * 1.85, len(cases) + 1.45, f"trial {t}", color=AMBER, fontsize=9, ha="center")
    for i, cd in enumerate(cases):
        y = len(cases) - i + 0.4
        rows = []
        for t in (1, 2, 3):
            v = json.loads((cd / f"trial-{t}" / "verdict.json").read_text())
            ch = v.get("checks") or {}
            rows.append((v, ch))
        v0 = rows[0][0]
        accs = sum(1 for v, _ in rows if v.get("accepted"))
        gps = sum(1 for _, ch in rows if ch.get("genus_pass") is True)
        dps = sum(1 for _, ch in rows if ch.get("dims_axiswise_pass") is True)
        ax.text(0.1, y, (cd.name if len(cd.name) <= 21 else cd.name[:20] + "…"), color=FG, fontsize=8.2, va="center")
        for t, (v, ch) in enumerate(rows):
            x = 3.1 + t * 1.85
            for kind, ok, label, dx in (("A", v.get("accepted"), f"A {'✓' if v.get('accepted') else '✗'}", -0.82),
                                        ("G", ch.get("genus_pass"), f"G {v.get('genus_total')}/{v.get('gt_genus')}", -0.22),
                                        ("D", ch.get("dims_axiswise_pass"), "D" + ("✓" if ch.get("dims_axiswise_pass") else "✗"), 0.38)):
                chip(ax, x + dx, y, label, ok)
                expect = GREEN if ok is True else (RED if ok is False else GREY)
                if plant and t == 0 and kind == "D":
                    expect = RED if expect == GREEN else GREEN  # declared colour lies about drawn chip
                chips.append((cd.name, t + 1, kind, expect, x + dx + 0.07, y))
        if gps == 0:
            verdict, col = "GENUS defect is STABLE", RED
        elif gps < 3:
            verdict, col = "genus intermittent", AMBER
        else:
            verdict, col = "genus stable", GREEN
        suffix = f"  ·  accepted {accs}/3 · genus {gps}/3 · thin-axis dims {dps}/3 vs GT"
        ax.text(8.4, y, verdict + suffix, color=col, fontsize=8.6, va="center")
    plt.tight_layout()
    fig.savefig(out, dpi=130, facecolor=BG)
    # Self-verification: every chip's centre pixel must equal its declared
    # colour — a figure whose pixels contradict its data is worse than none.
    from PIL import Image
    img = Image.open(out).convert("RGB")
    bad = 0
    for case, trial, kind, expect, x, y in chips:
        px, py = ax.transData.transform((x, y + 0.11))
        got = img.getpixel((int(px), img.height - int(py)))
        want = tuple(int(c, 16) for c in (expect[1:3], expect[3:5], expect[5:7]))
        if sum(abs(a - b) for a, b in zip(got, want)) > 60:
            bad += 1
            print(f"CHIP COLOR MISMATCH {case} t{trial} {kind}: got {got} want ~{want}")
    print(f"chips_verified={len(chips) - bad}/{len(chips)}")
    print("wrote", out)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
