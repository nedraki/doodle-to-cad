"""Aggregate bench-final trial rows into the metric tables (issue #79).

All headline metrics come from metrics.py - the ONE definition place shared
with audit.py and README.md. Reads only saved row.json artifacts (written by
scripts/evaluate_brep.py trials); never fabricates a row that does not exist
on disk.

Hard preconditions BEFORE any report is written (external review finding 2,
and the issue's "never skip, never write a passing report past a defect"):
  * every expected trial cell from the frozen plan exists (a deleted trial
    aborts naming the path — it can never silently shrink a denominator);
  * no unexpected/duplicate cells; row identity matches its directory;
  * MANIFEST.json matches the bytes on disk (evidence validated first).
A corrupt row.json aborts naming the trial and path. Excluded / superseded
rows stay published on disk, are listed with their reason and replacement
trial, and are counted in no metric.

audit.py imports build_outputs() and byte-compares the committed reports
against a fresh aggregation of the sealed rows (external review finding 1:
comparing only the headline blocks let falsified supplementary numbers and a
deleted results.json pass).

Writes results.json + RESULTS.md atomically (temp + os.replace), so an
interrupted run never replaces the last complete report.

Run from repo root:
  PYTHONPATH=. python3 docs/brep/bench-final/aggregate.py
"""
import json
import os
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import NoReturn

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import metrics  # noqa: E402
from make_manifest import build_manifest  # noqa: E402

RUNS = HERE / "runs"
CHECK_KEYS = ("build_success", "extents_pass", "genus_pass", "volume_pass",
              "fidelity_pass", "overall_pass")


def fail(what, path, detail="") -> NoReturn:
    print(f"AGGREGATE ABORT: {what}\n  path: {path}" + (f"\n  detail: {detail}" if detail else ""))
    sys.exit(2)


def atomic_write(path, text):
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(text)
    os.replace(tmp, path)


def expected_cells(plan):
    return {(c["id"], b, t) for c in plan["corpus"]
            for b in metrics.BACKENDS for t in (1, 2)}


def load_cells(plan):
    """{(drawing, backend, trial): row}, enumerated FROM THE FROZEN PLAN —
    not from a glob of whatever happens to exist. A deleted cell aborts;
    identity, duplicate and unexpected cells all abort."""
    cells = {}
    for (d, b, t) in sorted(expected_cells(plan)):
        rp = RUNS / d / b / f"trial-{t:02d}" / "row.json"
        if not rp.exists():
            fail("expected trial cell missing — the frozen plan demands it "
                 "(refusing to publish a shrunken denominator)", rp)
        try:
            r = json.loads(rp.read_text())
        except json.JSONDecodeError as exc:
            fail("row.json is corrupt (not skipping)", rp, str(exc))
        if (r.get("drawing"), r.get("backend"), r.get("trial")) != (d, b, t):
            fail("row identity does not match its directory (not skipping)", rp,
                 f"row={r.get('drawing')}/{r.get('backend')}/t{r.get('trial')} dir={d}/{b}/t{t}")
        cells[(d, b, t)] = r
    for d in sorted(RUNS.glob("*/*/trial-*")):
        try:
            t = int(d.name[len("trial-"):])
        except ValueError:
            fail("trial directory name malformed", d)
        key = (d.parent.parent.name, d.parent.name, t)
        if key not in cells:
            fail("unexpected trial cell (not in the frozen plan)", d, str(key))
    return cells


def verify_evidence():
    """Manifest-vs-bytes check shared with the audit: aggregating over drifted
    bytes would publish a report consistent with the tampering."""
    manifest_path = HERE / "MANIFEST.json"
    if not manifest_path.exists():
        fail("evidence manifest missing — refusing to publish reports over unsealed evidence",
             manifest_path)
    try:
        sealed = json.loads(manifest_path.read_text())["files"]
    except (json.JSONDecodeError, KeyError) as e:
        fail("evidence manifest corrupt", manifest_path, str(e))
    actual = build_manifest()["files"]
    drift = [k for k, v in sealed.items()
             if actual.get(k) is None or actual[k]["sha256"] != v["sha256"]]
    extra = sorted(set(actual) - set(sealed))[:4]
    if drift or extra:
        fail("evidence manifest does not match the bytes on disk — refusing to publish",
             manifest_path,
             "; ".join(["drift: " + k for k in drift[:4]] + ["extra: " + k for k in extra]))


