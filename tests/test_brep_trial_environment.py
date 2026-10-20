"""Gate for issue #85: the trial harness must actually write the environment
fingerprint the frozen plan declares (evidence_layout: 'environment.json
(git rev, python versions, usd-brep version, model, dates) written at trial
end'). Declared-but-never-written evidence is how the #34 run lost its
per-trial provenance.

These tests pin the choke point: _finish_row is the ONLY sanctioned row
write, and it always leaves an environment.json next to row.json — even
when collection of one field fails (the failure lands in _collect_error;
the file is never silently skipped).
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HARNESS = ROOT / "scripts" / "evaluate_brep.py"

sys.path.insert(0, str(ROOT / "scripts"))
import evaluate_brep  # noqa: E402


def test_no_row_write_bypasses_the_choke_point():
    """Every persisted row must carry its environment record: no code path
    may write row.json directly (the exact regression #85 files)."""
    source = HARNESS.read_text()
    writes = re.findall(r'\(cell\s*/\s*"row\.json"\)\.write_text', source)
    assert len(writes) == 1, (
        f"row.json written directly {len(writes)} times — all writes must go "
        f"through _finish_row (issue #85)")
    # and that one is inside _finish_row itself
    body = source.split("def _finish_row", 1)[1].split("\ndef ", 1)[0]
    assert '(cell / "row.json").write_text' in body


def test_finish_row_writes_environment_with_plan_declared_fields(tmp_path, monkeypatch):
    monkeypatch.setattr(evaluate_brep, "_ENV_STATIC", None)
    monkeypatch.setattr(evaluate_brep, "_SERVER_MODEL", "test/model-FP4")
    row = {"drawing": "wheel", "backend": "usd-brep", "trial": 1,
           "submitted_at": "2026-10-20T00:00:00+00:00",
           "finished_at": "2026-10-20T00:05:00+00:00"}
    evaluate_brep._finish_row(tmp_path, row)

    assert (tmp_path / "row.json").exists()
    env_path = tmp_path / "environment.json"
    assert env_path.exists(), "plan declares environment.json at trial end"
    env = json.loads(env_path.read_text())
    # the fields TRIAL-PLAN evidence_layout names: git rev, python versions,
    # usd-brep version, model, dates
    assert env["tested_commit"], "git rev must be recorded"
    assert env["python"], "python version must be recorded"
    assert env["server_model"] == "test/model-FP4"
    assert env["trial"] == "wheel/usd-brep/t1"
    assert env["trial_submitted_at"] and env["trial_finished_at"] and env["written_at"]


def test_environment_written_even_when_collection_partially_fails(tmp_path, monkeypatch):
    """A broken collector must degrade to _collect_error, never a missing
    file — a declared artifact that vanishes on error is the #85 bug class."""
    monkeypatch.setattr(evaluate_brep, "_ENV_STATIC", None)
    monkeypatch.setattr(evaluate_brep, "_SERVER_MODEL", None)
    monkeypatch.setattr("subprocess.check_output",
                        lambda *a, **k: (_ for _ in ()).throw(OSError("no git here")))
    row = {"drawing": "wheel", "backend": "openscad", "trial": 2}
    evaluate_brep._finish_row(tmp_path, row)
    env = json.loads((tmp_path / "environment.json").read_text())
    assert env.get("_collect_error"), "collection failures must be recorded"
    assert (tmp_path / "row.json").exists()
    assert "environment_write_error" not in row


def test_resume_path_does_not_touch_existing_rows(tmp_path, monkeypatch):
    """Resumability stays intact: an existing row is returned untouched —
    no environment rewrite of historical trials (they stay byte-sealed)."""
    cell = tmp_path / "wheel" / "usd-brep" / "trial-01"
    cell.mkdir(parents=True)
    before = json.dumps({"drawing": "wheel", "backend": "usd-brep", "trial": 1})
    (cell / "row.json").write_text(before)
    # The resume guard runs before any _finish_row call in _run_trial:
    src = HARNESS.read_text()
    guard = 'if (cell / "row.json").exists():'
    assert guard in src and src.index(guard) < src.index("_finish_row(cell, row)\n            return row")
