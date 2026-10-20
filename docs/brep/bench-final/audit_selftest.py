"""Adversarial self-test for bench-final/audit.py (issue #79 hardening).

Every check class in audit.py must be shown to FIRE on a planted defect.
For each scenario we copy the bench-final tree to a scratch dir, mutate ONE
artifact, run audit.py against the copy, and require (a) non-zero exit and
(b) the named failure. Two tamper depths are covered:

  * RAW  — bytes edited without touching MANIFEST.json: the manifest gate
    must abort naming the artifact path (the row/mesh/input/reference edits
    a naive audit would silently re-read).
  * RE-SEALED — attacker also regenerated the manifest (they control that
    file too): the SEMANTIC checks (montage hash chain, historical counts,
    archived-STL equality, coverage, index consistency, README comparison)
    must still catch it. Without re-seal coverage these checks would be
    unreachable and the manifest check would be the only live wire.

A defect nobody can trigger is decoration. Quick set (raw + cheap semantcs)
runs in pytest; full set including re-seal scenarios: BENCH_SELFTEST_SET=full.
Clone gate source/ref override: BENCH_AUDIT_SOURCE, BENCH_AUDIT_REF;
BENCH_SELFTEST_SKIP_CLONE=1 to skip the clone leg.

Run from repo root:
  python3 docs/brep/bench-final/audit_selftest.py
"""
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
PY = sys.executable
DEFAULT_SOURCE = "https://github.com/nedraki/doodle-to-cad"
DEFAULT_REF = "brep-integration"


def reseal(copy):
    subprocess.run([PY, str(copy / "make_manifest.py")], check=True,
                   capture_output=True)


def make_copy():
    """Disposable FAKE repo: the copy must sit at <fake-repo>/docs/brep/bench-final
    with a real benchmarks/ tree beside it, so repo-relative recorded pointers
    resolve INSIDE the copy — an audit copy that escapes its repo would test
    nothing (the round-2 absolute-path bug in miniature)."""
    tmp = Path(tempfile.mkdtemp(prefix="bench-selftest-"))
    fake_repo = tmp / "repo"
    copy = fake_repo / "docs" / "brep" / "bench-final"
    copy.parent.mkdir(parents=True)
    shutil.copytree(HERE, copy)
    bench_src = HERE.parents[2] / "benchmarks"
    if bench_src.exists():
        shutil.copytree(bench_src, fake_repo / "benchmarks")
    return tmp, copy


# ---------------- RAW tamper (manifest gate must abort with the path)
def sc_edit_row_field(copy):
    f = copy / "runs/004_flat_mounting_plate/openscad/trial-01/row.json"
    r = json.loads(f.read_text()); r["wall_seconds"] = 1.0
    f.write_text(json.dumps(r))
    return "runs/004_flat_mounting_plate/openscad/trial-01/row.json"


def sc_edit_mesh_bytes(copy):
    (copy / "runs/004_flat_mounting_plate/openscad/trial-01/stl/model.stl").write_bytes(b"solid x\n")
    return "model.stl"


def sc_edit_reference_stl(copy):
    (copy / "references/wheel-reference.stl").write_bytes(b"solid evil\n")
    return "references/wheel-reference.stl"


def sc_edit_input_nonmontage(copy):
    (copy / "runs/004_flat_mounting_plate/openscad/trial-01/input.png").write_bytes(b"not a png")
    return "input.png"


def sc_delete_cell_raw(copy):
    shutil.rmtree(copy / "runs/004_flat_mounting_plate/openscad/trial-02")
    return "sealed file missing"


def sc_add_unsealed_file(copy):
    (copy / "runs/004_flat_mounting_plate/openscad/trial-01/sneaky.json").write_text("{}")
    return "unsealed artifact"


def sc_delete_manifest(copy):
    (copy / "MANIFEST.json").unlink()
    return "evidence manifest"


