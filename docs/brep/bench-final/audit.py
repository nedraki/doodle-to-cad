"""Claim gate for docs/brep/bench-final/ (issue #79 hardening).

What this audit proves, in the order it runs:

1. HARD PREREQUISITES (abort = exit 2, no report written):
   * MANIFEST.json exists, parses, and equals a fresh seal of the bytes in
     THIS checkout (runs/**, references/**, images/**, TRIAL-PLAN.json, plus
     recorded provenance/reference source files). Missing file, hash drift or
     an unsealed extra artifact aborts, naming trial + path.
   * Every trial cell directory parses; a corrupt row.json aborts naming the
     cell. Row fields (drawing/backend/trial) must match their directory.
   * Cell coverage is the frozen plan's exact set: corpus x 2 backends x
     trials 1..2. Missing, duplicate and unexpected cells are each listed.
     (Total row count is NOT treated as proof of coverage.)
   * runs/index.jsonl equals the archived row.json set.

2. SEMANTIC CHECKS (FAIL lines, exit 1): montage hash-chain bindings, panel
   pair walker, montage-vs-row mesh equality, references inventory, headline
   tables + metric definitions recomputed via metrics.py and compared
   verbatim to README.md and RESULTS.md, historical frozen counts, wording
   guards (genus never == spoke count; extents+volume never == shape
   agreement), excluded/superseded bookkeeping, disclosures preserved.

Every artifact is resolved against the checkout this file lives in — never
an absolute recorded path. Results are written atomically to
audit-result.json with an environment fingerprint.

Run from repo root:  python3 docs/brep/bench-final/audit.py
"""
import glob
import hashlib
import json
import os
import platform
import socket
import subprocess
import sys
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
sys.path.insert(0, str(HERE))
import metrics  # noqa: E402
from make_manifest import build_manifest, resolve_recorded  # noqa: E402

results = []


def check(name, ok, detail=""):
    results.append((name, bool(ok), detail))


def abort(what, path, detail=""):
    """Clear, non-skippable failure with trial + path. Writes NO report."""
    print(f"AUDIT ABORT: {what}\n  path: {path}" + (f"\n  detail: {detail}" if detail else ""))
    sys.exit(2)


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load_json(path, what):
    try:
        return json.loads(Path(path).read_text())
    except FileNotFoundError:
        abort(what, path, "file missing")
    except json.JSONDecodeError as e:
        abort(what, path, f"corrupt JSON: {e}")


def resolve_src(p):
    """Recorded paths are checkout-relative: 'runs/...' under bench-final,
    'repo:...' under the repo root. NEVER absolute — an audit must read the
    checkout it audits, not whichever tree happened to produce the images."""
    q = Path(p)
    if q.is_absolute():
        abort("absolute recorded path (re-seal from this checkout)", p)
    if p.startswith("repo:"):
        return REPO / p[len("repo:"):]
    return HERE / q


# ============================================================ 1. hard gates
manifest_path = HERE / "MANIFEST.json"
manifest = load_json(manifest_path, "evidence manifest")
fresh = build_manifest()
if "files" not in manifest:
    abort("evidence manifest has no files block", manifest_path)
sealed, actual = manifest["files"], fresh["files"]
drift = []
for k, v in sorted(sealed.items()):
    a = actual.get(k)
    if a is None:
        drift.append(f"sealed file missing: {k}")
    elif a["sha256"] != v["sha256"]:
        drift.append(f"hash differs from sealed bytes: {k}")
for k in sorted(set(actual) - set(sealed)):
    drift.append(f"unsealed artifact on disk (not in MANIFEST.json): {k}")
if drift:
    abort("evidence manifest does not match the bytes in this checkout",
          manifest_path, "; ".join(drift[:8]) + (f" (+{len(drift) - 8} more)" if len(drift) > 8 else ""))

