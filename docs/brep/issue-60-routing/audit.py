#!/usr/bin/env python3
"""Rerunnable audit for the issue #60 routing dossier. Every claim in README.md
is re-verified here; exit 0 means all pass."""
import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
results = []


def check(name, ok, detail=""):
    results.append((name, bool(ok), detail))
    print(f"{'PASS' if ok else 'FAIL'}  {name}" + (f" — {detail}" if detail else ""))


m = json.loads((HERE / "data/routing-matrix.json").read_text())
check("frozen matrix covers 8 drawings", m["summary"]["drawings"] == 8)
check("frozen matrix has zero disagreements", m["summary"]["disagree"] == 0,
      f"agree {m['summary']['agree']}, neutral {m['summary']['neutral']}")
check("frozen matrix rerun matches (no LLM, deterministic)",
      subprocess.run([sys.executable, "scripts/validate_routing.py"], cwd=REPO,
                     capture_output=True, text=True).returncode == 0)

live = {p.stem: json.loads(p.read_text()) for p in (HERE / "data/live").glob("*.json")}
check("live demo recorded both cases", set(live) == {"single_view_box", "multi_view_grid"})
check("single-view box routed to usd-brep via rule D",
      live["single_view_box"]["routing"]["rule"] == "D"
      and live["single_view_box"]["backend_in_result"] == "usd-brep")
check("multi-view grid routed to openscad via rule V",
      live["multi_view_grid"]["routing"]["rule"] == "V"
      and live["multi_view_grid"]["backend_in_result"] == "openscad")
for name, row in live.items():
    stored = REPO / "results" / row["job_id"] / "routing.json"
    check(f"routing.json persisted for {name} ({row['job_id']})",
          stored.is_file() and json.loads(stored.read_text())["rule"] == row["routing"]["rule"])

t = subprocess.run([sys.executable, "-m", "pytest", "tests/test_backend_router.py", "-q"],
                   cwd=REPO, capture_output=True, text=True)
check("router tests pass (14)", "14 passed" in t.stdout, (t.stdout.strip().splitlines() or [""])[-1])

suite = (HERE / "logs/full-suite.txt").read_text()
check("full-suite log records the branch suite", "passed" in suite and "failed" not in suite,
      suite.strip().splitlines()[-1])

s = subprocess.run(["sha256sum", "-c", "SHA256SUMS"], cwd=HERE, capture_output=True, text=True)
check("SHA256SUMS verifies", s.returncode == 0, f"{s.stdout.count('OK')} files OK")

failed = [r for r in results if not r[1]]
print(f"\n{len(results) - len(failed)}/{len(results)} PASS")
raise SystemExit(1 if failed else 0)
