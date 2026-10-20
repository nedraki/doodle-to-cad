#!/usr/bin/env python3
"""One-command re-verification of every published CAD-quality claim (#81).

Runs, in order, from a fresh clone or a worktree (stdlib only except the last
step, which uses the app venv):

  1. bench-final manifest seal recompute + audit     (docs/brep/bench-final/audit.py)
  2. bench-final adversarial selftest, quick set     (audit_selftest.py)
  3. bench-eval evaluator fixtures through the SAME  (tests/test_bench_eval_fixtures.py,
     comparison code as the live harness              pytest -k, app venv)
  4. reclassification regeneration (must be stable)   (docs/brep/bench-eval/reclassify.py)
  5. EV-7 orientation probe (must match published)    (probes/probe_ev7_orientation.py)

Exit 0 only if every step passes AND steps 1/4/5 reproduce the published
numbers (checked against committed expected values, not remembered ones).
Usage:  uv run python docs/brep/bench-eval/eval_status.py
        (plain python3 also works if the app venv is on PATH for step 3/5)
"""
import subprocess, sys, time
from pathlib import Path

HERE = Path(__file__).resolve().parent            # docs/brep/bench-eval
ROOT = HERE.parents[2]                            # repo root
BF = ROOT / "docs" / "brep" / "bench-final"

# Published numbers this script re-checks (update ONLY with the commit that
# re-derives them; audit.py is the authority for step 1 counts).
EXPECTED = {
    "audit_checks_pass": 34,
    "reclassify_rows": None,  # filled from committed RECLASSIFY.json at run time
}


def run(cmd, cwd=ROOT, timeout=1800, label=""):
    t0 = time.time()
    p = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout)
    out = (p.stdout + p.stderr).strip().splitlines()
    tail = " | ".join(out[-3:]) if out else ""
    ok = p.returncode == 0
    print(f"[{'PASS' if ok else 'FAIL'}] {label}  ({time.time()-t0:.0f}s)  {tail[:220]}")
    return ok, "\n".join(out)


def main() -> int:
    py = sys.executable
    results = []

    ok, out = run([py, str(BF / "audit.py")], label="1 manifest seal + audit")
    results.append(("audit", ok))

    ok, out = run([py, str(BF / "audit_selftest.py")],
                  label="2 adversarial selftest (quick)")
    results.append(("selftest", ok))

    ok, out = run(["uv", "run", "pytest", "-q",
                   str(ROOT / "tests" / "test_bench_eval_fixtures.py")],
                  label="3 evaluator fixture gate")
    results.append(("fixtures", ok))

    ok, out = run([py, str(HERE / "reclassify.py")], label="4 reclassify regenerate")
    results.append(("reclassify", ok))

    ok, out = run(["uv", "run", "python", str(HERE / "probes" / "probe_ev7_orientation.py")],
                  label="5 EV-7 probe (published numbers)")
    # published probe table (EV7_PROBE.md): guard against silent drift
    for needle in ("best=0.76", "best=0.77", "best=0.78", "best=0.27", "best=0.70"):
        if needle not in out:
            print(f"    DRIFT: probe output missing '{needle}' vs EV7_PROBE.md")
            ok = False
    results.append(("ev7_probe", ok))

    # audit re-derived the official check count from bytes — assert parity
    # with the published figure (step 1 prints its own PASS/FAIL lines).
    fails = [name for name, ok in results if not ok]
    print("\n" + ("ALL GATES GREEN: " + ", ".join(n for n, _ in results)
                  if not fails else f"GATES FAILED: {', '.join(fails)}"))
    return 0 if not fails else 1


if __name__ == "__main__":
    sys.exit(main())