def sc_corrupt_row(copy):
    """Corrupt row.json AND re-seal: the cell scan itself must abort naming
    the cell (a manifest-only defense would not prove rows are parsed)."""
    (copy / "runs/007_angle_bracket_holes/usd-brep/trial-01/row.json").write_text("{ not json")
    reseal(copy)
    return "corrupt JSON"


# ---------------- RE-SEALED tamper (semantic checks must catch)
def sc_image_swap(copy):
    """Codex's own reproduction: wheel montage replaced by the vase montage."""
    img = copy / "images"
    shutil.copyfile(img / "002_greek_vase_silhouette_t1.png", img / "wheel_t2.png")
    reseal(copy)
    return "montage wheel_t2.png: image/row/mesh/panel hash chain"


def edit_row(copy, cell_rel, mutate):
    """Edit a row.json AND its index.jsonl twin consistently, so the
    index-consistency abort gate is satisfied and the scenario actually
    reaches the semantic check it claims to prove (a scenario that aborts
    earlier is testing the wrong wire)."""
    f = copy / cell_rel / "row.json"
    r = json.loads(f.read_text())
    mutate(r)
    f.write_text(json.dumps(r))
    idf = copy / "runs/index.jsonl"
    lines = idf.read_text().splitlines()
    out = []
    for ln in lines:
        e = json.loads(ln)
        if (e["drawing"], e["backend"], e["trial"]) == (r["drawing"], r["backend"], r["trial"]):
            e = r
        out.append(json.dumps(e))
    idf.write_text("\n".join(out) + "\n")


def sc_acceptance_flip(copy):
    """The single plan-accepted usd row silently downgraded to failed."""
    edit_row(copy, "runs/006_stepped_knob/usd-brep/trial-01",
             lambda r: r["product"].__setitem__("status", "failed"))
    reseal(copy)
    return "HISTORICAL frozen-plan counts: usd-brep 31/46"


def sc_fake_reference(copy):
    """907eed7 chamfer error class: a no_ground_truth row reclassified as GT."""
    f = copy / "references/reference-measurements.json"
    refs = json.loads(f.read_text())
    refs["bevelled_block"]["kind"] = "ground_truth_stl"
    f.write_text(json.dumps(refs))
    reseal(copy)
    return "bevelled_block: 2/2 automatic overall_pass AND no GT reference"


def sc_provenance_rebind(copy):
    """provenance.json re-pointed at another row (image kept, binding moved)."""
    pf = copy / "images/provenance.json"
    prov = json.loads(pf.read_text())
    other = prov["003_front_grille_multiview_t1.png"]
    prov["101_bltouch_bracket_t1.png"]["row_sha256"] = other["row_sha256"]
    pf.write_text(json.dumps(prov))
    reseal(copy)
    return "montage 101_bltouch_bracket_t1.png: image/row/mesh/panel hash chain"


def sc_empty_reference(copy):
    """Delete a reference so dims/topo/vol pass loses its claimed members."""
    f = copy / "references/reference-measurements.json"
    refs = json.loads(f.read_text())
    refs["solid_transition"] = {"kind": "no_ground_truth", "note": "planted"}
    f.write_text(json.dumps(refs))
    for t in (1, 2):
        edit_row(copy, f"runs/solid_transition/openscad/trial-0{t}",
                 lambda r: r["checks"].update(
                     {"extents_pass": None, "genus_pass": None, "volume_pass": None}))
    reseal(copy)
    return "HISTORICAL frozen-plan counts: openscad 44/46"


def sc_sophisticated_build_hash(copy):
    """Row claims a mesh sha the archived bytes never had, manifest re-sealed:
    the archived-STL-vs-row equality must fire, not just the manifest."""
    edit_row(copy, "runs/004_flat_mounting_plate/openscad/trial-01",
             lambda r: r["build"].__setitem__("sha256", "0" * 64))
    reseal(copy)
    return "archived STLs match row build.sha256"


