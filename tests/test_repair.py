"""Targeted post-generation repair (issue #16) on the OpenSCAD backend."""
import asyncio
import json
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from doodle_to_cad import revisions
from doodle_to_cad import repair


ORIGINAL_SCAD = '''/* doodle-meta {"version":1,"parameters":{"hub_diameter":{"label":"Hub","description":"Hub diameter","unit":"mm"},"outer_diameter":{"label":"Outer","description":"Outer diameter","unit":"mm"}}} */
outer_diameter = 120; // mm
hub_diameter = 32; // mm
spoke_count = 8; // count
module wheel(){difference(){cylinder(d=outer_diameter,h=8);translate([0,0,-1])cylinder(d=108,h=10);}cylinder(d=hub_diameter,h=8);}
wheel();
'''
REPAIRED_SCAD = ORIGINAL_SCAD.replace('hub_diameter = 32;', 'hub_diameter = 40;') + '\n// repair-marker: spokes extended into rim\n'

BEFORE_MESH = {"watertight": True, "components": 2, "triangles": 512, "extents_mm": [120.0, 8.0, 120.0], "volume_mm3": 60000.0}
AFTER_MESH = {"watertight": True, "components": 1, "triangles": 640, "extents_mm": [120.0, 8.0, 120.0], "volume_mm3": 61200.0}


class StubClient:
    def image_url(self, data, mime): return "data:image/png;base64,AA"


class StubPipeline:
    def __init__(self, scad=REPAIRED_SCAD, interpretation=None, scad_fail=False, interp_fail=False):
        self.settings = SimpleNamespace(requested_model="stub-model")
        self.client = StubClient()
        self.scad, self.interpretation = scad, interpretation or {"requested_change": "join spokes to rim", "preserve": ["outer diameter"]}
        self.scad_fail, self.interp_fail = scad_fail, interp_fail
        self.calls = []

    async def _json_call(self, messages, out, label, temperature=0):
        self.calls.append(("json", messages))
        if self.interp_fail: raise RuntimeError("interpretation model down")
        return dict(self.interpretation)

    async def _scad_call(self, messages, out, label, temperature=0):
        self.calls.append(("scad", messages))
        if self.scad_fail: raise RuntimeError("repair model down")
        out.mkdir(parents=True, exist_ok=True)
        (out / f"{label}.raw.scad.txt").write_text(self.scad)
        return self.scad


def setup_openscad_run(tmp_path):
    out = tmp_path / "abcdef123456"; out.mkdir()
    (out / "model.scad").write_text(ORIGINAL_SCAD)
    (out / "model.stl").write_bytes(b"fake-stl")
    (out / "input.png").write_bytes(b"fake-png")
    (out / "result.json").write_text(json.dumps({
        "id": out.name, "backend": "openscad", "success": True,
        "spec": {"object": "eight-spoke wheel"}, "evaluation": {"accepted": True, "score": 88},
        "files": {"scad": f"/results/{out.name}/model.scad", "stl": f"/results/{out.name}/model.stl", "views": {}}}))
    return out


def stub_build(fail=False, on_build=None):
    def build_candidate(out, scad_text, candidate_dir, binary):
        candidate_dir.mkdir(parents=True, exist_ok=True)
        (candidate_dir / "model.scad").write_text(scad_text)
        if on_build: on_build()
        if fail: return SimpleNamespace(stl=None, views={}, log="ERROR: syntax error", metadata=lambda: {"ok": False})
        stl = candidate_dir / "model.stl"; stl.write_bytes(b"candidate-stl")
        return SimpleNamespace(stl=stl, views={}, log="", metadata=lambda: {"ok": True})
    return build_candidate


def stub_mesh(meshes):
    """meshes: dict of substring -> diagnostics (or None).

    Matched against ``<parent-dir>/<filename>`` only, never the full path:
    pytest tmp dirs embed the test name (e.g. ``test_repair_...``) and would
    otherwise false-match keys like "repair" on every file in the run.
    """
    def describe(stl):
        if stl is None: return None
        p = Path(stl)
        name = f"{p.parent.name}/{p.name}"
        for key, value in meshes.items():
            if key in name and p.is_file(): return dict(value) if value else None
        return None
    return describe