# trial cells: parse, identity, coverage vs the frozen plan
plan = load_json(HERE / "TRIAL-PLAN.json", "frozen trial plan")
cell_dirs = sorted(glob.glob(str(HERE / "runs" / "*" / "*" / "trial-*")))
rows, cell_seen, dupes, id_bad = [], {}, [], []
for d in cell_dirs:
    d = Path(d)
    rp = d / "row.json"
    r = load_json(rp, f"trial row {d.relative_to(HERE)}")
    dname, bname, tname = d.parent.parent.name, d.parent.name, d.name
    if not (tname.startswith("trial-") and tname[6:].isdigit()):
        abort("trial directory name malformed", d)
    trial = int(tname[6:])
    if (r.get("drawing"), r.get("backend"), r.get("trial")) != (dname, bname, trial):
        id_bad.append(f"{d.relative_to(HERE)}: row says {r.get('drawing')}/{r.get('backend')}/t{r.get('trial')}")
    key = (dname, bname, trial)
    if key in cell_seen:
        dupes.append(str(key))
    cell_seen[key] = r
    rows.append(r)
if id_bad:
    abort("row identity does not match its directory", "; ".join(id_bad[:4]))
corpus_ids = [c["id"] for c in plan["corpus"]]
expected_cells = {(c, b, t) for c in corpus_ids for b in metrics.BACKENDS for t in (1, 2)}
missing = sorted(str(k) for k in expected_cells - set(cell_seen))
unexpected = sorted(str(k) for k in set(cell_seen) - expected_cells)
if missing or unexpected or dupes:
    abort("cell coverage does not match the frozen plan", HERE / "runs",
          f"missing={missing[:3]} unexpected={unexpected[:3]} duplicated={dupes[:3]}")

index_rows = []
for ln in (HERE / "runs" / "index.jsonl").read_text().splitlines():
    try:
        index_rows.append(json.loads(ln))
    except json.JSONDecodeError as e:
        abort("runs/index.jsonl corrupt", HERE / "runs" / "index.jsonl", str(e))
idx = {(r.get("drawing"), r.get("backend"), r.get("trial")): r for r in index_rows}
idx_mismatch = [str(k) for k, r in cell_seen.items() if idx.get(k) != r]
extra_idx = sorted(str(k) for k in set(idx) - set(cell_seen))
if idx_mismatch or extra_idx:
    abort("runs/index.jsonl disagrees with archived row.json files", HERE / "runs" / "index.jsonl",
          f"mismatched={idx_mismatch[:3]} extra={extra_idx[:3]}")

# ============================================================ 2. semantic
os_ = [r for r in rows if r["backend"] == "openscad" and not metrics.exclusion(r)]
usd = [r for r in rows if r["backend"] == "usd-brep" and not metrics.exclusion(r)]
osd = [r for r in os_ if r.get("job_status") == "done"]
usdd = [r for r in usd if r.get("job_status") == "done"]

check("cell coverage = exact plan set: 23 corpus x 2 backends x 2 trials = 92 "
      "(total count is not used as coverage proof)",
      len(expected_cells) == 92 and len(cell_seen) == 92 and len(plan["corpus"]) == 23,
      f"cells={len(cell_seen)}")
check("manifest seals every artifact (rows, meshes, inputs, references, plan, montages)",
      len(sealed) >= 250, f"{len(sealed)} sealed files")

# acceptance drift guard: the aggregator/audit definition must still equal
# the FROZEN PLAN's text (the 0/31 error came from the aggregator inventing
# a stricter rule the evaluator can never emit)
_acc = plan.get("pass_criteria", {}).get("product_acceptance", "")
check("acceptance definition matches the frozen plan text",
      "score >= 70" in _acc and "status != 'failed'" in _acc
      and "usd-brep never auto-accepts" not in _acc, _acc[:80])
check("plan revision logged (dimension fix, 12 cells)",
      len(plan.get("plan_revisions", [])) == 1 and "12 cells" in plan["plan_revisions"][0]["cells"])

refs = load_json(HERE / "references" / "reference-measurements.json", "reference measurements")
prov = load_json(HERE / "images" / "provenance.json", "montage provenance")
kinds = {}
for v in refs.values():
    kinds[v["kind"]] = kinds.get(v["kind"], 0) + 1
check("references: 17 GT STL + 3 openscad refs + 3 no_ground_truth",
      kinds == {"ground_truth_stl": 17, "openscad_reference": 3, "no_ground_truth": 3}, str(kinds))
