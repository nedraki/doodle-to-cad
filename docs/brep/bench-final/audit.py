"""Claim gate for docs/brep/bench-final/README.md.

Recomputes every headline number from the published row.json artifacts and
fails if any README claim drifted. Run from repo root:
  PYTHONPATH=. .venv/bin/python docs/brep/bench-final/audit.py
"""
import glob
import hashlib
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
results = []


def check(name, ok, detail=""):
    results.append((name, bool(ok), detail))


rows = [json.load(open(f)) for f in glob.glob(str(HERE / "runs/*/*/trial-*/row.json"))]
os_ = [r for r in rows if r["backend"] == "openscad"]
usd = [r for r in rows if r["backend"] == "usd-brep"]
osd = [r for r in os_ if r.get("job_status") == "done"]
usdd = [r for r in usd if r.get("job_status") == "done"]

plan = json.loads((HERE / "TRIAL-PLAN.json").read_text())
check("matrix complete: 23 corpus x 2 backends x 2 trials = 92 rows",
      len(rows) == 92 and len(plan["corpus"]) == 23, f"rows={len(rows)}")
check("plan revision logged (dimension fix, 12 cells)",
      len(plan.get("plan_revisions", [])) == 1 and "12 cells" in plan["plan_revisions"][0]["cells"])
refs = json.loads((HERE / "references/reference-measurements.json").read_text())
kinds = {}
for v in refs.values():
    kinds[v["kind"]] = kinds.get(v["kind"], 0) + 1
check("references: 17 GT STL + 3 openscad refs + 3 no_ground_truth",
      kinds == {"ground_truth_stl": 17, "openscad_reference": 3, "no_ground_truth": 3}, str(kinds))

acc_os = sum(1 for r in osd if (r.get("product") or {}).get("accepted"))
bld_os = sum(1 for r in osd if (r.get("checks") or {}).get("build_success"))
ovr_os = sum(1 for r in osd if (r.get("checks") or {}).get("overall_pass"))
check("openscad: 44/46 done, 22 accepted, 42 build_ok, 2 GT overall_pass",
      (len(osd), acc_os, bld_os, ovr_os) == (44, 22, 42, 2),
      f"{len(osd)},{acc_os},{bld_os},{ovr_os}")
passed_usd = sum(1 for r in usdd if (r.get("product") or {}).get("status") == "passed")
bld_usd = sum(1 for r in usdd if (r.get("checks") or {}).get("build_success"))
check("usd-brep: 31/46 done, 0 status=passed, 31/31 build_ok",
      (len(usdd), passed_usd, bld_usd) == (31, 0, 31), f"{len(usdd)},{passed_usd},{bld_usd}")
check("errors published: openscad 2, usd-brep 15",
      len(os_) - len(osd) == 2 and len(usd) - len(usdd) == 15,
      f"{len(os_) - len(osd)}/{len(usd) - len(usdd)}")
q_os = sum(r.get("questions_asked") or 0 for r in os_)
q_usd = sum(r.get("questions_asked") or 0 for r in usd)
check("questions: openscad 0 (ask off), usd-brep 9", (q_os, q_usd) == (0, 9), f"{q_os}/{q_usd}")

# wheel at corrected 120 mm: extents AND genus pass both trials
wh = [json.load(open(f)) for f in glob.glob(str(HERE / "runs/wheel/openscad/trial-*/row.json"))]
check("wheel @120 mm: both trials pass extents and genus (spokes present)",
      len(wh) == 2 and all(r["checks"]["extents_pass"] and r["checks"]["genus_pass"]
                           and r["build"]["genus"] == 8 for r in wh))
# bevelled block full GT pass both trials
bb = [json.load(open(f)) for f in glob.glob(str(HERE / "runs/bevelled_block/openscad/trial-*/row.json"))]
check("bevelled_block: 2/2 GT overall_pass", all(r["checks"]["overall_pass"] for r in bb) and len(bb) == 2)
# vase: usd-brep refused (error rows), never a bogus solid
vase = [r for r in rows if r["drawing"] == "002_greek_vase_silhouette" and r["backend"] == "usd-brep"]
check("greek vase usd-brep: refusal errors, no built mesh",
      all(r["job_status"] == "error" and not (r.get("build") or {}).get("watertight") for r in vase))
# honesty: every error row carries a message (no silent skips)
check("every error row publishes a message",
      all((r.get("error") or {}).get("message") for r in rows if r.get("job_status") == "error"))
# README consistency
text = (HERE / "README.md").read_text()
check("README headline table matches", "22/44 (50%)" in text and "31/31 (100%)" in text
      and "0/31 (0%)" in text)
# frozen plan precedes trials (honesty rule from #34, reused) — compare parsed datetimes
from datetime import datetime
first = min(datetime.fromisoformat(r["submitted_at"]) for r in rows if r.get("submitted_at"))
check("plan frozen_at precedes every trial",
      datetime.fromisoformat(plan["frozen_at"]) < first)
# montages: every published image exists and its underlying row still says what the caption claims
MONTAGES = {
    "003_front_grille_multiview_t1.png": ("003_front_grille_multiview", "usd-brep", 1, "failed"),
    "wheel_t2.png": ("wheel", "usd-brep", 2, "failed"),
    "constant_radius_handle_t1.png": ("constant_radius_handle", "usd-brep", 1, "failed"),
    "007_angle_bracket_holes_t1.png": ("007_angle_bracket_holes", "usd-brep", 1, "failed"),
    "101_bltouch_bracket_t1.png": ("101_bltouch_bracket", "usd-brep", 1, "failed"),
    "002_greek_vase_silhouette_t1.png": ("002_greek_vase_silhouette", "usd-brep", 1, "error"),
}
for name, (drw, be, tr, want) in MONTAGES.items():
    img = HERE / "images" / name
    r = json.load(open(HERE / "runs" / drw / be / f"trial-{tr:02d}" / "row.json"))
    got = (r.get("product") or {}).get("status") or r.get("job_status")
    check(f"montage {name} committed + row verdict={want}",
          img.exists() and img.stat().st_size > 10000 and got == want, f"verdict={got}")

# planted-error self-test
saved = results[:]
results.clear()
check("planted-error probe (must FAIL and prove the gate is live)", 1 == 2)
self_test_failed = any(not ok for _, ok, _ in results)
results[:] = saved
check("planted-error probe actually failed", self_test_failed)

fails = [n for n, ok, _ in results if not ok]
for n, ok, d in results:
    print(("PASS" if ok else "FAIL"), n, d)
print(f"{len(results) - len(fails)}/{len(results)} PASS")
sys.exit(1 if fails else 0)
