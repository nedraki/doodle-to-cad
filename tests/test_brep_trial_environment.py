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


def test_copy_evidence_retains_gate_rejection_transcripts(tmp_path):
    """#95 follow-up: a gate-rejected construction plan never produces
    construction-plan.json — the raw model transcript written by _json_call
    is the only witness of WHY the gate fired (2 of 9 bench-revolve rows were
    undiagnosable for exactly this reason). _copy_evidence must carry every
    construction-plan* transcript, base round and clarification rounds alike,
    and must never overwrite already-frozen evidence."""
    import pytest
    run = tmp_path / "run"
    run.mkdir()
    cell = tmp_path / "cell"
    cell.mkdir()
    (run / "construction-plan.raw.txt").write_text('{"clarification":{"kind":"radius"}}')
    (run / "construction-plan-answer-1.raw.txt").write_text('{"features":[]}')
    (run / "construction-plan-request.json").write_text('{"controls":{}}')  # not a raw transcript
    (run / "secret-ish-other-raw.txt").write_text("must not be copied")
    (run / "generation.json").write_text("{}")

    evaluate_brep._copy_evidence(run, cell)

    assert json.loads((cell / "construction-plan.raw.txt").read_text())["clarification"]["kind"] == "radius"
    assert (cell / "construction-plan-answer-1.raw.txt").exists()
    assert (cell / "generation.json").exists()
    assert not (cell / "secret-ish-other-raw.txt").exists()
    assert not (cell / "construction-plan-request.json").exists()

    # Append-only: a second trial replaying into the same cell must not overwrite.
    (run / "construction-plan.raw.txt").write_text("clobber-attempt")
    with pytest.raises(RuntimeError, match="refusing to overwrite"):
        evaluate_brep._copy_evidence(run, cell)
    assert "radius" in (cell / "construction-plan.raw.txt").read_text()


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


def test_copy_evidence_retains_kernel_crash_forensics(tmp_path):
    """#89: when the worker kernel fails on a recipe, the cell must carry the
    per-attempt reproducer set: the triggering recipe (already since #59), the
    kernel failure payload (failure.json), the stage name captured at the
    crash (stage.txt, e.g. the op id 'union_2'), and the runner log. Without
    them the frozen cell holds only one top-level error.json from the LAST
    attempt and the kernel message that killed attempt 1 is lost
    (ATTRIBUTION: 'wheel usd t1: kernel non-manifold on spoke union_2')."""
    import pytest
    run = tmp_path / "run"
    a1 = run / "construction-attempts" / "1"
    a2 = run / "construction-attempts" / "2"
    a1.mkdir(parents=True)
    a2.mkdir(parents=True)
    (a1 / "recipe.json").write_text('{"version": 2, "operations": [{"id": "union_2"}]}')
    (a1 / "failure.json").write_text(json.dumps(
        {"code": "build_failed", "message": "kernel non-manifold on spoke union_2"}))
    (a1 / "stage.txt").write_text("union_2")
    (a1 / "runner.log").write_text("worker traceback line")
    (a2 / "recipe.json").write_text('{"version": 2, "operations": []}')
    (a2 / "failure.json").write_text(json.dumps(
        {"code": "build_failed", "message": "kernel non-manifold on spoke union_2"}))
    cell = tmp_path / "cell"
    cell.mkdir()

    evaluate_brep._copy_evidence(run, cell)

    failed = cell / "failed"
    assert json.loads((failed / "1.recipe.json").read_text())["operations"][0]["id"] == "union_2"
    assert json.loads((failed / "1.failure.json").read_text())["message"] \
        == "kernel non-manifold on spoke union_2"
    assert (failed / "1.stage.txt").read_text() == "union_2"
    assert (failed / "1.runner.log").read_text() == "worker traceback line"
    # attempt 2 has only a recipe; missing siblings must not block the copy
    assert json.loads((failed / "2.recipe.json").read_text()) == {"version": 2, "operations": []}
    assert not (failed / "2.stage.txt").exists()

    # Append-only: replaying into a frozen cell must not clobber the reproducer.
    (a1 / "recipe.json").write_text('{"version": 2, "operations": ["clobbered"]}')
    with pytest.raises(RuntimeError, match="refusing to overwrite"):
        evaluate_brep._copy_evidence(run, cell)
    assert json.loads((failed / "1.recipe.json").read_text())["operations"][0]["id"] == "union_2"


def test_run_recipe_job_carries_attempt_forensics_to_frozen_cell(tmp_path, monkeypatch):
    """End-to-end #89 kernel half: a planted worker crash (writes stage.txt,
    writes error.json, exits 1) leaves recipe+failure+stage+runner.log in the
    retained run directory AND _copy_evidence reproduces all of them in the
    cell directory."""
    import asyncio
    import sys
    from doodle_to_cad import recipe_jobs
    real_spawn = asyncio.create_subprocess_exec
    fake = chr(10).join([
        "import sys, pathlib, json",
        "out = pathlib.Path(sys.argv[1])",
        "(out / 'stage.txt').write_text('union_2')",
        "(out / 'error.json').write_text(json.dumps(",
        "    {'message': 'kernel non-manifold on spoke union_2', 'code': 'build_failed'}))",
        "print('planted kernel traceback')",
        "sys.exit(1)",
    ])
    async def spawn(*args, **kwargs):
        if "doodle_to_cad.recipe_job_worker" in args:
            return await real_spawn(sys.executable, "-c", fake, args[-1], **kwargs)
        return await real_spawn(*args, **kwargs)
    monkeypatch.setattr(recipe_jobs.asyncio, "create_subprocess_exec", spawn)
    async def no_docker(_): pass
    monkeypatch.setattr(recipe_jobs, "_docker_cleanup", no_docker)

    output = tmp_path / "results"
    output.mkdir()
    job = {"job_id": "crash123cras", "status": "running", "result": None}
    async def prepare(out):
        (out / "generation.json").write_text("{}")
        return {"version": 2, "operations": [{"id": "union_2"}]}
    asyncio.run(recipe_jobs.run_recipe_job(job, {}, output, lambda *a: None, prepare=prepare))

    assert job["status"] == "error"
    assert job["error"]["message"] == "kernel non-manifold on spoke union_2"
    retained = output / job["job_id"] / "construction-attempts" / "1"
    assert json.loads((retained / "recipe.json").read_text())["operations"][0]["id"] == "union_2"
    assert json.loads((retained / "failure.json").read_text())["code"] == "build_failed"
    # The stage captured at the crash is the op id that killed the kernel.
    assert (retained / "stage.txt").read_text() == "union_2"
    assert "planted kernel traceback" in (retained / "runner.log").read_text()

    cell = tmp_path / "cell"
    cell.mkdir()
    evaluate_brep._copy_evidence(output / job["job_id"], cell)
    assert (cell / "failed" / "1.stage.txt").read_text() == "union_2"
    assert "union_2" in (cell / "failed" / "1.failure.json").read_text()
