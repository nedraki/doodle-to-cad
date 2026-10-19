#!/usr/bin/env python3
"""Offline validation of the issue #60 routing rules against the frozen
80-run comparison (docs/brep/task-17-comparison/).

For each drawing we recompute the router inputs from the row's own input.png
and request.json, recommend a backend, and compare with what actually got
accepted on each side in the frozen matrix. No LLM, no kernel: pure rerun.

Usage: PYTHONPATH=. .venv/bin/python scripts/validate_routing.py
Writes docs/brep/issue-60-routing/data/routing-matrix.json
"""
import json
import sys
from collections import defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from doodle_to_cad.backend_router import route  # noqa: E402
from doodle_to_cad.geometry import analyze_image  # noqa: E402

RUNS = REPO / "docs/brep/task-17-comparison/runs"
OUT = REPO / "docs/brep/issue-60-routing/data/routing-matrix.json"


def accepted_count(drawing: str, backend: str) -> tuple[int, int]:
    dirs = sorted((RUNS / drawing / backend).glob("trial-*"))
    ok = total = 0
    for d in dirs:
        row = d / "row.json"
        if not row.is_file():
            continue
        total += 1
        data = json.loads(row.read_text())
        if (data.get("product") or {}).get("accepted"):
            ok += 1
    return ok, total


def main() -> int:
    rows = defaultdict(dict)
    for row_path in RUNS.rglob("row.json"):
        parts = row_path.parts
        drawing, backend = parts[-4], parts[-3]
        data = json.loads(row_path.read_text())
        rows[drawing].setdefault(backend, data)
        rows[drawing]["_dir"] = row_path.parent.parent.parent

    matrix, agree, disagree, neutral = [], 0, 0, 0
    for drawing in sorted(rows):
        row = rows[drawing]
        any_row = next(v for k, v in row.items() if k != "_dir")
        req = json.loads((row["_dir"] / "request.json").read_text()) \
            if (row["_dir"] / "request.json").is_file() else {}
        # Find this drawing's input.png (same sheet for both backends).
        inp = next((row["_dir"] / b / t / "input.png"
                    for b in ("openscad", "usd-brep")
                    for t in sorted((row["_dir"] / b).glob("trial-*"), reverse=True)
                    if (t / "input.png").is_file()), None)
        if inp is None:
            print(f"SKIP {drawing}: no input.png", file=sys.stderr)
            continue
        evidence, _ = analyze_image(inp.read_bytes())
        rec = route(evidence, req.get("notes", ""), str(req.get("dimension", "")), False)
        o_ok, o_total = accepted_count(drawing, "openscad")
        b_ok, b_total = accepted_count(drawing, "usd-brep")
        chosen_ok = o_ok if rec["backend"] == "openscad" else b_ok
        other_ok = b_ok if rec["backend"] == "openscad" else o_ok
        if chosen_ok > 0 and other_ok == 0:
            verdict = "agree"
            agree += 1
        elif other_ok > 0 and chosen_ok == 0:
            verdict = "disagree"
            disagree += 1
        else:
            verdict = "neutral"  # both sides accepted or neither did
            neutral += 1
        matrix.append({"drawing": drawing, "recommended": rec["backend"],
                       "rule": rec["rule"], "signals": rec["signals"],
                       "openscad_accepted": f"{o_ok}/{o_total}",
                       "usd_brep_accepted": f"{b_ok}/{b_total}", "verdict": verdict})
        print(f"{drawing:24s} -> {rec['backend']:9s} rule {rec['rule']}"
              f"  openscad {o_ok}/{o_total}  usd-brep {b_ok}/{b_total}  [{verdict}]")
    summary = {"drawings": len(matrix), "agree": agree, "disagree": disagree,
               "neutral": neutral,
               "note": "agree = recommended backend produced accepted rows while the"
                       " other backend produced none; disagree = the reverse; neutral ="
                       " both or neither accepted (rules cannot be validated there)"}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({"summary": summary, "rows": matrix}, indent=2))
    print(json.dumps(summary, indent=2))
    return 0 if disagree == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