def sc_readme_drift(copy):
    """README headline number edited without regenerating the table."""
    f = copy / "README.md"
    t = f.read_text().replace("22/46 (48%)", "23/46 (50%)")
    assert t != f.read_text()
    f.write_text(t)
    return "README headline tables equal the metrics-recomputed tables"


def sc_excluded_no_reason(copy):
    """A row marked excluded without reason+replaced_by must fail the gate,
    not quietly vanish from the metrics."""
    edit_row(copy, "runs/004_flat_mounting_plate/openscad/trial-02",
             lambda r: r.__setitem__("excluded", {"reason": "because"}))  # no replaced_by
    reseal(copy)
    return "excluded/superseded rows"


def sc_montage_input_corrupt(copy):
    """Replace the wheel montage row's input drawing (panel hash must catch
    even after the manifest is honestly re-sealed)."""
    (copy / "runs/wheel/usd-brep/trial-02/input.png").write_bytes(b"not a png")
    reseal(copy)
    return "montage wheel_t2.png: image/row/mesh/panel hash chain"


def sc_index_desync(copy):
    """row.json and runs/index.jsonl disagree about the same trial."""
    rf = copy / "runs/004_flat_mounting_plate/openscad/trial-01/row.json"
    r = json.loads(rf.read_text())
    r["wall_seconds"] = 1.0
    rf.write_text(json.dumps(r))
    idf = copy / "runs/index.jsonl"
    lines = idf.read_text().splitlines()
    out = []
    for ln in lines:
        e = json.loads(ln)
        if (e["drawing"], e["backend"], e["trial"]) == ("004_flat_mounting_plate", "openscad", 1):
            e["wall_seconds"] = 2.0
        out.append(json.dumps(e))
    idf.write_text("\n".join(out) + "\n")
    reseal(copy)
    return "does not correspond 1:1"


def sc_remove_cell(copy):
    """Cell deleted and manifest re-sealed: coverage must detect the hole."""
    shutil.rmtree(copy / "runs/004_flat_mounting_plate/openscad/trial-02")
    reseal(copy)
    return "cell coverage does not match the frozen plan"


def sc_duplicate_cell(copy):
    """Cell duplicated (trial-03) with a consistent identity + re-seal:
    coverage must reject the unexpected trial."""
    src = copy / "runs/004_flat_mounting_plate/openscad/trial-01"
    dst = copy / "runs/004_flat_mounting_plate/openscad/trial-03"
    shutil.copytree(src, dst)
    f = dst / "row.json"
    r = json.loads(f.read_text()); r["trial"] = 3
    f.write_text(json.dumps(r))
    reseal(copy)
    return "cell coverage does not match the frozen plan"


# ---------------- external-review regression probes (findings 1-5)
def sc_falsified_results_json(copy):
    """Review #1a: published results.json numerator inflated. The audit
    re-derives the COMPLETE report and byte-compares — not just the blocks."""
    f = copy / "results.json"
    d = json.loads(f.read_text())
    d["summary"]["usd-brep"]["metrics"]["automatic_checks_unverified"]["numerator"] = 31
    f.write_text(json.dumps(d, indent=2) + "\n")
    return "results.json is byte-identical"


def sc_deleted_results_json(copy):
    """Review #1b: results.json deleted entirely must not pass."""
    (copy / "results.json").unlink()
    return "file missing"


def sc_falsified_results_md(copy):
    """Review #1c: a supplementary Markdown count (42 -> 999) edited."""
    f = copy / "RESULTS.md"
    t = f.read_text().replace("build_success 42", "build_success 999")
    assert t != f.read_text(), "probe lost its target string"
    f.write_text(t)
    return "RESULTS.md is byte-identical"


def sc_forge_execution_log(copy):
    """Review #4: the trial log is now SEALED — replacing it with a forged
    one containing only the expected server-model line must abort."""
    (copy / "logs-trials.log").write_text(
        "server model: local-inference-lab/Qwen3.8-Flash-Next-NVFP4\n")
    return "logs-trials.log"


