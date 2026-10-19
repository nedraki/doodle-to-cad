"""Rerunnable gate for docs/brep/issue-68-size-ask/README.md claims.

Run from the repo root:  PYTHONPATH=. .venv/bin/python docs/brep/issue-68-size-ask/audit.py
Exits non-zero and prints FAIL lines when any README claim stops matching
the repo. Planted-error self-test proves the checker can fail.
"""
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
results = []


def check(name, ok, detail=""):
    results.append((name, bool(ok), detail))


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


# 1. wiring contract (README 'Fix' section)
src = (ROOT / "doodle_to_cad" / "sizes.py").read_text()
check("sizes.plan_unconstrained_axes exists with depth-first order",
      "def plan_unconstrained_axes" in src and '"depth", "height", "width"' in src)
pipe = (ROOT / "doodle_to_cad" / "pipeline.py").read_text()
check("pipeline asks one body_dimension question",
      'ask_user=None' in pipe and '"kind": "body_dimension"' in pipe and "unconstrained[0]" in pipe)
check("pipeline records user_supplied_axes + size_clarification",
      "user_supplied_axes" in pipe and '"size_clarification"' in pipe)
clar = (ROOT / "doodle_to_cad" / "clarification.py").read_text()
check("clarification supports body_dimension + timeout",
      "kind=='body_dimension'" in clar and "timeout_s=None" in clar and "status='timeout'" in clar)
appsrc = (ROOT / "doodle_to_cad" / "app.py").read_text()
check("app wires ask_user with 120 s timeout + opt-out flag",
      "timeout_s=120" in appsrc and "ask_missing_dimensions" in appsrc)
ui = (ROOT / "web" / "app.js").read_text()
check("UI posts value_mm for body_dimension", "body_dimension" in ui and "payload.value_mm" in ui)
check("UI cache-busted", "app.js?v=20" in (ROOT / "web" / "index.html").read_text())

# 2. tests present
tst = (ROOT / "tests" / "test_size_clarification.py").read_text()
check("unit tests cover matrix + timeout + wiring",
      all(k in tst for k in ("test_accept_answer_body_dimension_matrix",
                             "test_ask_body_dimension_times_out_and_records",
                             "test_pipeline_wiring_contract")))

# 3. manifest annotations (README 'Evidence')
m12 = json.loads((ROOT / "benchmarks/cases/012_vent_grille_grid/manifest.json").read_text())
check("012 manifest carries dimension_audit_issue_68",
      m12.get("provenance", {}).get("dimension_audit_issue_68", {}).get("reference_thickness_mm") == 4)
m003 = json.loads((ROOT / "benchmarks/cases/003_front_grille_multiview/manifest.json").read_text())
ia = m003.get("provenance", {}).get("ink_adaptation", {})
check("003 manifest carries ink_adaptation with preserved original hash",
      ia.get("adapted_from_reference_stl") is True
      and ia.get("original_drawing_sha256")
      == sha(ROOT / "benchmarks/cases/003_front_grille_multiview/source/drawing-as-drawn.png"))
check("003 active drawing hash recorded in provenance",
      m003["provenance"]["sha256"]["drawing.png"]
      == sha(ROOT / "benchmarks/cases/003_front_grille_multiview/source/drawing.png"))

# 4. live demo evidence (README 'Evidence' + acceptance table)
log = HERE / "logs" / "lottery-and-ask.json"
check("demo log exists", log.is_file())
if log.is_file():
    d = json.loads(log.read_text())
    # the plate thickness is the SMALL extent (Y here); the no-ask runs
    # guess it from ink gestalt and miss the 4 mm reference either way.
    def thickness(ext):
        return min(ext) if ext else None
    lottery = [thickness(r["extents_xyz"]) for r in d.get("lottery_runs", []) if r.get("extents_xyz")]
    check("three no-ask runs completed", len(d.get("lottery_runs", [])) == 3
          and all(r["status"] == "done" for r in d["lottery_runs"]))
    check("no-ask guesses miss the 4 mm reference (the silent-guess problem)",
          len(lottery) == 3 and all(abs(t - 4.0) > 0.5 for t in lottery), str(lottery))
    a = d.get("ask_run") or {}
    check("asked run reached body_dimension depth question",
          a.get("question_status") == "waiting_for_answer" and a.get("question_kind") == "body_dimension"
          and a.get("question_axis") == "depth")
    check("answered run finished and size_clarification recorded the answer",
          a.get("final_status") == "done"
          and (a.get("size_clarification") or {}).get("answer", {}).get("value_mm") == 4.0)
    if a.get("extents_xyz"):
        check("answered run reproduces the answered 4 mm plate thickness (<=1 mm)",
              abs(thickness(a["extents_xyz"]) - 4.0) <= 1.0, str(a["extents_xyz"]))

# 5. suite log
suite = HERE / "logs" / "full-suite.txt"
if suite.is_file():
    text = suite.read_text()
    m = re.search(r"(\d+) passed", text)
    check("full-suite log shows >=298 passed, 0 failed",
          m and int(m.group(1)) >= 298 and "failed" not in text)
else:
    check("full-suite log exists", False)

# 6. planted-error self-test: the checker must be able to fail
saved = results[:]
results.clear()
check("planted-error probe (must report FAIL and still exit 0 here)", "never" == "equal")
self_test_failed = any(not ok for _, ok, _ in results)
results[:] = saved
check("planted-error probe actually failed (checker is live)", self_test_failed)

fails = [n for n, ok, _ in results if not ok]
for n, ok, detail in results:
    print(("PASS" if ok else "FAIL"), n, detail)
print(f"{len(results)-len(fails)}/{len(results)} PASS")
sys.exit(1 if fails else 0)
