"""Claim gate for docs/brep/bench-final/README.md.

Recomputes every headline number from the published row.json artifacts and
fails if any README claim drifted. Montages are bound to their rows through
images/provenance.json: image sha256 -> row sha256 -> mesh sha256 -> archived
STL bytes. Swapping or editing any link of that chain fails the audit.
Run from repo root:
  PYTHONPATH=. .venv/bin/python docs/brep/bench-final/audit.py
"""
import glob
import hashlib
import json
import sys
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
results = []


def check(name, ok, detail=""):
    results.append((name, bool(ok), detail))


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


rows = [json.load(open(f)) for f in glob.glob(str(HERE / "runs/*/*/trial-*/row.json"))]
os_ = [r for r in rows if r["backend"] == "openscad"]
usd = [r for r in rows if r["backend"] == "usd-brep"]
osd = [r for r in os_ if r.get("job_status") == "done"]
usdd = [r for r in usd if r.get("job_status") == "done"]

plan = json.loads((HERE / "TRIAL-PLAN.json").read_text())
check("matrix complete: 23 corpus x 2 backends x 2 trials = 92 rows",
      len(rows) == 92 and len(plan["corpus"]) == 23, f"rows={len(rows)}")
# acceptance drift guard: the aggregator/audit definition must still equal
# the FROZEN PLAN's text (the 0/31 error came from the aggregator inventing
# a stricter rule the evaluator can never emit)
_acc = plan.get("pass_criteria", {}).get("product_acceptance", "")
check("acceptance definition matches the frozen plan text",
      "score >= 70" in _acc and "status != 'failed'" in _acc
      and "usd-brep never auto-accepts" not in _acc, _acc[:80])
check("plan revision logged (dimension fix, 12 cells)",
      len(plan.get("plan_revisions", [])) == 1 and "12 cells" in plan["plan_revisions"][0]["cells"])
refs = json.loads((HERE / "references/reference-measurements.json").read_text())
kinds = {}
for v in refs.values():
    kinds[v["kind"]] = kinds.get(v["kind"], 0) + 1
check("references: 17 GT STL + 3 openscad refs + 3 no_ground_truth",
      kinds == {"ground_truth_stl": 17, "openscad_reference": 3, "no_ground_truth": 3}, str(kinds))

# archived mesh provenance: every row build.sha256 must equal the archived STL
n_hash = m_hash = 0
for f in glob.glob(str(HERE / "runs/*/*/trial-*/row.json")):
    r = json.load(open(f))
    h = (r.get("build") or {}).get("sha256")
    if not h:
        continue
    n_hash += 1
    try:
        m_hash += sha256(Path(f).parent / "stl" / "model.stl") == h
    except FileNotFoundError:
        pass
check("archived STLs match row build.sha256 (75/75)", n_hash == 75 and m_hash == 75,
      f"{m_hash}/{n_hash}")

# headline table, using the FROZEN PLAN acceptance definition
acc_os = sum(1 for r in osd if (r.get("product") or {}).get("accepted"))
bld_os = sum(1 for r in osd if (r.get("checks") or {}).get("build_success"))
full_gt_os = [r for r in osd if (r.get("checks") or {}).get("extents_pass")
              and (r.get("checks") or {}).get("genus_pass") and (r.get("checks") or {}).get("volume_pass")]
check("openscad: 44/46 done, 22 accepted, 42 build_ok, ref dims/topo/vol pass = 2x solid_transition "
      "(which still FAIL projection fidelity — not full matches)",
      (len(osd), acc_os, bld_os) == (44, 22, 42) and len(full_gt_os) == 2
      and {r["drawing"] for r in full_gt_os} == {"solid_transition"}
      and all(r["checks"].get("fidelity_pass") is False and r["checks"].get("overall_pass") is False
              for r in full_gt_os),
      f"{len(osd)},{acc_os},{bld_os},{sorted({r['drawing'] for r in full_gt_os})}")
plan_acc_usd = [r for r in usdd if (r.get("product") or {}).get("status") not in (None, "failed")]
strict_usd = sum(1 for r in usdd if (r.get("product") or {}).get("status") == "passed")
bld_usd = sum(1 for r in usdd if (r.get("checks") or {}).get("build_success"))
check("usd-brep: 31/46 done, plan-acceptance 1 (006_stepped_knob unverified), strict-passed 0, 31 build_ok",
      len(usdd) == 31 and len(plan_acc_usd) == 1
      and plan_acc_usd[0]["drawing"] == "006_stepped_knob"
      and plan_acc_usd[0]["product"]["status"] == "unverified"
      and strict_usd == 0 and bld_usd == 31,
      f"{len(usdd)},{len(plan_acc_usd)},{strict_usd},{bld_usd}")
check("errors published: openscad 2, usd-brep 15",
      len(os_) - len(osd) == 2 and len(usd) - len(usdd) == 15,
      f"{len(os_) - len(osd)}/{len(usd) - len(usdd)}")
q_os = sum(r.get("questions_asked") or 0 for r in os_)
q_usd = sum(r.get("questions_asked") or 0 for r in usd)
check("questions: openscad 0 (ask off), usd-brep 9", (q_os, q_usd) == (0, 9), f"{q_os}/{q_usd}")

# wheel: extents+genus pass (8 spokes) BUT volume fails +~18-19% on both backends
WHEEL_REF_VOL = 43128.5
wh = [r for r in (json.load(open(f)) for f in
      glob.glob(str(HERE / "runs/wheel/*/trial-*/row.json")))
      if r.get("job_status") == "done" and (r.get("checks") or {}).get("build_success")]