# every recorded reference SOURCE exists and its sealed bytes verify (the
# measurements must belong to a real model, not a float)
src_bad = []
for drawing, v in refs.items():
    src = v.get("source")
    if not src:
        continue
    try:
        key, p = resolve_recorded(src)
    except SystemExit as e:  # absolute pointer / missing source = published FAIL, not skip
        src_bad.append(f"{drawing}: {e}")
        continue
    entry = manifest["files"].get(key)
    if entry is None or not p.exists() or sha256(p) != entry["sha256"]:
        src_bad.append(drawing)
check("reference sources sealed and byte-verified (repo-relative pointers only)",
      not src_bad, str(src_bad[:3]))

# archived mesh provenance: every row build.sha256 must equal the archived STL
n_hash = m_hash = 0
mesh_bad = []
for key, r in cell_seen.items():
    h = (r.get("build") or {}).get("sha256")
    if not h:
        continue
    n_hash += 1
    stl = HERE / "runs" / key[0] / key[1] / f"trial-{key[2]:02d}" / "stl" / "model.stl"
    if stl.exists() and sha256(stl) == h:
        m_hash += 1
    else:
        mesh_bad.append(f"{key} ({stl.relative_to(HERE)})")
check("archived STLs match row build.sha256 (75/75)", n_hash == 75 and m_hash == 75,
      f"{m_hash}/{n_hash} bad={mesh_bad[:2]}")

# ---------------- metrics: one definition, recomputed, compared verbatim
decisions_path = HERE / "review" / "decisions.json"
decisions = json.loads(decisions_path.read_text()) if decisions_path.exists() else {}
rows_by_backend = {"openscad": rows, "usd-brep": rows}
stats = metrics.compute(rows_by_backend, refs, decisions)
tables_block = "\n".join(metrics.tables_block_lines(stats))
defs_block = "\n".join(metrics.definitions_block_lines())

text = (HERE / "README.md").read_text()
res_md = (HERE / "RESULTS.md").read_text()
check("README headline tables equal the metrics-recomputed tables (one definition)",
      tables_block in text, "AUDIT:TABLE block mismatch")
check("RESULTS.md headline tables equal the metrics-recomputed tables",
      tables_block in res_md, "AUDIT:TABLE block mismatch")
check("README publishes the metric definitions verbatim", defs_block in text,
      "AUDIT:METRICS block mismatch")

# ---------------- historical frozen counts (kept labeled, never silently edited)
acc_os = sum(1 for r in osd if (r.get("product") or {}).get("accepted"))
bld_os = sum(1 for r in osd if (r.get("checks") or {}).get("build_success"))
full_gt_os = [r for r in osd if all((r.get("checks") or {}).get(k) is True
                                    for k in ("extents_pass", "genus_pass", "volume_pass"))]
check("HISTORICAL frozen-plan counts: openscad 44/46 done, 22 accepted, 42 build_ok; "
      "ref dims/topo/vol = 2x solid_transition (still FAIL projection — not full matches)",
      (len(osd), acc_os, bld_os) == (44, 22, 42) and len(full_gt_os) == 2
      and {r["drawing"] for r in full_gt_os} == {"solid_transition"}
      and all(r["checks"].get("fidelity_pass") is False and r["checks"].get("overall_pass") is False
              for r in full_gt_os),
      f"{len(osd)},{acc_os},{bld_os},{sorted({r['drawing'] for r in full_gt_os})}")
plan_acc_usd = [r for r in usdd if (r.get("product") or {}).get("status") not in (None, "failed")]
strict_usd = sum(1 for r in usdd if (r.get("product") or {}).get("status") == "passed")
bld_usd = sum(1 for r in usdd if (r.get("checks") or {}).get("build_success"))
check("HISTORICAL frozen-plan counts: usd-brep 31/46 done, plan-acceptance 1 "
      "(006_stepped_knob UNVERIFIED — reported separately from failed and from full acceptance), "
      "strict-passed 0 (historical label), 31 build_ok",
      len(usdd) == 31 and len(plan_acc_usd) == 1
      and plan_acc_usd[0]["drawing"] == "006_stepped_knob"
      and plan_acc_usd[0]["product"]["status"] == "unverified"
      and strict_usd == 0 and bld_usd == 31,
      f"{len(usdd)},{len(plan_acc_usd)},{strict_usd},{bld_usd}")