def run_repair(tmp_path, pipeline=None, monkeypatch=None, payload_overrides=None, build=None, meshes=None):
    out = setup_openscad_run(tmp_path) if monkeypatch is not None else None
    payload = {"parent_id": "original", "selection_version": 0,
               "instruction": "Connect every spoke to the rim. Keep the outer diameter, hub, spoke count, and thickness unchanged."}
    payload.update(payload_overrides or {})
    if build: monkeypatch.setattr(repair, "build_candidate", build)
    monkeypatch.setattr(repair, "mesh_diagnostics", stub_mesh(meshes or {"repair": AFTER_MESH, "model.stl": BEFORE_MESH}))
    result = asyncio.run(repair.repair_preview(pipeline or StubPipeline(), SimpleNamespace(openscad_bin="openscad"), out, payload))
    return out, result


# ---- happy path ------------------------------------------------------------

def test_repair_creates_separate_candidate_without_touching_selection(tmp_path, monkeypatch):
    out, result = run_repair(tmp_path, monkeypatch=monkeypatch, build=stub_build())
    assert result["revision"]["kind"] == "repair"
    assert result["revision"]["parent_id"] == "original"
    assert result["revision"]["candidate"] is True
    assert result["repair"]["started_from"] == "parent-revision"
    assert result["repair"]["instruction"].startswith("Connect every spoke")
    assert result["repair"]["model"] == "stub-model"
    assert result["repair"]["score_carried_from_generation"] is False
    assert result["evaluation"] == {"status": "unverified", "accepted": False, "score": None,
                                    "failures": ["The original generation acceptance score was not rerun for this repair candidate."]}
    by_name = {c["name"]: c for c in result["repair"]["checks"]}
    assert by_name["compiles"]["status"] == "passed"
    assert by_name["connected_components"] == {**by_name["connected_components"], "before": 2, "after": 1, "status": "passed"}
    assert by_name["watertight"]["status"] == "passed"
    assert by_name["extents_preserved"]["status"] == "passed"
    # The stub repair legitimately changes hub_diameter (32→40): changed editable
    # parameters are surfaced for review ("reported"), never silently dropped.
    assert by_name["editable_parameters_preserved"]["status"] == "reported"
    assert by_name["editable_parameters_preserved"]["changed"] == ["hub_diameter"]
    assert by_name["requested_correction"]["status"] == "unverified"
    assert result["repair"]["interpretation"]["requested_change"] == "join spokes to rim"
    # The displayed version is untouched: selection still points at original.
    store = revisions.read_store(out)
    assert store["selected"] == "original" and len(store["revisions"]) == 2
    assert revisions.selected_result(out)["revision"]["id"] == "original"
    assert (out / "result.json").read_text().find('"score": 88') >= 0
    # Candidate files live inside the run dir and its provenance is stored.
    assert result["files"]["stl"].startswith(f"/results/{out.name}/repair-")
    assert Path(result["files"]["repair"]).relative_to(f"/results/{out.name}")
    assert (out / Path(result["files"]["repair"]).relative_to(f"/results/{out.name}")).is_file()
    assert store["revisions"][result["revision"]["id"]]["source_text"] == REPAIRED_SCAD