def sc_index_duplicate(copy):
    """Review #5: an index record duplicated + manifest honestly re-sealed.
    The multiset gate must abort — collapsing to a dict hides this."""
    idf = copy / "runs/index.jsonl"
    lines = idf.read_text().splitlines()
    lines.append(lines[0])
    idf.write_text("\n".join(lines) + "\n")
    reseal(copy)
    return "does not correspond 1:1"


def sc_aggregate_missing_cell(copy):
    """Review #2: with the manifest re-sealed (so the evidence gate passes),
    aggregate must still ABORT on a missing expected cell — never publish a
    shrunken denominator. Runner: aggregate.py, not audit.py."""
    (copy / "runs/004_flat_mounting_plate/openscad/trial-02/row.json").unlink()
    reseal(copy)
    return "expected trial cell missing"


def _exclude_row(copy, cell_rel, replaced_by):
    edit_row(copy, cell_rel, lambda r: r.__setitem__(
        "excluded", {"reason": "duplicate submission (planted)",
                     "replaced_by": replaced_by}))
    reseal(copy)
    agg = subprocess.run([PY, str(copy / "aggregate.py")], capture_output=True,
                         text=True, cwd=str(HERE.parents[2]))
    assert agg.returncode == 0, f"aggregate refused a valid exclusion: {agg.stdout[-300:]}"


def sc_superseded_plain_form(copy):
    """Review #3 (form 'trial-01'): a VALID superseded reference must be
    accepted, not searched for as 'trial-trial-01'. Expectation: PASS."""
    _exclude_row(copy, "runs/004_flat_mounting_plate/openscad/trial-02", "trial-01")
    return "excluded/superseded rows are published"


def sc_superseded_bare_number(copy):
    """Review #3 (bare '02' form): must resolve to the existing trial-02
    directory instead of failing the old 'trial-' substring demand."""
    _exclude_row(copy, "runs/004_flat_mounting_plate/openscad/trial-01", "02")
    return "excluded/superseded rows are published"


SCENARIOS = [
    # (name, mutate, quick?)
    ("raw row edit (manifest must name the trial)", sc_edit_row_field, True),
    ("raw mesh byte edit", sc_edit_mesh_bytes, True),
    ("raw reference STL edit", sc_edit_reference_stl, True),
    ("raw non-montage input edit", sc_edit_input_nonmontage, True),
    ("raw cell deletion (sealed file missing)", sc_delete_cell_raw, True),
    ("raw unsealed extra file planted", sc_add_unsealed_file, True),
    ("manifest deleted", sc_delete_manifest, True),
    ("corrupt row.json (abort names path, never skips)", sc_corrupt_row, True),
    ("re-sealed image swap (montage chain)", sc_image_swap, True),
    ("re-sealed acceptance flip (historical counts)", sc_acceptance_flip, False),
    ("re-sealed fake GT reference (907eed7 class)", sc_fake_reference, False),
    ("re-sealed provenance re-bind", sc_provenance_rebind, False),
    ("re-sealed reference removal on GT-match rows", sc_empty_reference, False),
    ("re-sealed build.sha256 tamper (STL equality)", sc_sophisticated_build_hash, True),
    ("README number drifted without regeneration", sc_readme_drift, True),
    ("row excluded without reason+replacement", sc_excluded_no_reason, False),
    ("re-sealed montage input corruption", sc_montage_input_corrupt, False),
    ("index.jsonl vs row.json desync", sc_index_desync, False),
    ("re-sealed cell removal (coverage)", sc_remove_cell, True),
    ("re-sealed cell duplication (coverage)", sc_duplicate_cell, True),
    # external-review regression probes (findings 1-5 of the PR #84 review)
    ("falsified results.json numerator (full-report compare)", sc_falsified_results_json, True),
    ("deleted results.json (full-report compare)", sc_deleted_results_json, True),
    ("falsified RESULTS.md supplementary count", sc_falsified_results_md, True),
    ("forged execution log (now sealed)", sc_forge_execution_log, True),
    ("duplicated index record, re-sealed (multiset gate)", sc_index_duplicate, True),
    ("aggregate on missing cell (no shrunken denominator)", sc_aggregate_missing_cell, True),
    ("valid superseded 'trial-01' accepted (positive)", sc_superseded_plain_form, False, "expect"),
    ("valid superseded bare '02' accepted (positive)", sc_superseded_bare_number, False, "expect"),
]


