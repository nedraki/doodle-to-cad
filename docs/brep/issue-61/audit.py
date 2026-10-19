#!/usr/bin/env python3
"""Re-verify every claim in README.md. Exit 0 only if all pass."""
import json, subprocess, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
sys.path.insert(0, str(REPO))

results = []
def check(name, ok, detail=""):
    results.append((name, bool(ok), detail))
    print(f"{'PASS' if ok else 'FAIL'}  {name}{(' — ' + detail) if detail else ''}")

from doodle_to_cad.build_contract import classify_kernel_crash, reproducer_hash, KERNEL_CRASH_SIGNATURE

fixture = Path(REPO) / "scripts/fixtures/omni_solid_minimal.recipe.json"
import hashlib
sha = hashlib.sha256(fixture.read_bytes()).hexdigest()
check("fixture sha256 consistent across fixture/contract/log",
      sha == reproducer_hash() and sha in (HERE / "logs/fixture.sha256").read_text(), sha[:16])
recipe = json.loads(fixture.read_text())
kinds = [op["kind"] for op in recipe["operations"]]
check("minimal fixture is arc_pipe + cylinder + union", kinds.count("arc_pipe") >= 1
      and "cylinder" in kinds and "union" in kinds, str(kinds))

r = subprocess.run([sys.executable, "scripts/repro_omni_solid.py", "--repeat", "3"], cwd=REPO,
                   capture_output=True, text=True,
                   env={"PATH": "/usr/bin:/bin", "HOME": str(Path.home()),
                        "DOODLE_BREP_PYTHON": str(REPO / "workers/brep/.venv/bin/python")})
check("reproducer: 3/3 deterministic crash with exact signature",
      r.returncode == 0 and "3/3 behaved as expected" in r.stdout and KERNEL_CRASH_SIGNATURE in r.stdout)
check("reproducer surfaces structured kernel_unavailable + advice",
      "kernel_unavailable" in r.stdout and "OpenSCAD backend" in r.stdout)

ladder = json.loads((HERE / "logs/shrink-ladder.json").read_text())
steps = ladder["steps"]
def behaved(s):
    if s["expected"] == "crash":
        return s["crashed"]
    if s["expected"] == "ok":
        return not s["crashed"]
    return True  # 'unknown' probes are recorded verbatim, not scored
bad = [s["case"] for s in steps if not behaved(s)]
check("ladder: every labeled step behaved as expected", not bad, f"{len(steps)} cases, bad={bad}")
def st(name):
    s = next(s for s in steps if s["case"] == name)
    return s["crashed"], s["expected"]
check("ladder: arc-only builds, arc180∩cap-union crashes, arc90∪cyl builds",
      st("arc_only")[0] is False and st("minimal_v1")[0] is True and st("arc90_union")[0] is False)
check("ladder: union partner being a box does NOT crash (trigger is cap-crossing cylinder/pipe)",
      st("arc_plus_box_union")[0] is False)

code, msg = classify_kernel_crash("boom: No module named '_omni_solid'")
check("classifier: exact signature -> kernel_unavailable + switch advice",
      code == "kernel_unavailable" and "OpenSCAD" in msg and sha[:12] in msg)
check("classifier: generic ModuleNotFoundError NOT absorbed",
      classify_kernel_crash("No module named 'numpy'") is None
      and classify_kernel_crash("watertight check failed") is None)

t = subprocess.run([sys.executable, "-m", "pytest", "tests/test_brep_kernel_containment.py", "-q"],
                   cwd=REPO, capture_output=True, text=True,
                   env={"PYTHONPATH": str(REPO), "PATH": "/usr/bin:/bin",
                        "DOODLE_BREP_PYTHON": str(REPO / "workers/brep/.venv/bin/python")})
check("containment tests pass (10, incl. planted errors)", "10 passed" in t.stdout, t.stdout[-90:])
suite = (HERE / "logs/full-suite.txt").read_text()
check("full-suite log records >= 261 passed", "261 passed" in suite or "262 passed" in suite)
frozen = [p for p in Path(REPO, "docs/brep/task-17-comparison/runs").rglob("row.json")
          if "_omni_solid" in p.read_text()]
check("frozen #34 crash rows are exactly the 3 curved_handle trials",
      len(frozen) == 3 and all("curved_handle" in str(p) for p in frozen), f"{len(frozen)} rows")
verify = subprocess.run(["sha256sum", "-c", "SHA256SUMS"], cwd=HERE, capture_output=True, text=True)
check("SHA256SUMS verifies", verify.returncode == 0, f"{verify.stdout.count('OK')} files OK")

failed = [n for n, ok, _ in results if not ok]
print(f"\n{len(results) - len(failed)}/{len(results)} PASS")
sys.exit(1 if failed else 0)
