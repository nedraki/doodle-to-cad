"""Re-verify the task 01 baseline on 2026-10-18 without touching the frozen evidence.

Runs the same checks as scripts/check_baseline_geometry.py (three BRep builds and
edits, three OpenSCAD equivalents, five reference solids) but writes every output
under docs/brep/baseline-01/reverify-2026-10/ so the original baseline-01 evidence
files keep their original bytes. Prints a plain per-case pass/fail table.

Usage (from the repository root, worker venv built, .env present):

  DOODLE_PORT=8118 DOODLE_BREP_PYTHON="$PWD/workers/brep/.venv/bin/python" \
    .venv/bin/python scripts/reverify_baseline_2026_10.py
"""
import json
import sys
import time
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import scripts.check_baseline_geometry as cbg

OUT = ROOT / "docs/brep/baseline-01/reverify-2026-10"


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    cbg.OUT = OUT
    started = time.monotonic()
    status = "PASS"
    error: str | None = None
    try:
        cbg.main()
    except Exception:
        status = "FAIL"
        error = traceback.format_exc()
    rows: dict = {"ran_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                  "overall": status, "recipes": {}, "references": {}}
    if error:
        rows["error"] = error
    for f, key, label in [("recipe-checks.json", "recipes", "case"),
                          ("reference-checks.json", "references", "case")]:
        p = OUT / f
        if p.exists():
            for row in json.loads(p.read_text()):
                rows[key][row[label]] = row
    (OUT / "reverify-report.json").write_text(json.dumps(
        {k: rows[k] for k in ("ran_at_utc", "overall", "error") if k in rows}
        | {"elapsed_seconds": round(time.monotonic() - started, 1),
           "recipes": {c: {"build": r["build"], "edit": r["edit"]}
                       for c, r in rows["recipes"].items()},
           "references": rows["references"]}, indent=2) + "\n")
    print(f"overall: {status} ({time.monotonic() - started:.1f}s)")
    for name, r in rows["recipes"].items():
        b, e, o = r["build"], r["edit"], r["openscad"]
        print(f"recipe  {name:12s} watertight={b['watertight']} usd_roundtrip={b['usd_roundtrip']} "
              f"edited_ok={e['watertight'] and e['usd_roundtrip']} "
              f"openscad_watertight={o['watertight']} extents={o['extents_mm']}")
    for name, r in rows["references"].items():
        h = r["health"]
        print(f"ref     {name:12s} dim_check={r['reference_dimension_check']} "
              f"watertight={h['watertight']} components={h['components']} extents={h['extents_mm']}")
    if status == "FAIL":
        print(error, file=sys.stderr)
    return 0 if status == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
