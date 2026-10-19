"""Issue #15 decision: Direct BRep is the UI default backend; manual choice is
kept (OpenSCAD, Auto); the legacy HTTP default for API clients that omit the
field stays 'openscad'. These tests pin all three halves of that contract."""
import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]


def _backend_options():
    html = (REPO / "web/index.html").read_text()
    match = re.search(r'GENERATION BACKEND<select name="backend">(.*?)</select>', html)
    assert match, "backend selector missing from index.html"
    return re.findall(r'<option value="([^"]+)">([^<]+)</option>', match.group(1))


def test_brep_is_the_first_and_default_option():
    options = _backend_options()
    assert options[0] == ("usd-brep", "Direct BRep (default)")
    labels = " ".join(label for _, label in options)
    assert labels.count("(default)") == 1


def test_manual_choice_and_auto_remain_available():
    values = [value for value, _ in _backend_options()]
    assert set(values) == {"usd-brep", "openscad", "auto"}


def test_ui_falls_back_only_for_untouched_selector_when_kernel_missing():
    js = (REPO / "web/app.js").read_text()
    assert "userPickedBackend" in js
    assert re.search(r"!userPickedBackend&&form\.backend\.value==='usd-brep'"
                     r"&&!h\.brep_worker\?\.available", js), "missing guarded fallback"
    assert re.search(r"form\.backend\.value='openscad'", js)
    assert "form.backend.onchange();" in js, "help text not synced on load"


def test_http_default_stays_openscad_for_clients_that_omit_backend(monkeypatch):
    from fastapi.testclient import TestClient
    import doodle_to_cad.app as api

    client_app = TestClient(api.app)
    submitted = {}

    async def fake_generate(self, image, mime, notes, dimension, extra=None, controls=None,
                            run_id=None, on_stage=None):
        submitted["run_id"] = run_id
        return {"id": run_id, "success": True, "evaluation": {"score": 99},
                "attempts": [], "spec": {}, "model": "fake", "duration_seconds": 0.1,
                "files": {"scad": f"/results/{run_id}/model.scad", "stl": None,
                          "attempts": None, "overlay": None, "views": {}}}

    monkeypatch.setattr(api.Pipeline, "generate", fake_generate)
    response = client_app.post("/api/generate",
        files={"image": ("primary.png", _png(), "image/png")},
        data={"notes": "", "dimension": "120", "view_directions": "[]"})
    assert response.status_code == 200
    status = client_app.get(f"/api/generate/{response.json()['job_id']}")
    assert status.json()["status"] == "done", "omitting backend must use the OpenSCAD pipeline"


def _png():
    import numpy as np
    import cv2
    ok, encoded = cv2.imencode(".png", np.zeros((60, 60, 3), np.uint8))
    assert ok
    return encoded.tobytes()
