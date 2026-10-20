"""Executable claim gate for docs/brep/bench-final (issue #79).

pytest re-verifies the published benchmark report end-to-end:
  * audit.py passes (every headline number recomputes from metrics.py and
    matches README/RESULTS; every sealed hash verifies in THIS checkout)
  * the adversarial self-test (quick set) still catches planted defects
  * an audit from a fresh clone of this branch passes standalone

The full self-test (re-sealed tampers) runs with BENCH_SELFTEST_SET=full.
"""
import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
BENCH = REPO / "docs" / "brep" / "bench-final"


def _run(script, env=None):
    return subprocess.run([sys.executable, str(BENCH / script)],
                          capture_output=True, text=True, cwd=str(REPO),
                          env={**os.environ, **(env or {})})


def test_audit_passes_on_this_checkout():
    proc = _run("audit.py")
    assert proc.returncode == 0, proc.stdout[-3000:] + proc.stderr[-1500:]
    assert "PASS" in proc.stdout


def test_audit_result_json_published_with_environment():
    proc = _run("audit.py")
    assert proc.returncode == 0
    import json
    report = json.loads((BENCH / "audit-result.json").read_text())
    assert report["summary"]["failed"] == 0
    env = report["environment"]
    # environment fingerprint: which checkout + revision + python produced this
    assert env["git_rev"] and env["python"] and env["checkout"].endswith("bench-final")


def test_manifest_seal_is_up_to_date():
    sys.path.insert(0, str(BENCH))
    try:
        import make_manifest
        committed = (BENCH / "MANIFEST.json").read_text()
        import json
        sealed = make_manifest.build_manifest()["files"]
        on_disk = json.loads(committed)["files"]
        assert sealed == on_disk, "MANIFEST.json is stale — run make_manifest.py"
    finally:
        sys.path.remove(str(BENCH))


def test_selftest_catches_planted_defects():
    proc = _run("audit_selftest.py", env={"BENCH_SELFTEST_SET": "quick",
                                          "BENCH_SELFTEST_SKIP_CLONE": "1"})
    assert proc.returncode == 0, proc.stdout[-3000:] + proc.stderr[-1500:]


def test_fresh_clone_audit_is_green():
    branch = subprocess.run(["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=REPO,
                            capture_output=True, text=True).stdout.strip()
    if branch in ("", "HEAD"):
        pytest.skip("detached HEAD — clone gate runs against the pushed branch in CI")
    proc = _run("audit_selftest.py", env={"BENCH_SELFTEST_SET": "quick",
                                          "BENCH_AUDIT_SOURCE": str(REPO),
                                          "BENCH_AUDIT_REF": branch})
    # clone of the committed tip must audit green standalone
    assert proc.returncode == 0, proc.stdout[-3000:] + proc.stderr[-1500:]
    assert "GREEN" in proc.stdout
