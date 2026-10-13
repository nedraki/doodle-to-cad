import copy
import json
import os
from pathlib import Path
import subprocess

import pytest

from doodle_to_cad.brep import build_recipe
from doodle_to_cad.brep_recipe import scalar, validate_recipe

FIXTURES = Path(__file__).resolve().parents[1] / "benchmarks" / "brep"


def recipe(name="bracket"):
    return json.loads((FIXTURES / f"{name}.json").read_text())


@pytest.mark.parametrize("expression", ["__import__('os')", "width ** 2", "width.real", "[1][0]", "1/0", "True", "unknown", "1e309"])
def test_no_executable_or_nonfinite_dimensions(expression):
    with pytest.raises(ValueError):
        scalar(expression, {"width": 60})


def test_detail_updates_resolve_dependencies_without_mutating_source():
    source = recipe()
    baseline = copy.deepcopy(source)
    edited, ops = validate_recipe(source, {"hole1_width": 12, "thickness": 7})
    cutter = next(op for op in ops if op["id"] == "cutter1")
    assert cutter["size"] == [12, 9, 15]
    assert source == baseline
    assert edited["parameters"]["hole1_width"]["value"] == 12


@pytest.mark.parametrize("updates", [{"unknown": 1}, {"hole1_width": -1}, {"hole1_width": True}, {"hole1_width": float('nan')}])
def test_invalid_updates_rejected(updates):
    with pytest.raises(ValueError):
        validate_recipe(recipe(), updates)


def test_forward_reference_and_duplicate_ids_rejected():
    source = recipe()
    source["operations"][2]["left"] = "cut4"
    with pytest.raises(ValueError):
        validate_recipe(source)
    source = recipe()
    source["operations"][1]["id"] = "base"
    with pytest.raises(ValueError):
        validate_recipe(source)


def test_timeout_publishes_nothing(tmp_path, monkeypatch):
    monkeypatch.setattr("doodle_to_cad.brep.worker_python", lambda: "/python")
    def timeout(*args, **kwargs):
        raise subprocess.TimeoutExpired(args[0], 120)
    monkeypatch.setattr("doodle_to_cad.brep.subprocess.run", timeout)
    existing = tmp_path / "last-valid.stl"
    existing.write_bytes(b"last valid")
    with pytest.raises(ValueError, match="timed out"):
        build_recipe(tmp_path, recipe())
    assert list(tmp_path.iterdir()) == [existing]
    assert existing.read_bytes() == b"last valid"


@pytest.mark.skipif(not os.getenv("DOODLE_BREP_PYTHON"), reason="Isolated BRep worker not configured")
def test_kernel_build_edit_and_failure_recovery(tmp_path):
    import trimesh
    source = recipe()
    original = build_recipe(tmp_path, source)
    original_dir = tmp_path / original["stl"].split('/')[-2]
    original_bytes = (original_dir / "model.stl").read_bytes()
    assert original["diagnostics"]["solid_volume_mm3"] == pytest.approx(31500)
    assert original["diagnostics"]["euler_number"] == -6
    changed = build_recipe(tmp_path, source, {"hole1_width": 12, "hole1_x": 12})
    assert changed["diagnostics"]["solid_volume_mm3"] == pytest.approx(31350)
    assert changed["diagnostics"]["euler_number"] == -6
    # Independently section the wall: none of the four openings may disappear.
    mesh = trimesh.load(original_dir / "model.stl", force="mesh")
    import networkx as nx
    lines = trimesh.intersections.mesh_plane(mesh, plane_normal=[0, 1, 0], plane_origin=[0, 2, 0])
    graph = nx.Graph()
    for a, b in lines:
        graph.add_edge(tuple(a.round(5)), tuple(b.round(5)))
    loops = list(nx.connected_components(graph))
    assert len(loops) == 5  # outer boundary plus four holes
    assert all(degree == 2 for _, degree in graph.degree())
    bounds = sorted((min(p[0] for p in loop), min(p[2] for p in loop),
                     max(p[0] for p in loop), max(p[2] for p in loop)) for loop in loops)
    assert bounds == [(0, 0, 60, 80), (10, 20, 20, 35), (10, 50, 20, 65),
                      (35, 20, 45, 35), (35, 50, 45, 65)]
    enclosure = recipe("enclosure")
    enclosure["parameters"]["fillet"]["max"] = 1000
    with pytest.raises(ValueError):
        build_recipe(tmp_path, enclosure, {"fillet": 1000})
    assert (original_dir / "model.stl").read_bytes() == original_bytes
    assert len(list(tmp_path.glob("brep-*"))) == 2


def test_brep_api_routes_and_original_preservation(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient
    from doodle_to_cad import app as module
    from dataclasses import replace
    monkeypatch.setattr(module, "settings", replace(module.settings, results_dir=tmp_path))
    run = tmp_path / "abc123"
    run.mkdir()
    source = recipe()
    (run / "model.recipe.json").write_text(json.dumps(source))
    client = TestClient(module.app)
    response = client.get('/api/results/abc123/params')
    assert response.status_code == 200
    assert any(p["name"] == "hole1_width" for p in response.json()["params"])
    before = (run / "model.recipe.json").read_bytes()
    response = client.post('/api/results/abc123/parametrize', json={"hole1_width": -5})
    assert response.status_code == 422
    assert (run / "model.recipe.json").read_bytes() == before
    assert client.get('/api/results/not-a-run/params').status_code == 404
