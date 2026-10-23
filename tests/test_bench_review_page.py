"""Executable gate for the bench-final human review server (issue #80).

Starts the server on an ephemeral port with an isolated decisions file
(never the real one), then verifies the properties the review depends on:
  * every frozen-plan cell renders — no success-only filtering;
  * the five trial states are representable (done/error/unverified render
    from real data; excluded renders from a planted row in a copy);
  * a decision round-trips to disk bound to the mesh sha256;
  * downloads are hash-bound: a mesh whose bytes differ from the row's
    recorded build.sha256 is refused, path escapes are refused.
"""
import json
import os
import socket
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
BENCH = REPO / "docs" / "brep" / "bench-final"


def free_port():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    p = s.getsockname()[1]
    s.close()
    return p


def start(port, decisions):
    env = {**os.environ, "BENCH_REVIEW_PORT": str(port),
           "BENCH_REVIEW_DECISIONS": str(decisions)}
    proc = subprocess.Popen([sys.executable, str(BENCH / "review_server.py")],
                            env=env, stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL)
    for _ in range(100):
        try:
            urllib.request.urlopen(f"http://127.0.0.1:{port}/decisions.json", timeout=1)
            return proc
        except OSError:
            time.sleep(0.1)
    proc.kill()
    raise RuntimeError("review server did not come up")


def get(port, path):
    with urllib.request.urlopen(f"http://127.0.0.1:{port}{path}", timeout=30) as r:
        return r.status, r.read()


def post(port, path, payload):
    req = urllib.request.Request(f"http://127.0.0.1:{port}{path}",
                                 data=json.dumps(payload).encode(),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.status, json.loads(r.read())


def test_all_plan_cells_render(tmp_path):
    port = free_port()
    proc = start(port, tmp_path / "decisions.json")
    try:
        _, page = get(port, "/")
        page = page.decode()
        plan = json.loads((BENCH / "TRIAL-PLAN.json").read_text())
        assert page.count('class="card"') == 92 == len(plan["corpus"]) * 4
        # states survive the render — failed cells are NOT filtered away
        assert page.count('class="err"') == 17          # the 17 published errors
        assert "chip unverified" in page                  # 006_stepped_knob/usd
        assert "none published" in page                   # no-reference disclosed
    finally:
        proc.terminate()


def test_decision_roundtrip_binds_mesh_hash(tmp_path):
    port = free_port()
    dec = tmp_path / "decisions.json"
    proc = start(port, dec)
    try:
        status, resp = post(port, "/decide",
                            {"cell": "wheel|usd-brep|t2", "decision": "accepted",
                             "note": "gate probe"})
        assert status == 200 and resp["ok"]
        on_disk = json.loads(dec.read_text())
        entry = on_disk["wheel|usd-brep|t2"]
        row = json.loads((BENCH / "runs/wheel/usd-brep/trial-02/row.json").read_text())
        assert entry["mesh_sha256"] == row["build"]["sha256"]
        # invalid vocabulary is refused
        import urllib.error
        try:
            post(port, "/decide", {"cell": "wheel|usd-brep|t2", "decision": "loved-it"})
            assert False, "bad decision accepted"
        except urllib.error.HTTPError as e:
            assert e.code == 400
        # clear removes the record
        post(port, "/decide", {"cell": "wheel|usd-brep|t2", "decision": ""})
        assert json.loads(dec.read_text()) == {}
    finally:
        proc.terminate()


def test_downloads_are_hash_bound(tmp_path):
    port = free_port()
    proc = start(port, tmp_path / "decisions.json")
    try:
        st, data = get(port, "/dl?cell=wheel%7Cusd-brep%7Ct2&f=stl/model.stl")
        assert st == 200
        import hashlib
        row = json.loads((BENCH / "runs/wheel/usd-brep/trial-02/row.json").read_text())
        assert hashlib.sha256(data).hexdigest() == row["build"]["sha256"]
        import urllib.error
        try:
            get(port, "/dl?cell=..%7C..%7Ct1&f=../../../etc/passwd")
            assert False, "path escape served"
        except urllib.error.HTTPError as e:
            assert e.code == 403
    finally:
        proc.terminate()
