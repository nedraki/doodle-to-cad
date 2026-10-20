#!/usr/bin/env python3
"""Issue #81: re-score the frozen bench with PROVEN-unreliable checks marked
unreliable (never deleted, thresholds never lowered).

Reads only the sealed rows under ../bench-final/runs/ and the EV registry in
CASES.json; writes RECLASSIFY.md + RECLASSIFY.json beside this script. The
frozen bench-final numbers are never touched — this answers "what would the
verdict be if we stop trusting checks we have proven cannot measure", so the
model is neither credited for passing a broken check nor blamed by one.

Unreliable rules (each cites its VERIFIED EV evidence in CASES.json):
  EV-1  GT dimensions that exist nowhere the model can see (004 thickness,
        007 depth/height, 008 depth/height, 101 x/z): extents + volume
  EV-2/EV-7  wheel opening extraction undercount + orientation-dependent
        fidelity (same correct part, opposite verdicts by backend): fidelity
  EV-5  wheel volume compares the reference author's undimensioned rim and
        spoke widths: volume (both backends)
  EV-7  004 fidelity: identical part, opposite verdicts by orientation:
        fidelity (both backends)
EV-4 (007 acceptance insensitivity) was REFUTED by the byte re-read: the
007 fidelity check is RELIABLE (front similarity 0.35 caught the plate
that the product also rejected). Visible-topology checks (genus) stay
reliable everywhere: they are what catch the real model failures.
"""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
RUNS = HERE.parent / "bench-final" / "runs"
CASES = json.loads((HERE / "CASES.json").read_text())

UNRELIABLE = {  # drawing -> (checks, ev)
    "004_flat_mounting_plate": ([("extents_pass", "volume_pass", "fidelity_pass")],
                                "EV-1+EV-7"),
    "007_angle_bracket_holes": ([("extents_pass", "volume_pass")], "EV-1"),
    "101_bltouch_bracket": ([("extents_pass", "volume_pass")], "EV-1"),
    "008_open_enclosure_window": ([("extents_pass", "volume_pass")], "EV-1"),
    "wheel": ([("volume_pass", "fidelity_pass")], "EV-5+EV-2"),
}


def rules_for(drawing: str):
    if drawing in UNRELIABLE:
        return list(UNRELIABLE[drawing][0][0]), [UNRELIABLE[drawing][1]]
    return [], []


def main() -> None:
    rows = []
    for row_file in sorted(RUNS.glob("*/*/trial-*/row.json")):
        rows.append(json.loads(row_file.read_text()))
    per_backend: dict = {}
    changed = []
    for r in rows:
        b = r["backend"]
        st = per_backend.setdefault(b, {"cells": 0, "pass_orig": 0, "pass_recl": 0})
        checks = r.get("checks") or {}
        orig = bool(checks.get("overall_pass"))
        bad_checks, evs = rules_for(r["drawing"])
        meta = ("overall_pass", "not_applicable", "build_success")
        measuring = {k: v for k, v in checks.items()
                     if k not in meta and v is not None and k not in bad_checks}
        if not measuring and checks.get("build_success"):
            recl: object = "unjudgeable"  # every measuring check was proven broken or n/a
        else:
            recl = all(measuring.values()) and bool(checks.get("build_success"))
        st["cells"] += 1
        st["pass_orig"] += orig
        st["pass_recl"] += (recl is True)
        st.setdefault("unjudgeable", 0)
        st["unjudgeable"] += (recl == "unjudgeable")
        if orig is not True and recl is not False:
            changed.append({"drawing": r["drawing"], "backend": b, "trial": r["trial"],
                            "orig_overall": orig, "reclassified_overall": recl,
                            "unreliable_checks_ignored": bad_checks, "evidence": evs,
                            "failed_check_names": [k for k, v in checks.items()
                                                   if v is False and k not in bad_checks
                                                   and k != "overall_pass"]})
    lines = ["# Re-scoring with proven-unreliable checks marked (issue #81)", "",
             "Frozen bench-final verdicts are NOT modified. A check is ignored only",
             "where CASES.json carries a VERIFIED evaluator/input defect; ignored does",
             "not mean passed — the cell is judged by its remaining reliable checks.", "",
             "A reclassified pass means only: the bench's *reliable* checks found no",
             "failure. It is not a truth verdict — ATTRIBUTION.md still assigns some",
             "reclassified cells to model failures (e.g. the 007 plate, whose genus",
             "equals the bracket's: the bench simply has no reliable check left that",
             "can see the bend). This file measures the bench, not the parts.", "",
             "| backend | cells | overall_pass (frozen) | reclassified (reliable checks only) | unjudgeable (all measuring checks proven broken) |",
             "|---|---|---|---|---|"]
    for b, st in sorted(per_backend.items()):
        lines.append(f"| {b} | {st['cells']} | {st['pass_orig']} | {st['pass_recl']} | {st['unjudgeable']} |")
    lines += ["", "## Cells whose verdict changes", ""]
    for c in changed:
        lines.append(f"- {c['drawing']} / {c['backend']} trial-{c['trial']:02d}: "
                     f"{c['orig_overall']} -> {c['reclassified_overall']} "
                     f"(ignored {c['unreliable_checks_ignored']} per {'+'.join(c['evidence'])}; "
                     f"still-failing reliable checks: {c['failed_check_names'] or 'none'})")
    (HERE / "RECLASSIFY.md").write_text("\n".join(lines) + "\n")
    (HERE / "RECLASSIFY.json").write_text(json.dumps(
        {"per_backend": per_backend, "changed": changed}, indent=2))
    print(f"cells={len(rows)}; changed={len(changed)}")
    for b, st in sorted(per_backend.items()):
        print(b, st)


if __name__ == "__main__":
    main()