def build_outputs(rows, refs, decisions):
    """Pure: rows -> (results.json text, RESULTS.md text). audit.py imports
    this and byte-compares the committed reports against it."""
    stats = metrics.compute({"openscad": rows, "usd-brep": rows}, refs, decisions)

    supp = {}
    for backend in metrics.BACKENDS:
        done_rows = [r for r in rows if r["backend"] == backend
                     and metrics.done(r) and not metrics.exclusion(r)]
        scores = [r["product"]["score"] for r in done_rows
                  if (r.get("product") or {}).get("score") is not None]
        supp[backend] = {
            "check_pass_true": {k: sum(1 for r in done_rows if (r.get("checks") or {}).get(k) is True)
                                for k in CHECK_KEYS},
            "check_pass_null": {k: sum(1 for r in done_rows if (r.get("checks") or {}).get(k) is None)
                                for k in CHECK_KEYS},
            "mean_score": round(sum(scores) / len(scores), 1) if scores else None,
            "top_failures": Counter(f for r in done_rows
                                    for f in ((r.get("product") or {}).get("failures") or [])).most_common(6),
            "unsupported": Counter(
                (u.get("code") or str(u.get("flag")))[:80] if isinstance(u, dict) else str(u)[:80]
                for r in rows if r["backend"] == backend
                for u in ([r["unsupported"]] if isinstance(r.get("unsupported"), dict)
                          else (r.get("unsupported") or []))).most_common(6),
        }

    by_drawing = defaultdict(lambda: defaultdict(list))
    for r in rows:
        by_drawing[r["drawing"]][r["backend"]].append(r)
    per_drawing = {}
    for drawing, cels in sorted(by_drawing.items()):
        per_drawing[drawing] = {}
        for backend, rs in cels.items():
            d_rows = [r for r in rs if metrics.done(r) and not metrics.exclusion(r)]
            per_drawing[drawing][backend] = {
                "trials": len(rs),
                "completed": len(d_rows),
                "accepted_frozen_plan": sum(1 for r in d_rows if (
                    metrics.METRIC_BY_ID["plan_acceptance"]["predicate"](r, refs))),
                "overall_pass": sum(1 for r in d_rows if (r.get("checks") or {}).get("overall_pass")),
                "scores": [(r.get("product") or {}).get("score") for r in d_rows],
                "best_failure": sorted({f for r in d_rows
                                        for f in ((r.get("product") or {}).get("failures") or [])})[:2],
            }

    result_doc = {"metric_definitions": "metrics.py (single source; embedded verbatim in README.md)",
                  "summary": stats, "supplementary": supp, "per_drawing": per_drawing,
                  "decisions_file_present": (HERE / "review" / "decisions.json").exists()}
    results_json = json.dumps(result_doc, indent=2) + "\n"

    lines = ["# bench-final results — merged BRep line (plan 3f5d76d)",
             "",
             "Generated by aggregate.py from the archived row.json artifacts; every",
             "headline number recomputes from the definitions below (audit.py re-derives",
             "and byte-compares the COMPLETE report). Rows marked superseded stay",
             "listed, count in nothing.",
             ""]
    lines += metrics.tables_block_lines(stats)
    lines += ["", "## Per-check pass counts over completed trials (true / null = not applicable)", ""]
    for backend in metrics.BACKENDS:
        s = supp[backend]
        lines.append(f"- **{backend}**: " + ", ".join(
            f"{k} {s['check_pass_true'][k]} ({s['check_pass_null'][k]} n/a)" for k in CHECK_KEYS))
    lines += ["", "## Top gate failures", ""]
    for backend in metrics.BACKENDS:
        lines.append(f"- **{backend}**: " +
                     ("; ".join(f"{n}×{t[:70]}" for t, n in supp[backend]["top_failures"]) or "—"))
    lines += ["", "## Unsupported operations recorded", ""]
    for backend in metrics.BACKENDS:
        lines.append(f"- **{backend}**: " +
                     ("; ".join(f"{n}×{t[:70]}" for t, n in supp[backend]["unsupported"]) or "—"))
    excluded = [e for s in stats.values() for e in s["excluded"]]
    lines += ["", "## Superseded / excluded attempts (stays published, counted nowhere)", ""]
    if excluded:
        lines += ["| drawing | backend | trial | reason | replaced_by |", "|---|---|---|---|---|"]
        for e in excluded:
            lines.append(f"| {e['drawing']} | {e.get('backend', '')} | {e['trial']} | "
                         f"{e['reason']} | {e['replaced_by']} |")
    else:
        lines.append("None. (The 12 cells deleted in the logged plan revision predate this "
                     "bookkeeping; they are disclosed in README 'Limits', not recovered here.)")
    lines += ["", "## Per-drawing (plan-accepted / overall_pass over submitted trials)", "",
              "| drawing | openscad | usd-brep |", "|---|---|---|"]
    for drawing, cels in per_drawing.items():
        def cell(b, _c=cels):
            c = _c.get(b)
            if not c:
                return "—"
            sc = [round(s, 1) for s in c["scores"] if s is not None]
            return (f"{c['accepted_frozen_plan']}/{c['trials']} (pass {c['overall_pass']}/{c['trials']}, "
                    f"done {c['completed']}/{c['trials']}) " + (str(sc) if sc else ""))
        lines.append(f"| {drawing} | {cell('openscad')} | {cell('usd-brep')} |")
    lines += ["", metrics.definitions_block_lines()[0]]
    for m in metrics.METRICS:
        lines.append(f"- **{m['label']}** (`{m['id']}`, basis: {m['basis']}): {m['definition']}")
    lines.append(metrics.definitions_block_lines()[-1])
    return results_json, "\n".join(lines) + "\n"


