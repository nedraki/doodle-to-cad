"""Issue #61 containment: the usd_brep 1.0.0 tessellation crash must surface as
a structured kernel_unavailable failure with backend-switch advice, while every
other worker failure keeps its existing code. Planted-error fake workers prove
the classifier fires only on the real signature."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys

import pytest

from doodle_to_cad.build_contract import (
    BuildInput, KERNEL_CRASH_ADVICE, KERNEL_CRASH_SIGNATURE, REPRODUCER_SCRIPT,
    classify_kernel_crash, reproducer_hash)
from doodle_to_cad.brep import build_brep, worker_available

REPO = Path(__file__).resolve().parents[1]
FIXTURE = REPO / "scripts" / "fixtures" / "omni_solid_minimal.recipe.json"

SIMPLE_RECIPE = {"version": 1, "units": "mm", "parameters": {}, "operations": [
    {"id": "block", "kind": "box", "origin": [0, 0, 0], "size": [10, 10, 10]}], "output": "block"}

# A worker that crashes the way the shipped usd_brep 1.0.0 wheel does today.
CRASH_WORKER = '''
import json, sys
from pathlib import Path
staging = Path(sys.argv[2])
print("Traceback (most recent call last):\\nModuleNotFoundError: No module named '_omni_solid'", file=sys.stderr)
(staging / "construction-error.json").write_text(json.dumps(
    {"code": "build_failed", "message": "No module named '_omni_solid'"}))
sys.exit(1)
'''

# Same crash, but the worker died before writing construction-error.json.
CRASH_WITHOUT_ERROR_FILE_WORKER = '''
import sys
print("Traceback (most recent call last):\\nModuleNotFoundError: No module named '_omni_solid'", file=sys.stderr)
sys.exit(1)
'''

# An unrelated crash must keep the generic code.
UNRELATED_CRASH_WORKER = '''
import json, sys
from pathlib import Path
staging = Path(sys.argv[2])
(staging / "construction-error.json").write_text(json.dumps(
    {"code": "build_failed", "message": "RuntimeError: kernel exploded"}))
sys.exit(1)
'''

# A generic ModuleNotFoundError is NOT the shipped defect signature.
UNRELATED_IMPORT_WORKER = '''
import json, sys
from pathlib import Path
staging = Path(sys.argv[2])
(staging / "construction-error.json").write_text(json.dumps(
    {"code": "build_failed", "message": "No module named 'numpy'"}))
sys.exit(1)
'''

# A worker that already classifies its own crash (the shipped worker path).
ALREADY_CLASSIFIED_WORKER = '''
import json, sys
from pathlib import Path
staging = Path(sys.argv[2])
(staging / "construction-error.json").write_text(json.dumps(
    {"code": "kernel_unavailable",
     "message": "usd_brep 1.0.0 kernel crash during tessellation: {sig}. Retry with the OpenSCAD backend."}
    .replace("{sig}", "No module named '_omni_solid'"}))
sys.exit(1)
'''

# A fake worker that succeeds: watertight STL + USD + diagnostics, exit 0.
SUCCESS_WORKER = '''
import json, sys
from pathlib import Path
import trimesh
staging = Path(sys.argv[2])
trimesh.creation.box(extents=(10, 10, 10)).export(str(staging / "model.stl"))
(staging / "model.usda").write_text("#usda 1.0\\n")
(staging / "diagnostics.json").write_text(json.dumps({"backend": "usd-brep"}))
print("fake worker ok")
'''


def run_worker(tmp_path, monkeypatch, script_body):
    worker = tmp_path / "fake_worker.py"
    worker.write_text(script_body)
    source = tmp_path / "model.recipe.json"
    source.write_text(json.dumps(SIMPLE_RECIPE))
    monkeypatch.setattr("doodle_to_cad.brep.WORKER", worker)
    monkeypatch.setattr("doodle_to_cad.brep.worker_python", lambda: str(sys.executable))
    return build_brep(BuildInput("usd-brep", source, tmp_path / "out", render=False))


def error_diagnostic(result):
    errors = [d for d in result.diagnostics if d.severity == "error"]
    assert len(errors) == 1, [vars(d) for d in result.diagnostics]
    return errors[0]


# --- classifier unit behaviour -------------------------------------------------

def test_classifier_fires_only_on_the_real_signature():
    hit = classify_kernel_crash("BRep build failed: No module named '_omni_solid'")
    assert hit is not None and hit[0] == "kernel_unavailable"
    assert KERNEL_CRASH_ADVICE in hit[1]
    assert REPRODUCER_SCRIPT in hit[1]
    assert reproducer_hash() in hit[1]
    for unrelated in ["No module named 'numpy'", "No module named 'usd_brep'",
                      "kernel produced an invalid geometry", "", "RuntimeError: exploded"]:
        assert classify_kernel_crash(unrelated) is None, unrelated


def test_second_kernel_signature_maps_without_reproducer_claim():
    code, advice = classify_kernel_crash("wheel_s0: kernel produced an invalid solid")
    assert code == "kernel_unavailable"
    assert KERNEL_CRASH_ADVICE in advice
    assert "Minimal reproducer" not in advice  # no reproducer exists for this one yet


def test_second_signature_requires_exact_message():
    assert classify_kernel_crash("kernel produced an invalid geometry") is None
    assert classify_kernel_crash("invalid solid") is None
    assert classify_kernel_crash("invalid solid produced by kernel") is None


def test_reproducer_hash_matches_canonical_fixture():
    assert reproducer_hash() == hashlib.sha256(FIXTURE.read_bytes()).hexdigest()


# --- planted-error fake workers ------------------------------------------------

def test_planted_kernel_crash_becomes_kernel_unavailable(tmp_path, monkeypatch):
    result = run_worker(tmp_path, monkeypatch, CRASH_WORKER)
    assert not result.ok and result.stl is None
    diagnostic = error_diagnostic(result)
    assert diagnostic.code == "kernel_unavailable"
    assert "Retry with the OpenSCAD backend." in diagnostic.message
    assert reproducer_hash() in diagnostic.message
    assert KERNEL_CRASH_SIGNATURE in diagnostic.message


def test_kernel_crash_contained_even_without_construction_error_file(tmp_path, monkeypatch):
    result = run_worker(tmp_path, monkeypatch, CRASH_WITHOUT_ERROR_FILE_WORKER)
    diagnostic = error_diagnostic(result)
    assert diagnostic.code == "kernel_unavailable"
    assert "Retry with the OpenSCAD backend." in diagnostic.message


def test_unrelated_crash_keeps_generic_code(tmp_path, monkeypatch):
    result = run_worker(tmp_path, monkeypatch, UNRELATED_CRASH_WORKER)
    diagnostic = error_diagnostic(result)
    assert diagnostic.code == "build_failed"
    assert "kernel_unavailable" != diagnostic.code
    assert "OpenSCAD" not in diagnostic.message


def test_unrelated_module_not_found_stays_generic(tmp_path, monkeypatch):
    result = run_worker(tmp_path, monkeypatch, UNRELATED_IMPORT_WORKER)
    assert error_diagnostic(result).code == "build_failed"


def test_already_classified_worker_passes_through(tmp_path, monkeypatch):
    result = run_worker(tmp_path, monkeypatch, ALREADY_CLASSIFIED_WORKER)
    diagnostic = error_diagnostic(result)
    assert diagnostic.code == "kernel_unavailable"
    assert diagnostic.message.startswith("usd_brep 1.0.0 kernel crash")


def test_fake_success_worker_is_not_misclassified(tmp_path, monkeypatch):
    result = run_worker(tmp_path, monkeypatch, SUCCESS_WORKER)
    assert result.ok, [vars(d) for d in result.diagnostics]
    assert result.stl is not None and result.stl.exists()
    assert not any(d.code == "kernel_unavailable" for d in result.diagnostics)


# --- the real worker end to end -------------------------------------------------

@pytest.mark.skipif(not worker_available(), reason="Isolated BRep worker not configured")
def test_real_worker_classifies_the_canonical_crash(tmp_path):
    source = tmp_path / "model.recipe.json"
    source.write_text(FIXTURE.read_text())
    staging = tmp_path / "staging"
    staging.mkdir()
    from doodle_to_cad.brep import WORKER, worker_python
    proc = subprocess.run([worker_python(), str(WORKER), str(source), str(staging)],
                          capture_output=True, text=True, timeout=300)
    assert proc.returncode == 1
    failure = json.loads((staging / "construction-error.json").read_text())
    assert failure["code"] == "kernel_unavailable"
    assert "Retry with the OpenSCAD backend." in failure["message"]
    assert hashlib.sha256(FIXTURE.read_bytes()).hexdigest() in failure["message"]


@pytest.mark.skipif(not worker_available(), reason="Isolated BRep worker not configured")
def test_real_worker_still_builds_simple_boxes(tmp_path):
    from doodle_to_cad.brep import build_recipe
    built = build_recipe(tmp_path, json.loads(json.dumps(SIMPLE_RECIPE)))
    assert built["ok"] and built["stl"]
