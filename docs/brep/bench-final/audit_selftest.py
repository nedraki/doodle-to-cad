"""Adversarial self-test for bench-final/audit.py.

Every check class in audit.py must be shown to FIRE on a planted defect.
For each scenario we copy the bench-final tree to a scratch dir, mutate ONE
artifact in a way that a vacuous audit would miss, run audit.py against the
copy, and require (a) non-zero exit and (b) the named check to FAIL.

This is the structural answer to the 907eed7 review: a check nobody can
trigger is decoration. Run from repo root:
  PYTHONPATH=. .venv/bin/python docs/brep/bench-final/audit_selftest.py
"""
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
PY = sys.executable


def scenario_swap_images(copy):
    """Codex's own test: wheel montage replaced by the vase montage."""
    img = copy / "images"
    shutil.copyfile(img / "002_greek_vase_silhouette_t1.png", img / "wheel_t2.png")
    return "montage wheel_t2.png: image/row/mesh/panel hash chain"


def scenario_tamper_row_hash(copy):
    """Row claims a sha the archived STL bytes do not have."""
    f = copy / "runs" / "004_flat_mounting_plate" / "openscad" / "trial-01" / "row.json"
    r = json.loads(f.read_text())
    r["build"]["sha256"] = "0" * 64
    f.write_text(json.dumps(r))
    return "archived STLs match row build.sha256"


def scenario_flip_acceptance(copy):
    """The single plan-accepted row silently downgraded to failed."""
    f = copy / "runs" / "006_stepped_knob" / "usd-brep" / "trial-01" / "row.json"
    r = json.loads(f.read_text())
    r["product"]["status"] = "failed"
    r["job_status"] = "done"
    f.write_text(json.dumps(r))
    return "usd-brep: 31/46 done, plan-acceptance 1"


def scenario_fake_reference(copy):
    """A no_ground_truth row reclassified as a full reference (the chamfer
    error from 907eed7: 'overall_pass' without any actual ground truth)."""
    f = copy / "references" / "reference-measurements.json"
    refs = json.loads(f.read_text())
    refs["bevelled_block"]["kind"] = "ground_truth_stl"
    f.write_text(json.dumps(refs))
    return "bevelled_block: 2/2 automatic overall_pass AND no GT reference"


def scenario_provenance_rebind(copy):
    """provenance.json re-pointed at another row (image kept, binding moved)."""
    pf = copy / "images" / "provenance.json"
    prov = json.loads(pf.read_text())
    other = prov["003_front_grille_multiview_t1.png"]
    prov["101_bltouch_bracket_t1.png"]["row_sha256"] = other["row_sha256"]
    pf.write_text(json.dumps(prov))
    return "montage 101_bltouch_bracket_t1.png: image/row/mesh/panel hash chain"


def scenario_empty_reference(copy):
    """Delete a reference so extents/genus/volume become null on a row the
    README counts as a complete-GT match."""
    f = copy / "references" / "reference-measurements.json"
    refs = json.loads(f.read_text())
    refs["solid_transition"] = {"kind": "no_ground_truth", "note": "planted"}
    f.write_text(json.dumps(refs))
    # audit reads checks from rows, so also null the row checks the way a
    # no-reference run would have produced them
    for t in ("trial-01", "trial-02"):
        rf = copy / "runs" / "solid_transition" / "openscad" / t / "row.json"
        r = json.loads(rf.read_text())
        r["checks"].update({"extents_pass": None, "genus_pass": None, "volume_pass": None})
        rf.write_text(json.dumps(r))
    return "ref dims/topo/vol pass = 2x solid_transition"


def scenario_local_row_edit(copy):
    """Codex round-2 repro: edit the LOCAL wheel row. With absolute provenance
    paths the audit would follow out of this checkout and still pass."""
    f = copy / "runs" / "wheel" / "usd-brep" / "trial-02" / "row.json"
    r = json.loads(f.read_text())
    r["wall_seconds"] = 1.0
    f.write_text(json.dumps(r))
    return "montage wheel_t2.png: image/row/mesh/panel hash chain"


def scenario_local_input_corrupt(copy):
    """Round-2 finding: panel sources recorded but not verified. Replace the
    wheel input drawing with garbage; the panel hash must catch it."""
    (copy / "runs" / "wheel" / "usd-brep" / "trial-02" / "input.png").write_bytes(b"not a png")
    return "montage wheel_t2.png: image/row/mesh/panel hash chain"


SCENARIOS = [
    ("local row edit (Codex round-2 repro)", scenario_local_row_edit),
    ("local input-bytes corruption (panel hash)", scenario_local_input_corrupt),
    ("image swap (Codex reproduction)", scenario_swap_images),
    ("row hash tamper", scenario_tamper_row_hash),
    ("acceptance flip", scenario_flip_acceptance),
    ("fake GT reference (907eed7 chamfer error)", scenario_fake_reference),
    ("provenance re-bind", scenario_provenance_rebind),
    ("reference removal on GT-match rows", scenario_empty_reference),
]


def main():
    failures = 0
    for name, plant in SCENARIOS:
        tmp = Path(tempfile.mkdtemp(prefix="bench-selftest-"))
        try:
            copy = tmp / "bench-final"
            shutil.copytree(HERE, copy)
            expected_failing = plant(copy)
            proc = subprocess.run(
                [PY, str(copy / "audit.py")], capture_output=True, text=True,
                cwd=str(HERE.parents[2]))
            out = proc.stdout + proc.stderr
            fired = any(ln.startswith("FAIL") and expected_failing in ln for ln in out.splitlines())
            ok = proc.returncode != 0 and fired
            print(("CAUGHT  " if ok else "MISSED  ") + name,
                  "" if ok else f"(exit={proc.returncode}, expected FAIL '{expected_failing}')")
            failures += 0 if ok else 1
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    print(f"{len(SCENARIOS) - failures}/{len(SCENARIOS)} planted defects caught")
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