def test_repair_starts_from_displayed_parameter_edit_not_original(tmp_path, monkeypatch):
    edited = ORIGINAL_SCAD.replace("hub_diameter = 32;", "hub_diameter = 40;")
    out = setup_openscad_run(tmp_path)
    (out / "edited-abc123.scad").write_text(edited)
    (out / "edited-abc123.stl").write_bytes(b"edited-stl")
    pipeline = StubPipeline(scad=REPAIRED_SCAD)
    monkeypatch.setattr(repair, "build_candidate", stub_build())
    monkeypatch.setattr(repair, "mesh_diagnostics", stub_mesh({"edited": BEFORE_MESH, "repair": AFTER_MESH}))
    result = asyncio.run(repair.repair_preview(pipeline, SimpleNamespace(openscad_bin="openscad"), out, {
        "parent_id": "original", "selection_version": 0,
        "instruction": "Connect every spoke to the rim.",
        "displayed": {"source": f"/results/{out.name}/edited-abc123.scad", "stl": f"/results/{out.name}/edited-abc123.stl"}}))
    assert result["repair"]["started_from"] == "displayed-parameter-edit"
    scad_messages = [m for kind, m in pipeline.calls if kind == "scad"][0]
    parts = scad_messages[1]["content"]
    diagnostics = json.loads(parts[0]["text"])          # the correction contract JSON
    current_code = next(p["text"] for p in parts if "CURRENT CODE" in p.get("text", ""))
    assert "hub_diameter = 40" in current_code           # the displayed edit, not the 32 original
    assert "CURRENT CODE" in current_code
    assert any(part.get("type") == "image_url" for part in parts)  # drawing fed in
    assert diagnostics["current_mesh_diagnostics"]["components"] == 2  # measured from the displayed STL
    assert (out / "repair-" ).exists() or any(p.name.startswith("repair-") for p in out.iterdir())


def test_drawing_and_spec_are_supplied_to_the_repair_model(tmp_path, monkeypatch):
    pipeline = StubPipeline()
    out, _ = run_repair(tmp_path, pipeline=pipeline, monkeypatch=monkeypatch, build=stub_build())
    scad_messages = [m for kind, m in pipeline.calls if kind == "scad"][0]
    assert "targeted correction" in scad_messages[0]["content"].lower()
    text = scad_messages[1]["content"][0]["text"]
    assert "eight-spoke wheel" in text                       # original specification
    assert "Connect every spoke to the rim" in text          # correction text
    assert '"components": 2' in text                          # geometry diagnostics
    images = [p for p in scad_messages[1]["content"] if p.get("type") == "image_url"]
    assert len(images) == 1                                  # original drawing


def test_refine_uses_candidate_as_parent_and_keep_chains(tmp_path, monkeypatch):
    out, first = run_repair(tmp_path, monkeypatch=monkeypatch, build=stub_build())
    pipeline = StubPipeline()
    monkeypatch.setattr(repair, "mesh_diagnostics", stub_mesh({"model.stl": AFTER_MESH, "abcdef": AFTER_MESH}))
    second = asyncio.run(repair.repair_preview(pipeline, SimpleNamespace(openscad_bin="openscad"), out, {
        "parent_id": first["revision"]["id"], "selection_version": 0, "instruction": "Make the rim slightly thicker."}))
    assert second["revision"]["parent_id"] == first["revision"]["id"]
    kept = revisions.keep(out, {"revision_id": second["revision"]["id"], "selection_version": 0})
    assert kept["revision"]["id"] == second["revision"]["id"] and kept["revision"]["candidate"] is False
    # Pre-repair versions stay recoverable: keep the original again.
    back = revisions.keep(out, {"revision_id": "original", "selection_version": 1})
    assert back["revision"]["id"] == "original" and back["evaluation"]["score"] == 88


# ---- failure behavior ------------------------------------------------------

def test_compile_failure_keeps_last_valid_and_retains_failed_source(tmp_path, monkeypatch):
    with pytest.raises(HTTPException) as error:
        run_repair(tmp_path, monkeypatch=monkeypatch, build=stub_build(fail=True))
    assert error.value.status_code == 422
    assert error.value.detail["code"] == "build_failed"
    assert "displayed version is unchanged" in error.value.detail["message"]
    out = tmp_path / "abcdef123456"
    store = revisions.read_store(out)
    assert store["selected"] == "original" and len(store["revisions"]) == 1
    candidates = [p for p in out.iterdir() if p.name.startswith("repair-")]
    assert candidates and (candidates[0] / "model.scad").read_text() == REPAIRED_SCAD  # failed attempt kept
    failure = json.loads((candidates[0] / "repair.json").read_text())
    assert failure["failed"]["stage"] == "compile"


def test_model_failure_keeps_last_valid(tmp_path, monkeypatch):
    with pytest.raises(HTTPException) as error:
        run_repair(tmp_path, pipeline=StubPipeline(scad_fail=True), monkeypatch=monkeypatch, build=stub_build())
    assert error.value.status_code == 422
    assert error.value.detail["code"] == "model_failure"
    out = tmp_path / "abcdef123456"
    store = revisions.read_store(out)
    assert store["selected"] == "original" and len(store["revisions"]) == 1