def sync_readme_blocks(table_lines, defs_lines):
    """Replace the two generated AUDIT blocks in README.md. The README keeps
    its prose; only these blocks are machine-owned, so they can never drift
    from metrics.py (audit.py still re-verifies them)."""
    readme = HERE / "README.md"
    text = readme.read_text()
    for begin, end, block in (
            ("<!-- AUDIT:TABLE:BEGIN", "<!-- AUDIT:TABLE:END -->", "\n".join(table_lines)),
            ("<!-- AUDIT:METRICS:BEGIN", "<!-- AUDIT:METRICS:END -->", "\n".join(defs_lines))):
        pat = re.compile(re.escape(begin) + r".*?" + re.escape(end) + r"\n?", re.S)
        if not pat.search(text):
            fail("README.md is missing the generated block markers (add them once by hand)",
                 readme, begin)
        text = pat.sub(lambda m: block + "\n", text, count=1)
    atomic_write(readme, text)


def main():
    verify_evidence()
    plan = json.loads((HERE / "TRIAL-PLAN.json").read_text())
    cells = load_cells(plan)
    rows = list(cells.values())
    refs = json.loads((HERE / "references" / "reference-measurements.json").read_text())
    decisions_path = HERE / "review" / "decisions.json"
    decisions = json.loads(decisions_path.read_text()) if decisions_path.exists() else {}

    results_json, results_md = build_outputs(rows, refs, decisions)
    atomic_write(HERE / "results.json", results_json)
    atomic_write(HERE / "RESULTS.md", results_md)
    stats = metrics.compute({"openscad": rows, "usd-brep": rows}, refs, decisions)
    sync_readme_blocks(metrics.tables_block_lines(stats), metrics.definitions_block_lines())

    print(json.dumps({b: {"submitted": s["submitted"], "done": s["done"],
                          "metrics": {k: v["e2e_rate"] for k, v in s["metrics"].items()}}
                      for b, s in stats.items()}, indent=1))
    print(f"cells: {len(cells)} -> results.json + RESULTS.md")


if __name__ == "__main__":
    main()
