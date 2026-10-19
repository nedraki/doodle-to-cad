"""Aggregate bench-final trial rows into strengths/weaknesses tables.

Run after evaluate_brep.py trials completes:
  PYTHONPATH=. .venv/bin/python docs/brep/bench-final/aggregate.py
Writes results.json + RESULTS.md next to this script. Reads only saved
row.json artifacts (written by scripts/evaluate_brep.py trials) — never
fabricates a row that does not exist on disk.
"""
import json
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
RUNS = HERE / "runs"
CHECK_KEYS = ("build_success", "extents_pass", "genus_pass", "volume_pass",
              "fidelity_pass", "overall_pass")


def rate(n, d):
    return f"{100.0 * n / d:.0f}%" if d else "—"


def verdict(r):
    """Product acceptance EXACTLY as the frozen plan defines it
    (TRIAL-PLAN.json product_acceptance):
      openscad: result.success (agent accepted, score >= 70)
      usd-brep: evaluation.status != 'failed'  -- the BRep path never
      auto-accepts fidelity (accepted stays false by design), so 'not
      failed' means 'automatic checks passed; still unverified', NOT
      fully accepted. A stricter status=='passed' is unsatisfiable by the
      evaluator (brep_checks.py only emits failed|unverified) and was a
      reporting error in rev 907eed7; both counts are published now."""
    p = r.get("product") or {}
    if p.get("score") is not None:
        return bool(p.get("accepted"))
    return p.get("status") is not None and p.get("status") != "failed"


def main():
    rows = []
    for row_file in sorted(RUNS.glob("*/*/trial-*/row.json")):
        try:
            rows.append(json.loads(row_file.read_text()))
        except Exception as exc:  # corrupt row: publish, never drop silently
            rows.append({"drawing": row_file.parent.parent.name,
                         "backend": row_file.parent.name, "trial": row_file.parent.name[-8:],
                         "job_status": "row_corrupt", "error": {"message": str(exc)}})
    by_backend = defaultdict(list)
    for r in rows:
        by_backend[r["backend"]].append(r)

    summary = {"rows": len(rows), "backends": {}}
    for backend, rs in sorted(by_backend.items()):
        done = [r for r in rs if r.get("job_status") == "done"]
        accepted = [r for r in done if verdict(r)]
        scores = [r["product"]["score"] for r in done
                  if (r.get("product") or {}).get("score") is not None]
        checks = {k: sum(1 for r in done if (r.get("checks") or {}).get(k) is True) for k in CHECK_KEYS}
        walls = [r["wall_seconds"] for r in rs if r.get("wall_seconds")]
        summary["backends"][backend] = {
            "trials": len(rs), "done": len(done),
            "accepted": len(accepted), "accept_rate": rate(len(accepted), len(done)),
            "build_ok_rate": rate(checks["build_success"], len(done)),
            "overall_pass_rate": rate(checks["overall_pass"], len(done)),
            "check_pass": {k: rate(checks[k], len(done)) for k in CHECK_KEYS},
            "mean_score": round(sum(scores) / len(scores), 1) if scores else None,
            "median_wall_s": sorted(walls)[len(walls) // 2] if walls else None,
            "questions_asked": sum(r.get("questions_asked") or 0 for r in rs),
            "top_failures": Counter(f for r in done for f in ((r.get("product") or {}).get("failures") or []))
                                   .most_common(6),
            "unsupported": Counter(
                (u.get("code") or str(u.get("flag")))[:80] if isinstance(u, dict) else str(u)[:80]
                for r in rs for u in ([r["unsupported"]] if isinstance(r.get("unsupported"), dict)
                                      else (r.get("unsupported") or []))).most_common(6),
        }

    by_drawing = defaultdict(lambda: defaultdict(list))
    for r in rows:
        by_drawing[r["drawing"]][r["backend"]].append(r)
    per_drawing = {}
    for drawing, cells in sorted(by_drawing.items()):
        per_drawing[drawing] = {}
        for backend, rs in cells.items():
            done = [r for r in rs if r.get("job_status") == "done"]
            per_drawing[drawing][backend] = {
                "trials": len(rs),
                "accepted": sum(1 for r in done if verdict(r)),
                "overall_pass": sum(1 for r in done if (r.get("checks") or {}).get("overall_pass")),
                "scores": [(r.get("product") or {}).get("score") for r in done],
                "best_failure": sorted({f for r in done for f in ((r.get("product") or {}).get("failures") or [])})[:2],
            }

    (HERE / "results.json").write_text(json.dumps(
        {"summary": summary, "per_drawing": per_drawing}, indent=2) + "\n")

    lines = ["# bench-final results — merged BRep line (plan 3f5d76d)", "",
             "| backend | trials | done | product-accepted | accept rate | build OK | GT overall pass | mean score | median wall (s) |",
             "|---|---|---|---|---|---|---|---|---|"]
    for backend, s in summary["backends"].items():
        lines.append(f"| {backend} | {s['trials']} | {s['done']} | {s['accepted']} | {s['accept_rate']} | "
                     f"{s['build_ok_rate']} | {s['overall_pass_rate']} | {s['mean_score']} | {s['median_wall_s']} |")
    lines += ["", "## Ground-truth check pass rates (done trials)", ""]
    for backend, s in summary["backends"].items():
        lines.append(f"- **{backend}**: " + ", ".join(f"{k} {v}" for k, v in s["check_pass"].items()))
    lines += ["", "## Top gate failures", ""]
    for backend, s in summary["backends"].items():
        lines.append(f"- **{backend}**: " + ("; ".join(f"{n}×{t[:70]}" for t, n in s["top_failures"]) or "—"))
    lines += ["", "## Unsupported operations recorded", ""]
    for backend, s in summary["backends"].items():
        lines.append(f"- **{backend}**: " + ("; ".join(f"{n}×{t[:70]}" for t, n in s["unsupported"]) or "—"))
    lines += ["", "## Per-drawing (accepted / overall_pass of trials)", "",
              "| drawing | openscad | usd-brep |", "|---|---|---|"]
    for drawing, cells in per_drawing.items():
        def cell(b, _c=cells, _d=drawing):
            c = _c.get(b)
            if not c:
                return "—"
            sc = [round(s, 1) for s in c["scores"] if s is not None]
            return f"{c['accepted']}/{c['trials']} (pass {c['overall_pass']}/{c['trials']}) " + (str(sc) if sc else "")
        lines.append(f"| {drawing} | {cell('openscad')} | {cell('usd-brep')} |")
    (HERE / "RESULTS.md").write_text("\n".join(lines) + "\n")
    print(json.dumps(summary["backends"], indent=1)[:1500])
    print("rows:", len(rows), "-> results.json + RESULTS.md")


if __name__ == "__main__":
    main()
