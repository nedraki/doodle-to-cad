"""Task 15 (#32): targeted recipe edits on a selected target, with measured proof.

Every edit must (a) change exactly the selected feature and (b) preserve declared
fixed dimensions, measured on the exported mesh. Planted-error tests prove the
checkers can actually fail before any green result is trusted.
"""
import json
import shutil
from pathlib import Path

import pytest
import trimesh

from doodle_to_cad.brep import build_brep, worker_available
from doodle_to_cad.build_contract import BuildInput
from doodle_to_cad import targeted_edits

ROOT = Path(__file__).resolve().parents[1]
POCKET = json.loads((ROOT / "benchmarks/brep-targeted/pocket-block.json").read_text())
BOOKEND = json.loads((ROOT / "benchmarks/brep-selection/bookend.json").read_text())
KERNEL = pytest.mark.skipif(not worker_available(), reason="Native worker not configured")

POCKET_RULE = {"kind": "box_cutout", "owner": "cut1", "cutter": "box_p1"}
OTHER_FLOORS = {"cut2": (46.0, 14.0, 18.0), "cut3": (14.0, 30.0, 15.0)}


def build(recipe, tmp):
    tmp.mkdir(parents=True, exist_ok=True)
    source = tmp / "recipe.json"
    source.write_text(json.dumps(recipe))
    result = build_brep(BuildInput("usd-brep", source, tmp, render=False))
    assert result.ok, result.log
    return result


def floor_z(mesh, cx, cy, top=20.0):
    from doodle_to_cad.targeted_edits import _inside
    # Start half a step below the top face so the scan never lands exactly on a
    # surface (ray parity on-boundary is undefined); resolution stays 0.05 mm.
    z = top - 0.03
    while z > 0.02 and not _inside(mesh, [(cx, cy, z)])[0]:
        z -= 0.05
    return round(z, 2)


@KERNEL
def test_pocket_fixture_builds_and_catalog_uses_five_floor_faces(tmp_path):
    result = build(POCKET, tmp_path)
    catalog = result.backend_details["selection_catalog"]
    assert catalog["status"] == "available"
    rules = [t["rule"] for t in catalog["targets"] if t["rule"]["kind"] == "box_cutout"]
    assert sorted(r["owner"] for r in rules) == ["cut1", "cut2", "cut3"]
    assert all(r["expected_faces"] == 5 for r in rules), "top pockets expose four walls plus floor"


@KERNEL
def test_plan_pocket_depth_rejects_through_openings_expressions_and_unsupported_rules():
    with pytest.raises(ValueError, match="[Pp]arameter"):
        targeted_edits.plan(BOOKEND, {"kind": "box_cutout", "owner": "cut4", "cutter": "cutter4"}, 5.0)
    through = json.loads(json.dumps(POCKET))
    cutter = next(op for op in through["operations"] if op["id"] == "box_p1")
    cutter["origin"][1] = -1.0
    cutter["size"][1] = 42.0
    with pytest.raises(ValueError, match="[Tt]hrough"):
        targeted_edits.plan(through, POCKET_RULE, 5.0)
    expression = json.loads(json.dumps(POCKET))
    expression["operations"][1]["size"][2] = "depth_1"
    expression["parameters"]["depth_1"] = {"value": 3, "min": 1, "max": 6}
    with pytest.raises(ValueError, match="[Pp]arameter"):
        targeted_edits.plan(expression, POCKET_RULE, 5.0)
    with pytest.raises(ValueError, match="[Ss]upported"):
        targeted_edits.plan(POCKET, {"kind": "extreme_face", "owner": "cut3", "axis": 2, "side": "max"}, 5.0)
    with pytest.raises(ValueError):
        targeted_edits.plan(POCKET, POCKET_RULE, 0)


@KERNEL
def test_plan_pocket_depth_deepens_only_the_selected_pocket(tmp_path):
    original = build(POCKET, tmp_path / "before")
    edited, edit = targeted_edits.plan(POCKET, POCKET_RULE, 5.0)
    assert edited is not POCKET
    cutter = next(op for op in edited["operations"] if op["id"] == "box_p1")
    assert cutter["origin"][2] == 15.0 and cutter["size"][2] == 5.0
    assert edit["operation"] == "pocket_depth" and abs(edit["new_floor"] - 15.0) < 1e-6
    changed = build(edited, tmp_path / "after")
    report = targeted_edits.verify_edit(original.stl, changed.stl, edit)
    assert report["ok"], report
    assert any("floor" in name for name in report["checks"])
    mesh = trimesh.load(changed.stl, force="mesh")
    assert abs(floor_z(mesh, 14.0, 14.0) - 15.0) <= 0.05
    for owner, (cx, cy, floor) in OTHER_FLOORS.items():
        assert abs(floor_z(mesh, cx, cy) - floor) <= 0.05, owner
    assert [round(v, 3) for v in mesh.bounds[0]] == [0.0, 0.0, 0.0]
    assert [round(v, 3) for v in mesh.bounds[1]] == [60.0, 40.0, 20.0]


@KERNEL
def test_pocket_checker_rejects_planted_preservation_violation(tmp_path):
    original = build(POCKET, tmp_path / "before")
    broken = json.loads(json.dumps(POCKET))
    next(op for op in broken["operations"] if op["id"] == "body")["size"][0] = 62.0
    cutter = next(op for op in broken["operations"] if op["id"] == "box_p1")
    cutter["origin"][2] = 15.0
    cutter["size"][2] = 5.0
    violation = build(broken, tmp_path / "after")
    _, edit = targeted_edits.plan(POCKET, POCKET_RULE, 5.0)
    report = targeted_edits.verify_edit(original.stl, violation.stl, edit)
    assert not report["ok"]
    assert any("outer" in name.lower() and check["status"] == "failed" for name, check in report["checks"].items())