check("errors published (kept as outcomes, not skipped): openscad 2, usd-brep 15",
      len(os_) - len(osd) == 2 and len(usd) - len(usdd) == 15,
      f"{len(os_) - len(osd)}/{len(usd) - len(usdd)}")
q_os = sum(r.get("questions_asked") or 0 for r in os_)
q_usd = sum(r.get("questions_asked") or 0 for r in usd)
check("questions: openscad 0 (ask off), usd-brep 9", (q_os, q_usd) == (0, 9), f"{q_os}/{q_usd}")

# wheel: extents+genus pass BUT volume fails — and genus is never read as spokes
WHEEL_REF_VOL = 43128.5
wh = [r for r in (cell_seen[k] for k in cell_seen if k[0] == "wheel")
      if r.get("job_status") == "done" and (r.get("checks") or {}).get("build_success")]
check("wheel: all 3 completed wheel builds pass extents+genus (genus==8 is a "
      "topology-connection count only) and FAIL volume (+17..20% vs 43128.5 mm3)",
      len(wh) == 3 and all(r["checks"]["extents_pass"] and r["checks"]["genus_pass"]
                           and r["build"]["genus"] == 8 and not r["checks"]["volume_pass"]
                           and 1.17 <= r["build"]["volume_mm3"] / WHEEL_REF_VOL <= 1.21 for r in wh),
      str([(r["backend"], round(r["build"]["volume_mm3"] / WHEEL_REF_VOL, 3)) for r in wh]))

bb = [cell_seen[k] for k in cell_seen if k[0] == "bevelled_block" and k[1] == "openscad"]
check("bevelled_block: 2/2 automatic overall_pass AND no GT reference (never called a GT pass)",
      len(bb) == 2 and all(r["checks"]["overall_pass"] and r["checks"]["extents_pass"] is None
                           for r in bb) and refs["bevelled_block"]["kind"] == "no_ground_truth")
vase = [cell_seen[k] for k in cell_seen if k[0] == "002_greek_vase_silhouette" and k[1] == "usd-brep"]
check("greek vase usd-brep: model-stage refusal errors, no built mesh",
      all(r["job_status"] == "error" and not (r.get("build") or {}).get("watertight") for r in vase))
check("every error row publishes a message",
      all((r.get("error") or {}).get("message") for r in rows if r.get("job_status") == "error"))

# trial-log server model must equal the model the plan froze
log = (HERE / "logs-trials.log").read_text()
models = {ln.split(":", 1)[1].strip() for ln in log.splitlines() if ln.startswith("server model:")}
check("trial-log server model matches the frozen plan model",
      models == {plan["model_settings"]["selected_model"]}, str(sorted(models))[:90])

# ---------------- wording guards: no overclaim vocabulary anywhere published
bad_wording = []
for label, t in (("README", text), ("RESULTS.md", res_md)):
    for phrase in ("GT overall pass", "all spokes present", "all 8 spokes present",
                   "complete GT match", "GT pass ("):
        if phrase in t:
            bad_wording.append(f"{label}: '{phrase}'")
    if "automatic overall_pass" not in t or "ref dims/topo/vol" not in t:
        bad_wording.append(f"{label}: missing separated-metric labels")


def walk_paths(node, found):
    if isinstance(node, dict):
        if isinstance(node.get("path"), str) and node["path"].startswith("/"):
            found.append(node["path"])
        for v in node.values():
            walk_paths(v, found)
    elif isinstance(node, list):
        for v in node:
            walk_paths(v, found)
    return found


abs_paths = walk_paths(prov, [])
if abs_paths:
    bad_wording.append(f"provenance.json: absolute path(s) {abs_paths[:2]}")
check("no overclaim wording (dims!=shape agreement, genus!=spoke count) and "
      "no absolute machine paths", not bad_wording, str(bad_wording[:3]))
check("README carries the Codex-review errata section + the 12-deleted-cells disclosure",
      "Rev errata" in text and "status != 'failed'" in text and "12 cells" in text and "deleted" in text)

# frozen plan precedes trials (honesty rule from #34, reused) — compare parsed datetimes
first = min(datetime.fromisoformat(r["submitted_at"]) for r in rows if r.get("submitted_at"))
check("plan frozen_at precedes every trial",
      datetime.fromisoformat(plan["frozen_at"]) < first)