def test_interpretation_failure_degrades_gracefully(tmp_path, monkeypatch):
    out, result = run_repair(tmp_path, pipeline=StubPipeline(interp_fail=True), monkeypatch=monkeypatch, build=stub_build())
    assert result["repair"]["interpretation"] is None
    assert result["repair"]["interpretation_failure"]["error_type"] == "RuntimeError"
    assert {c["name"] for c in result["repair"]["checks"]} >= {"compiles", "connected_components"}


def test_stale_selection_cannot_publish_candidate(tmp_path, monkeypatch):
    def race():  # a keep lands while the model/build is still running
        revisions.keep(out_ref[0], {"revision_id": "original", "selection_version": 0})
    out_ref = []
    def build_then_race(out, scad_text, candidate_dir, binary):
        out_ref.append(out)
        race()
        return stub_build()(out, scad_text, candidate_dir, binary)
    with pytest.raises(HTTPException) as error:
        run_repair(tmp_path, monkeypatch=monkeypatch, build=build_then_race)
    assert error.value.status_code == 409
    out = tmp_path / "abcdef123456"
    assert len(revisions.read_store(out)["revisions"]) == 1


@pytest.mark.parametrize("payload,code", [
    ({"parent_id": "original", "selection_version": 0}, 422),
    ({"parent_id": "original", "selection_version": 0, "instruction": "   "}, 422),
    ({"parent_id": "missing", "selection_version": 0, "instruction": "fix it"}, 404),
    ({"parent_id": "original", "selection_version": 7, "instruction": "fix it"}, 409),
    ({"parent_id": "original", "selection_version": 0, "instruction": "fix it", "displayed": {"nope": 1}}, 422),
    ({"parent_id": "original", "selection_version": 0, "instruction": "x" * 2001}, 422),
])
def test_repair_contract_validation(tmp_path, monkeypatch, payload, code):
    monkeypatch.setattr(repair, "build_candidate", stub_build())
    monkeypatch.setattr(repair, "mesh_diagnostics", stub_mesh({"model.stl": AFTER_MESH}))
    out = setup_openscad_run(tmp_path)
    with pytest.raises(HTTPException) as error:
        asyncio.run(repair.repair_preview(StubPipeline(), SimpleNamespace(openscad_bin="openscad"), out, payload))
    assert error.value.status_code == code


def test_repair_requires_openscad_parent(tmp_path, monkeypatch):
    out = setup_openscad_run(tmp_path)
    (out / "revisions.json").write_text(json.dumps({
        "version": 1, "selected": "original", "selection_version": 0,
        "revisions": {"original": {"id": "original", "parent_id": None, "kind": "generation",
                                   "source_text": ORIGINAL_SCAD, "parameters": [],
                                   "result": {"backend": "usd-brep", "files": {}}}}}))
    monkeypatch.setattr(repair, "build_candidate", stub_build())
    with pytest.raises(HTTPException) as error:
        asyncio.run(repair.repair_preview(StubPipeline(), SimpleNamespace(openscad_bin="openscad"), out,
                                          {"parent_id": "original", "selection_version": 0, "instruction": "fix"}))
    assert error.value.status_code == 422


@pytest.mark.parametrize("url", [
    "/results/ffffffffffff/model.scad",
    "/results/abcdef123456/../secrets.txt",
    "/results/abcdef123456/nonexistent.scad",
    "/etc/passwd",
])
def test_displayed_source_must_be_a_real_file_of_the_run(tmp_path, monkeypatch, url):
    out = setup_openscad_run(tmp_path)
    (tmp_path / "secrets.txt").write_text("nope")
    monkeypatch.setattr(repair, "build_candidate", stub_build())
    monkeypatch.setattr(repair, "mesh_diagnostics", stub_mesh({"model.stl": AFTER_MESH}))
    with pytest.raises(HTTPException) as error:
        asyncio.run(repair.repair_preview(StubPipeline(), SimpleNamespace(openscad_bin="openscad"), out, {
            "parent_id": "original", "selection_version": 0, "instruction": "fix it",
            "displayed": {"source": url}}))
    assert error.value.status_code == 422