@KERNEL
def test_pocket_checker_rejects_planted_no_change(tmp_path):
    original = build(POCKET, tmp_path / "before")
    untouched = tmp_path / "untouched.stl"
    shutil.copy(original.stl, untouched)
    _, edit = targeted_edits.plan(POCKET, POCKET_RULE, 5.0)
    report = targeted_edits.verify_edit(original.stl, untouched, edit)
    assert not report["ok"]
    assert any(check["status"] == "failed" for name, check in report["checks"].items() if "floor" in name.lower())


@KERNEL
def test_plan_edge_fillet_rounds_selected_corner_edges(tmp_path):
    rule = {"kind": "outer_vertical_edges", "owner": BOOKEND["output"]}
    original = build(BOOKEND, tmp_path / "before")
    edited, edit = targeted_edits.plan(BOOKEND, rule, 3.0)
    assert edited["operations"][-1]["kind"] == "fillet"
    assert edited["operations"][-1]["selector"] == "outer_vertical"
    assert edited["output"] == edited["operations"][-1]["id"]
    changed = build(edited, tmp_path / "after")
    report = targeted_edits.verify_edit(original.stl, changed.stl, edit)
    assert report["ok"], report
    assert any("contact" in name.lower() for name in report["checks"])


@KERNEL
def test_fillet_checker_rejects_planted_wrong_radius(tmp_path):
    rule = {"kind": "outer_vertical_edges", "owner": BOOKEND["output"]}
    original = build(BOOKEND, tmp_path / "before")
    edited, edit = targeted_edits.plan(BOOKEND, rule, 0.5)
    claimed = build(edited, tmp_path / "after")
    edit["radius"] = 3.0  # planted: verification claims a radius the build does not have
    report = targeted_edits.verify_edit(original.stl, claimed.stl, edit)
    assert not report["ok"]
    assert any(check["status"] == "failed" for name, check in report["checks"].items() if "rounded" in name.lower())


@KERNEL
def test_worker_fillets_outer_vertical_selector(tmp_path):
    recipe = {"version": 1, "units": "mm", "parameters": {}, "output": "round",
              "operations": [{"id": "block", "kind": "box", "origin": [0, 0, 0], "size": [40, 30, 10]},
                             {"id": "round", "kind": "fillet", "body": "block", "radius": 2, "selector": "outer_vertical"}]}
    result = build(recipe, tmp_path)
    assert result.measurements["components"] == 1 and result.measurements["watertight"]


@KERNEL
def test_targeted_edit_flows_through_preview_keep_and_stale_guards(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient
    from dataclasses import replace
    from doodle_to_cad.config import settings
    from doodle_to_cad import app as app_module
    monkeypatch.setattr(app_module, "settings", replace(settings, results_dir=tmp_path))
    tmp_path.mkdir(exist_ok=True)
    with TestClient(app_module.app) as client:
        initial = client.post("/api/brep/build", json=POCKET).json()
        job = initial["id"]
        target = next(t for t in initial["diagnostics"]["selection_catalog"]["targets"]
                      if t["rule"]["kind"] == "box_cutout" and t["rule"]["owner"] == "cut1")
        chosen = client.post("/api/results/" + job + "/selection", json={
            "revision_id": "original", "target_id": target["id"],
            "target_version": 0, "selection_version": 0}).json()
        assert chosen["target_selection"]["status"] == "matched"
        preview = client.post("/api/results/" + job + "/revisions/targeted", json={
            "parent_id": "original", "selection_version": 0,
            "operation": "pocket_depth", "value": 5.0})
        assert preview.status_code == 200, preview.text
        candidate = preview.json()
        assert candidate["revision"]["candidate"] and candidate["targeted"]["operation"] == "pocket_depth"
        assert candidate["targeted"]["ok"]
        kept = client.post("/api/results/" + job + "/revisions/keep",
                           json={"revision_id": candidate["revision"]["id"], "selection_version": 0})
        assert kept.status_code == 200 and kept.json()["revision"]["selected_id"] == candidate["revision"]["id"]
        stale = client.post("/api/results/" + job + "/revisions/targeted", json={
            "parent_id": "original", "selection_version": 0, "operation": "pocket_depth", "value": 7.0})
        assert stale.status_code == 409
        face_target = next(t for t in initial["diagnostics"]["selection_catalog"]["targets"]
                           if t["rule"]["kind"] == "extreme_face")
        kept_result = kept.json()
        client.post("/api/results/" + job + "/selection", json={
            "revision_id": candidate["revision"]["id"], "target_id": face_target["id"],
            "target_version": kept_result["target_version"],
            "selection_version": kept_result["revision"]["selection_version"]})
        wrong = client.post("/api/results/" + job + "/revisions/targeted", json={
            "parent_id": candidate["revision"]["id"], "selection_version": kept_result["revision"]["selection_version"],
            "operation": "pocket_depth", "value": 5.0})
        assert wrong.status_code == 422
        unsupported = client.post("/api/results/" + job + "/revisions/targeted", json={
            "parent_id": candidate["revision"]["id"], "selection_version": kept_result["revision"]["selection_version"],
            "operation": "warp", "value": 1.0})
        assert unsupported.status_code == 422