# ---------------- excluded/superseded bookkeeping
excl_bad, excl_rows = [], [r for r in rows if metrics.exclusion(r)]
for r in excl_rows:
    e = metrics.exclusion(r)
    if not e.get("reason") or not e.get("replaced_by"):
        excl_bad.append(f"{r['drawing']}/{r['backend']}/t{r['trial']}: {e}")
    else:
        rb = str(e["replaced_by"])
        repl_dir = HERE / "runs" / r["drawing"] / r["backend"] / f"trial-{rb}"
        if "trial-" not in rb or not repl_dir.exists():
            excl_bad.append(f"{r['drawing']}: replaced_by '{rb}' has no directory")
check("excluded/superseded rows are published, carry reason+replaced_by, and are "
      "counted in NO metric", not excl_bad, f"{len(excl_rows)} excluded; bad={excl_bad[:2]}")

# ---------------- montages: PROVEN BINDING image -> provenance.json -> row -> mesh -> bytes
for name, meta in sorted(prov.items()):
    img = HERE / "images" / name
    row_path = resolve_src(meta["row"])
    if not row_path.exists():
        abort("montage binds a missing row", f"images/{name} -> {meta['row']}")
    r = load_json(row_path, f"montage row for {name}")
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

# structural coverage: EVERY {path, sha256} pair recorded anywhere in the
# provenance schema must verify (walked generically — a hand-enumerated
# checklist is how the round-2 'recorded but unverified' gap happened).
def walk_hash_pairs(node):
    found = []
    if isinstance(node, dict):
        if "path" in node and "sha256" in node and node["sha256"]:
            found.append((node["path"], node["sha256"]))
        for v in node.values():
            found += walk_hash_pairs(v)
    elif isinstance(node, list):
        for v in node:
            found += walk_hash_pairs(v)
    return found


all_pairs = [(nm, p, s) for nm, meta in prov.items()
             for p, s in walk_hash_pairs(meta.get("panels", {}))]
bad_pairs = [(nm, p) for nm, p, s in all_pairs
             if not (resolve_src(p).exists() and sha256(resolve_src(p)) == s)]
check(f"all recorded path/sha256 pairs verify ({len(all_pairs)} recorded, floor 16)",
      not bad_pairs and len(all_pairs) >= 16, str(bad_pairs[:3]))
check("montage set is the 6 published cases", len(prov) == 6, str(len(prov)))
_a = prov["wheel_t2.png"]["row_sha256"]
_b = prov["003_front_grille_multiview_t1.png"]["row_sha256"]
check("binding probe: cross-montage row hashes differ (swap would fail)", _a != _b)

# planted-error probe inside the gate itself
saved = results[:]
results.clear()
check("planted-error probe (must FAIL and prove the gate is live)", 1 == 2)
self_test_failed = any(not ok for _, ok, _ in results)
results[:] = saved
check("planted-error probe actually failed", self_test_failed)

# ============================================================ report
fails = [n for n, ok, _ in results if not ok]
try:
    rev = subprocess.run(["git", "rev-parse", "HEAD"], cwd=REPO,
                         capture_output=True, text=True).stdout.strip() or "unknown"
except Exception:
    rev = "unknown"
report = {
    "ran_at": datetime.now().isoformat(timespec="seconds"),
    "environment": {"checkout": str(HERE), "git_rev": rev,
                    "python": sys.version.split()[0], "platform": platform.platform(),
                    "host": socket.gethostname()},
    "summary": {"checks": len(results), "passed": len(results) - len(fails), "failed": len(fails)},
    "results": [{"check": n, "ok": ok, "detail": d} for n, ok, d in results],
}
out = HERE / "audit-result.json"
tmp = out.with_name("audit-result.json.tmp")
tmp.write_text(json.dumps(report, indent=1) + "\n")
os.replace(tmp, out)  # atomic: an interrupted audit never replaces the last complete report

for n, ok, d in results:
    print(("PASS" if ok else "FAIL"), n, d)
print(f"{len(results) - len(fails)}/{len(results)} PASS -> audit-result.json")
sys.exit(1 if fails else 0)
