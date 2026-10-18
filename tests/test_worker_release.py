"""Issue #33: release readiness of the BRep worker — health, limits, cancellation, crashes.

Every check here answers one release question with a runnable assertion:
can another person install the worker, does the app tell them what is wrong,
does a cancelled or crashed worker stay contained, and are the limits real?
"""
import json
import os
import sys
import threading
import time
from pathlib import Path

import pytest

from doodle_to_cad import brep
from doodle_to_cad.brep import build_brep, worker_health, register_cancellation, unregister_cancellation
from doodle_to_cad.build_contract import BuildInput, BuildError

ROOT = Path(__file__).resolve().parents[1]
BOOKEND = json.loads((ROOT / "benchmarks/brep-selection/bookend.json").read_text())
BOX = {"version": 1, "units": "mm", "parameters": {}, "output": "block",
       "operations": [{"id": "block", "kind": "box", "origin": [0, 0, 0], "size": [20, 20, 10]}]}
KERNEL = pytest.mark.skipif(not brep.worker_available(), reason="BRep worker not configured")


def _stage_recipe(tmp_path, recipe, name="model.recipe.json"):
    source = tmp_path / name
    source.write_text(json.dumps(recipe))
    return source


def _write_stub(path, body):
    path.write_text("#!/usr/bin/env python3\n" + body)
    path.chmod(0o755)
    return path


def test_worker_health_reports_actionable_message_for_wrong_interpreter(monkeypatch):
    # The product interpreter is 3.11 in CI; the worker requires 3.12.
    monkeypatch.setenv("DOODLE_BREP_PYTHON", sys.executable)
    monkeypatch.setattr(brep, "_HEALTH_CACHE", {})
    health = worker_health()
    assert health["available"] is False
    assert "Python 3.12" in health["reason"] and "uv venv" in health["reason"]


def test_worker_health_reports_actionable_message_when_missing(monkeypatch, tmp_path):
    monkeypatch.setenv("DOODLE_BREP_PYTHON", str(tmp_path / "no-such-python"))
    monkeypatch.setattr(brep, "_HEALTH_CACHE", {})
    health = worker_health()
    assert health["available"] is False
    assert "DOODLE_BREP_PYTHON" in health["reason"]


@KERNEL
def test_worker_health_available_with_pinned_dependencies():
    health = worker_health()
    assert health == {"available": True, "reason": None}


@KERNEL
def test_resource_limits_are_actually_applied_to_the_worker(tmp_path, monkeypatch):
    monkeypatch.setenv("DOODLE_BREP_MEMORY_LIMIT_MB", "8192")
    monkeypatch.setenv("DOODLE_BREP_CPU_LIMIT_S", "150")
    result = build_brep(BuildInput("usd-brep", _stage_recipe(tmp_path, BOOKEND), tmp_path / "run-limits", render=False))
    assert result.ok, result.log
    limits = result.backend_details["resource_limits"]
    assert limits["memory_bytes"] == 8192 * 1024 * 1024
    assert limits["cpu_seconds"] == 150
    assert limits["file_size_bytes"] == 512 * 1024 * 1024


@KERNEL
def test_cancellation_kills_the_worker_process(tmp_path, monkeypatch):
    stub = _write_stub(tmp_path / "slow_worker.py", """
import sys, time
from pathlib import Path
(Path(sys.argv[2]) / "worker.pid").write_text(str(__import__("os").getpid()))
time.sleep(60)
""")
    monkeypatch.setattr(brep, "WORKER", stub)
    out = tmp_path / "cancel-job"
    event = register_cancellation("cancel-job")
    outcome = {}

    def run():
        outcome["result"] = build_brep(BuildInput("usd-brep", _stage_recipe(tmp_path, BOX, "box.json"), out, render=False))

    thread = threading.Thread(target=run)
    thread.start()
    stub = tmp_path / ".brep-"  # staging dir prefix; the pid file lives inside it
    pid = None
    deadline = time.monotonic() + 20
    while time.monotonic() < deadline and pid is None:
        for candidate in out.glob(".brep-*/worker.pid"):
            pid = int(candidate.read_text())
        time.sleep(0.1)
    assert pid is not None, "stub worker never started"
    assert Path(f"/proc/{pid}").exists(), "stub worker is not running"
    event.set()
    thread.join(timeout=30)
    assert not thread.is_alive(), "build_brep did not return after cancellation"
    codes = [d.code for d in outcome["result"].diagnostics]
    assert "cancelled" in codes, codes
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline and Path(f"/proc/{pid}").exists():
        time.sleep(0.1)
    assert not Path(f"/proc/{pid}").exists(), "worker process survived cancellation"
    # Cancellation is contained: no staging directories remain under the run dir.
    assert not list(out.glob(".brep-*")), "staging directories leaked after cancellation"
    brep._CANCEL_EVENTS.pop("cancel-job", None)


@KERNEL
def test_worker_crash_produces_diagnostic_and_keeps_previous_result(tmp_path, monkeypatch):
    stub = _write_stub(tmp_path / "crash_worker.py", """
import sys
print('simulated crash', file=sys.stderr)
sys.exit(3)
""")
    # First build with the real worker publishes a result...
    good = build_brep(BuildInput("usd-brep", _stage_recipe(tmp_path, BOOKEND, "book.json"), tmp_path / "job-x", render=False))
    assert good.ok, good.log
    published = sorted(p.name for p in (tmp_path / "job-x").iterdir())
    # ...then the crashing worker must fail cleanly without touching it.
    monkeypatch.setattr(brep, "WORKER", stub)
    crashed = build_brep(BuildInput("usd-brep", _stage_recipe(tmp_path, BOX, "box.json"), tmp_path / "job-x", render=False))
    assert not crashed.ok
    assert any(d.code == "build_failed" for d in crashed.diagnostics)
    assert not (tmp_path / "job-x" / "model.stl").exists(), "crashed worker must not publish an STL"
    assert published == sorted(p.name for p in (tmp_path / "job-x").iterdir()), "crash changed the run directory"


@KERNEL
def test_build_recipe_raises_actionable_build_error(tmp_path, monkeypatch):
    stub = _write_stub(tmp_path / "err_worker.py", """
import json, sys
from pathlib import Path
(Path(sys.argv[2]) / "construction-error.json").write_text(json.dumps(
    {"code": "unsupported_construction", "message": "stub refuses this recipe"}))
sys.exit(1)
""")
    monkeypatch.setattr(brep, "WORKER", stub)
    with pytest.raises(BuildError) as raised:
        brep.build_recipe(tmp_path / "job-y", BOX)
    assert raised.value.code == "unsupported_construction"
    assert "stub refuses" in str(raised.value)


@KERNEL
def test_health_endpoint_includes_worker_state(tmp_path, monkeypatch):
    monkeypatch.setattr(brep, "_HEALTH_CACHE", {})
    from fastapi.testclient import TestClient
    from doodle_to_cad import app as app_module
    with TestClient(app_module.app) as client_http:
        payload = client_http.get("/api/health").json()
    assert payload["brep_worker"]["available"] is True