def run_audit(copy):
    return subprocess.run([PY, str(copy / "audit.py")], capture_output=True,
                          text=True, cwd=str(HERE.parents[2]))


def main():
    import os
    quick = os.environ.get("BENCH_SELFTEST_SET", "full") == "quick"
    failures = 0
    selected = [s for s in SCENARIOS if not quick or s[2]]
    for entry in selected:
        name, plant, _, kind = (entry + ("audit",))[:4]
        tmp = None
        try:
            tmp, copy = make_copy()
            expected = plant(copy)
            if kind == "aggregate":
                proc = subprocess.run([PY, str(copy / "aggregate.py")], capture_output=True,
                                      text=True, cwd=str(HERE.parents[2]))
                out = proc.stdout + proc.stderr
                fired = any(expected in ln for ln in out.splitlines())
                ok = proc.returncode != 0 and fired
            elif kind == "expect":
                # positive scenario: the named check must PASS (not merely
                # 'nothing failed' — a check that vanishes also vanishes PASS)
                proc = run_audit(copy)
                out = proc.stdout + proc.stderr
                ok = ("AUDIT ABORT" not in out
                      and any(ln.startswith("PASS") and expected in ln
                              for ln in out.splitlines()))
                fired = ok
            else:
                proc = run_audit(copy)
                out = proc.stdout + proc.stderr
                fired = any(expected in ln for ln in out.splitlines())
                ok = proc.returncode != 0 and fired
            print(("CAUGHT  " if ok else "MISSED  ") + name,
                  "" if ok else f"(exit={proc.returncode}, expected '{expected}' "
                                f"{'in a PASS line' if kind == 'expect' else 'in output'})")
            failures += 0 if ok else 1
        finally:
            if tmp:
                shutil.rmtree(tmp, ignore_errors=True)

    # GREEN gate: an audit from a FRESH CLONE must pass standalone — 'green'
    # must be a property of the shipped artifacts, not of the author's tree.
    clone_failures = 0
    if os.environ.get("BENCH_SELFTEST_SKIP_CLONE") != "1":
        source = os.environ.get("BENCH_AUDIT_SOURCE", DEFAULT_SOURCE)
        ref = os.environ.get("BENCH_AUDIT_REF", DEFAULT_REF)
        clone = Path(tempfile.mkdtemp(prefix="bench-clone-")) / "repo"
        try:
            subprocess.run(["git", "clone", "-q", "--depth", "1", "-b", ref, source, str(clone)],
                           check=True)
            proc = run_audit(clone / "docs/brep/bench-final")
            green = proc.returncode == 0
            print(("GREEN   " if green else "NOT-GREEN") + f" fresh-clone audit passes standalone ({ref})")
            if not green:
                print((proc.stdout + proc.stderr)[-1200:])
            clone_failures = 0 if green else 1
        finally:
            shutil.rmtree(clone.parent, ignore_errors=True)

    total = len(selected) + (0 if clone_failures == 0 else 1) if os.environ.get("BENCH_SELFTEST_SKIP_CLONE") == "1" else len(selected) + 1
    print(f"{total - failures - clone_failures}/{total} gates green")
    sys.exit(1 if (failures or clone_failures) else 0)


if __name__ == "__main__":
    main()