# ---- deterministic measurements --------------------------------------------

def test_preservation_checks_documented_tolerances():
    checks = {c["name"]: c for c in repair.preservation_checks(
        BEFORE_MESH, {**AFTER_MESH, "extents_mm": [121.0, 8.0, 120.0]},
        {"hub_diameter": 32.0}, {"hub_diameter": 40.0})}
    assert checks["extents_preserved"]["status"] == "passed"     # 1 mm within rel 2% / abs 0.5 mm
    checks = {c["name"]: c for c in repair.preservation_checks(
        BEFORE_MESH, {**AFTER_MESH, "extents_mm": [130.0, 8.0, 120.0]}, {"hub_diameter": 32.0}, {"hub_diameter": 32.0})}
    assert checks["extents_preserved"]["status"] == "failed"
    assert checks["extents_preserved"]["drift"] == [{"axis": "x", "before": 120.0, "after": 130.0}]
    checks = {c["name"]: c for c in repair.preservation_checks(
        BEFORE_MESH, AFTER_MESH, {"hub_diameter": 32.0, "spoke_count": 8.0}, {"hub_diameter": 32.0, "spoke_count": 6.0})}
    assert checks["editable_parameters_preserved"]["status"] == "reported"
    assert checks["editable_parameters_preserved"]["changed"] == ["spoke_count"]
    untouched = {c["name"]: c for c in repair.preservation_checks(
        BEFORE_MESH, AFTER_MESH, {"hub_diameter": 32.0}, {"hub_diameter": 32.0})}
    assert untouched["editable_parameters_preserved"]["status"] == "passed"
    assert untouched["editable_parameters_preserved"]["changed"] == []
    component_status = {}
    for before, after in ((2, 1), (2, 2), (2, 3), (3, 2)):
        made = repair.preservation_checks({**BEFORE_MESH, "components": before}, {**AFTER_MESH, "components": after}, {}, {})
        component_status[(before, after)] = next(c for c in made if c["name"] == "connected_components")["status"]
    assert component_status == {(2, 1): "passed", (2, 2): "unchanged", (2, 3): "regressed", (3, 2): "improved"}
    watertight = {c["name"]: c for c in repair.preservation_checks(BEFORE_MESH, {**AFTER_MESH, "watertight": False}, {}, {})}
    assert watertight["watertight"]["status"] == "failed" and watertight["watertight"]["before"] is True


def test_mesh_diagnostics_counts_components_separately_from_watertight(tmp_path):
    import trimesh
    single = trimesh.creation.box(extents=(120, 8, 120))
    single_path = tmp_path / "single.stl"; single.export(single_path)
    pair = trimesh.util.concatenate([single, trimesh.creation.box(extents=(10, 10, 10)).apply_translation([0, 40, 160])])
    pair_path = tmp_path / "pair.stl"; pair.export(pair_path)
    one = repair.mesh_diagnostics(single_path)
    two = repair.mesh_diagnostics(pair_path)
    assert one["components"] == 1 and one["watertight"] is True
    # Two watertight bodies are still NOT one connected component — the wheel lesson.
    assert two["components"] == 2 and two["watertight"] is True
    assert repair.mesh_diagnostics(tmp_path / "missing.stl") is None
    (tmp_path / "junk.stl").write_bytes(b"not a mesh")
    assert repair.mesh_diagnostics(tmp_path / "junk.stl") is None


# ---- endpoint wiring ---------------------------------------------------------

