#!/usr/bin/env python3
"""Re-verify every claim in README.md of this dossier. Exit 0 only if all pass."""
import json, subprocess, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "data"
REPO = HERE.parents[2]
sys.path.insert(0, str(REPO))

results = []
def check(name, ok, detail=""):
    results.append((name, bool(ok), detail))
    print(f"{'PASS' if ok else 'FAIL'}  {name}{(' — ' + detail) if detail else ''}")

rows = [json.loads(l) for l in (DATA / "runs.jsonl").read_text().splitlines()]
newg = [json.loads(l) for l in (DATA / "runs-newgate.jsonl").read_text().splitlines()]
live = [json.loads(l) for l in (DATA / "runs-live.jsonl").read_text().splitlines()]
liveng = [json.loads(l) for l in (DATA / "runs-live-newgate.jsonl").read_text().splitlines()]

check("frozen baseline has 80 rows", len(rows) == 80, f"{len(rows)}")
check("frozen new-gate has 80 rows", len(newg) == 80, f"{len(newg)}")
check("live set has 9 rows", len(live) == 9 and len(liveng) == 9, f"{len(live)}/{len(liveng)}")

pairs = list(zip(rows, newg))
removed = sorted(f"{o['drawing']}/{o['backend']}/{o['trial']}"
                 for o, n in pairs if o.get("old_accepted") and not n.get("old_accepted"))
added = [f"{o['drawing']}/{o['backend']}/{o['trial']}"
         for o, n in pairs if n.get("old_accepted") and not o.get("old_accepted")]
check("new gate removes exactly the two blind-pocket false accepts",
      removed == ["bookend/openscad/trial-05", "enclosure/openscad/trial-04"], str(removed))
check("new gate never rescues a rejected run", added == [], str(added))

tr = [o for o, n in pairs if o.get("trusted") and o.get("old_accepted")]
killed = [f"{o['drawing']}/{o['backend']}/{o['trial']}" for o, n in pairs
          if o.get("trusted") and o.get("old_accepted") and not n.get("old_accepted")]
check("zero false rejections of trusted accepted rows", killed == [], f"{len(tr)} trusted, killed {killed}")
check("trusted accepted count is 6", len(tr) == 6, str(len(tr)))

def ratios(r):
    """Sorted-vs-sorted ratio signature: sorted(actual extents) vs sorted(derived
    sizes) — axis-order invariant, the form used in the calibration analysis."""
    rr = r.get("r1_ratios") or {}
    if len(rr) < 2:
        return ()
    a = sorted(v["actual_mm"] for v in rr.values())
    e = sorted(v["expected_mm"] for v in rr.values())
    return tuple(round(x / y, 3) for x, y in zip(a, e))
w1 = next(r for r in rows if r["drawing"] == "wheel" and r["trial"] == "trial-01" and r["backend"] == "usd-brep")
w2 = next(r for r in rows if r["drawing"] == "wheel" and r["trial"] == "trial-02" and r["backend"] == "usd-brep")
check("R1 rejection evidence: wheel false/trusted share identical ratio signatures",
      ratios(w1) == ratios(w2) and w1["trusted"] is False and w2["trusted"] is True, str(ratios(w1)))
prof = [r for r in rows if r["drawing"] == "profiles_empty_notes" and r["trusted"]]
check("R1 rejection evidence: trusted profiles row contains ratio 0.424",
      any(min(ratios(r)) < 0.5 for r in prof))

metrics = json.loads((DATA / "metrics.json").read_text())
check("metrics.json agrees with recomputed removals",
      sorted(x.split(":")[0] for x in metrics["r3_removed_from_accepted"]) == removed)

from doodle_to_cad.evaluation import openings_through_check
h = {"watertight": True, "components": 1, "through_holes": 0}
ok, msg = openings_through_check(h, 3, "front", True)
check("shipped gate rejects blind pockets with actionable text",
      ok is False and "blind pockets" in msg and "cut all the way through" in msg)
check("shipped gate passes true through-holes",
      openings_through_check({**h, "through_holes": 3}, 3, "front", True)[0] is True)
check("shipped gate stays silent non-strict / multi-component / missing genus",
      openings_through_check(h, 3, "front", False)[0]
      and openings_through_check({**h, "components": 2}, 3, "front", True)[0]
      and openings_through_check({**h, "through_holes": None}, 3, "front", True)[0])

t = subprocess.run([sys.executable, "-m", "pytest", "tests/test_evaluation_openings.py", "-q"],
                   cwd=REPO, capture_output=True, text=True, env={"PYTHONPATH": str(REPO), "PATH": "/usr/bin:/bin"})
check("issue tests pass (11)", "11 passed" in t.stdout, t.stdout[-120:])
suite = (HERE / "logs/full-suite.txt").read_text()
check("full-suite log records 262 passed", "262 passed" in suite)

sums = (HERE / "SHA256SUMS").read_text().splitlines()
verify = subprocess.run(["sha256sum", "-c", "SHA256SUMS"], cwd=HERE, capture_output=True, text=True)
check("SHA256SUMS verifies", verify.returncode == 0 and all("OK" in l for l in verify.stdout.splitlines()),
      f"{len(sums)} files")

failed = [n for n, ok, _ in results if not ok]
print(f"\n{len(results) - len(failed)}/{len(results)} PASS")
sys.exit(1 if failed else 0)