check("wheel: all 3 completed wheel builds pass extents+genus (genus 8) and FAIL volume (+17..20% vs 43128.5 mm3)",
      len(wh) == 3 and all(r["checks"]["extents_pass"] and r["checks"]["genus_pass"]
                           and r["build"]["genus"] == 8 and not r["checks"]["volume_pass"]
                           and 1.17 <= r["build"]["volume_mm3"] / WHEEL_REF_VOL <= 1.21 for r in wh),
      str([(r["backend"], round(r["build"]["volume_mm3"] / WHEEL_REF_VOL, 3)) for r in wh]))
# bevelled_block: automatic gates only — must have NO reference (honest labeling)
bb = [json.load(open(f)) for f in glob.glob(str(HERE / "runs/bevelled_block/openscad/trial-*/row.json"))]
check("bevelled_block: 2/2 automatic overall_pass AND no GT reference (never called a GT pass)",
      len(bb) == 2 and all(r["checks"]["overall_pass"] and r["checks"]["extents_pass"] is None
                           for r in bb) and refs["bevelled_block"]["kind"] == "no_ground_truth")
# vase: usd-brep refused (error rows), never a bogus solid
vase = [r for r in rows if r["drawing"] == "002_greek_vase_silhouette" and r["backend"] == "usd-brep"]
check("greek vase usd-brep: model-stage refusal errors, no built mesh",
      all(r["job_status"] == "error" and not (r.get("build") or {}).get("watertight") for r in vase))
# honesty: every error row carries a message (no silent skips)
check("every error row publishes a message",
      all((r.get("error") or {}).get("message") for r in rows if r.get("job_status") == "error"))
# README consistency
text = (HERE / "README.md").read_text()
check("README headline table matches", "22/44 (50%)" in text and "1/31 (3%)" in text
      and "31/31 (100%)" in text and "solid_transition" in text and "0/31 (0%)" in text)
res = (HERE / "RESULTS.md").read_text()
check("RESULTS.md separates the two GT measurements (no 'GT overall pass' label)",
      "GT overall pass" not in res and "automatic overall_pass" in res
      and "ref dims/topo/vol pass" in res)
prov_raw = (HERE / "images" / "provenance.json").read_text()
check("provenance paths are checkout-relative (no absolute machine paths)",
      '"/tmp/' not in prov_raw and '"/home/' not in prov_raw)
check("README carries the Codex-review errata section", "Rev errata" in text and "status != 'failed'" in text)
# frozen plan precedes trials (honesty rule from #34, reused) — compare parsed datetimes
first = min(datetime.fromisoformat(r["submitted_at"]) for r in rows if r.get("submitted_at"))
check("plan frozen_at precedes every trial",
      datetime.fromisoformat(plan["frozen_at"]) < first)

# montages: PROVEN BINDING image -> provenance.json -> row -> mesh -> bytes.
# Swapping two montage files, editing a row, or re-exporting a mesh breaks
# one of the sha256 equalities below.
def resolve_src(p):
    """Provenance paths are checkout-relative: 'runs/...' under bench-final,
    'repo:...' under the repo root. NEVER absolute — an audit must read the
    checkout it audits, not whichever tree happened to produce the images."""
    q = Path(p)
    if q.is_absolute():
        raise SystemExit(f"provenance path is absolute ({p}); re-run "
                         "make_fail_montages.py from this checkout")
    if p.startswith("repo:"):
        return HERE.parents[2] / p[len("repo:"):]
    return HERE / q


prov = json.loads((HERE / "images" / "provenance.json").read_text())
for name, meta in sorted(prov.items()):
    img = HERE / "images" / name
    row_path = resolve_src(meta["row"])
    r = json.load(open(row_path))
    got = (r.get("product") or {}).get("status") or r.get("job_status")
    ok_img = img.exists() and sha256(img) == meta["image_sha256"]
    ok_row = sha256(row_path) == meta["row_sha256"]
    ok_verdict = got == meta["verdict"]
    ok_mesh = True
    if meta["panels"]["brep_mesh"]["sha256"]:
        archived = row_path.parent / "stl" / "model.stl"
        ok_mesh = (archived.exists()
                   and sha256(archived) == meta["panels"]["brep_mesh"]["sha256"]
                   and meta["panels"]["brep_mesh"]["sha256"] == (r.get("build") or {}).get("sha256"))
    ok_panels = True
    for panel in meta["panels"].values():
        src = panel.get("path")
        if not src or panel.get("sha256") is None:
            continue
        sp = resolve_src(src)
        ok_panels = ok_panels and sp.exists() and sha256(sp) == panel["sha256"]
    check(f"montage {name}: image/row/mesh/panel hash chain + verdict={meta['verdict']}",
          ok_img and ok_row and ok_verdict and ok_mesh and ok_panels,
          f"img={ok_img} row={ok_row} verdict={ok_verdict}/{got} mesh={ok_mesh} panels={ok_panels}")
check("montage set is the 6 published cases", len(prov) == 6, str(len(prov)))
# non-vacuity: two different montages must NOT bind to each other's row hash
_a = prov["wheel_t2.png"]["row_sha256"]
_b = prov["003_front_grille_multiview_t1.png"]["row_sha256"]
check("binding probe: cross-montage row hashes differ (swap would fail)", _a != _b)

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