def test_endpoint_keep_params_and_stale_requests(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient
    import doodle_to_cad.app as api
    from dataclasses import replace
    out = setup_openscad_run(tmp_path)
    monkeypatch.setattr(api, "settings", replace(api.settings, results_dir=tmp_path))
    monkeypatch.setattr(api, "pipeline", StubPipeline())  # never touch the live model server
    monkeypatch.setattr(repair, "build_candidate", stub_build())
    monkeypatch.setattr(repair, "mesh_diagnostics", stub_mesh({"repair": AFTER_MESH, "model.stl": BEFORE_MESH}))
    client = TestClient(api.app)
    response = client.post(f"/api/results/{out.name}/revisions/repair",
                           json={"parent_id": "original", "selection_version": 0, "instruction": "join the spokes"})
    assert response.status_code == 200
    candidate = response.json()
    assert candidate["revision"]["kind"] == "repair" and candidate["revision"]["candidate"] is True
    # Stale selection_version is rejected while selection stays valid.
    stale = client.post(f"/api/results/{out.name}/revisions/repair",
                        json={"parent_id": "original", "selection_version": 5, "instruction": "join the spokes"})
    assert stale.status_code == 409
    assert client.get(f"/api/results/{out.name}").json()["revision"]["id"] == "original"
    kept = client.post(f"/api/results/{out.name}/revisions/keep",
                       json={"revision_id": candidate["revision"]["id"], "selection_version": 0})
    assert kept.status_code == 200 and kept.json()["revision"]["id"] == candidate["revision"]["id"]
    # Downloads and parameter controls follow the displayed revision.
    displayed = client.get(f"/api/results/{out.name}").json()
    assert displayed["files"]["stl"] == candidate["files"]["stl"]
    assert displayed["original_files"]["stl"] == f"/results/{out.name}/model.stl"
    params = client.get(f"/api/results/{out.name}/params", params={"revision_id": candidate["revision"]["id"]}).json()
    values = {p["name"]: p["value"] for p in params["params"]}
    assert values["hub_diameter"] == 40  # repaired value, not the 32 of model.scad
    assert params["revision_id"] == candidate["revision"]["id"]
    original_params = client.get(f"/api/results/{out.name}/params", params={"revision_id": "original"}).json()
    assert {p["name"]: p["value"] for p in original_params["params"]}["hub_diameter"] == 32
    # Failed contract calls never overwrite the kept result.
    bad = client.post(f"/api/results/{out.name}/revisions/repair", json={"parent_id": "original", "selection_version": 1})
    assert bad.status_code == 422
    assert client.get(f"/api/results/{out.name}").json()["revision"]["id"] == candidate["revision"]["id"]
    assert client.post("/api/results/deadbeef/revisions/repair",
                       json={"parent_id": "original", "selection_version": 0, "instruction": "x"}).status_code == 404


def test_parametrize_follows_displayed_revision(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient
    import doodle_to_cad.app as api
    import doodle_to_cad.openscad as openscad_module
    from dataclasses import replace
    out = setup_openscad_run(tmp_path)
    monkeypatch.setattr(api, "settings", replace(api.settings, results_dir=tmp_path))
    monkeypatch.setattr(api, "pipeline", StubPipeline())  # never touch the live model server
    monkeypatch.setattr(repair, "build_candidate", stub_build())
    monkeypatch.setattr(repair, "mesh_diagnostics", stub_mesh({"repair": AFTER_MESH, "model.stl": BEFORE_MESH}))
    captured = {}
    def fake_compile(output_dir, scad_text, tag, binary="openscad"):
        captured["scad_text"] = scad_text
        return f"/results/{output_dir.name}/{tag}.stl", ""
    monkeypatch.setattr(openscad_module, "compile_stl_only", fake_compile)
    client = TestClient(api.app)
    candidate = client.post(f"/api/results/{out.name}/revisions/repair",
                            json={"parent_id": "original", "selection_version": 0, "instruction": "join"}).json()
    client.post(f"/api/results/{out.name}/revisions/keep",
                json={"revision_id": candidate["revision"]["id"], "selection_version": 0})
    response = client.post(f"/api/results/{out.name}/parametrize",
                           params={"revision_id": candidate["revision"]["id"]}, json={"hub_diameter": 44})
    assert response.status_code == 200 and response.json()["ok"] is True
    assert "// repair-marker" in captured["scad_text"]      # edited FROM the kept repair, not model.scad
    assert "hub_diameter = 44" in captured["scad_text"]
    history = (out / "parametrize-history.jsonl").read_text()
    assert candidate["revision"]["id"] in history