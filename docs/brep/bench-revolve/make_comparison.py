"""Aggregate the #95 revolution-family comparison: frozen baseline vs revolve branch.

Baseline = docs/brep/bench-final/runs (pre-revolve, frozen). New = docs/brep/
bench-revolve/runs (same certified controls via the frozen plan, --trials 3).
Rows report machine checks and product verdict separately (usd-brep rows are
verdict-by-review by design; openscad rows carry accepted+score).
"""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
BENCH = HERE.parent / "bench-final"
CELLS = ["002_greek_vase_silhouette", "005_bolt_flange", "006_stepped_knob", "009_hex_prism_knob"]
BACKENDS = ["usd-brep", "openscad"]


def load_runs(base, cells, backends):
    table = {}
    for cell in cells:
        for backend in backends:
            rows = []
            for row_path in sorted((base / cell / backend).glob("trial-*/row.json")):
                rows.append(json.loads(row_path.read_text()))
            table[(cell, backend)] = rows
    return table


def summarize(rows, backend):
    n = len(rows)
    if n == 0:
        return {"submitted": 0}
    built = [r for r in rows if (r.get("checks") or {}).get("build_success")]
    overall = [r for r in rows if (r.get("checks") or {}).get("overall_pass")]
    errors = {}
    for r in rows:
        code = (r.get("error") or {}).get("code") or ("no_build" if r not in built else None)
        if code:
            errors[code] = errors.get(code, 0) + 1
    out = {"submitted": n, "build_success": len(built), "overall_pass": len(overall), "errors": errors}
    if backend == "usd-brep":
        statuses = {}
        for r in rows:
            s = (r.get("product") or {}).get("status") or "none"
            statuses[s] = statuses.get(s, 0) + 1
        out["product_status"] = statuses
    else:
        out["accepted"] = sum(1 for r in rows if (r.get("product") or {}).get("accepted"))
        scores = [(r.get("product") or {}).get("score") for r in rows]
        out["mean_score"] = round(sum(s for s in scores if s is not None) / max(1, len([s for s in scores if s is not None])), 1) if any(s is not None for s in scores) else None
    return out


def main():
    baseline = load_runs(BENCH / "runs", CELLS, BACKENDS)
    new = load_runs(HERE / "runs", CELLS, BACKENDS)
    lines = ["| cell | backend | baseline build/submit | baseline overall | baseline product | new build/submit | new overall | new product |",
             "|---|---|---|---|---|---|---|---|"]
    data = {}
    for cell in CELLS:
        for backend in BACKENDS:
            b, x = summarize(baseline.get((cell, backend), []), backend), summarize(new.get((cell, backend), []), backend)
            data[f"{cell}/{backend}"] = {"baseline": b, "revolve_branch": x}

            def prod(s):
                if not s or s.get("submitted", 0) == 0:
                    return "—"
                if backend == "usd-brep":
                    return json.dumps(s.get("product_status", {}))
                return f"accepted {s.get('accepted', 0)}/{s['submitted']}, mean {s.get('mean_score')}"
            def cell_fmt(s):
                if not s or s.get("submitted", 0) == 0:
                    return "—", "—"
                return f"{s['build_success']}/{s['submitted']}", f"{s['overall_pass']}/{s['submitted']}"
            bl, bo = cell_fmt(b)
            lines.append(f"| {cell} | {backend} | {bl} | {bo} | {prod(b)} | {cell_fmt(x)[0]} | {cell_fmt(x)[1]} | {prod(x)} |")
    (HERE / "comparison-table.md").write_text("\n".join(lines) + "\n")
    (HERE / "comparison-data.json").write_text(json.dumps(data, indent=2))
    print("\n".join(lines))
    env = HERE / "runs" / "environment.json"
    print("environment.json present:", env.exists())


if __name__ == "__main__":
    main()
