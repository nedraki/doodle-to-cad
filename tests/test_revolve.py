"""Issue #95: bounded revolve — validator rules and verified kernel fixtures.

Every fixture volume is the analytic Pappus value of its closed radius-height
loop. The KERNEL tests run the real worker; the validator tests run anywhere.
"""
import json
import math

import pytest
import trimesh

from doodle_to_cad import brep
from doodle_to_cad.brep import build_brep
from doodle_to_cad.brep_recipe import validate_recipe
from doodle_to_cad.build_contract import BuildInput
from doodle_to_cad.revolve_profile import resolve_revolve_profile

KERNEL = pytest.mark.skipif(not brep.worker_available(), reason="BRep worker not configured")

CYLINDER = [[0, 0], [10, 0], [10, 20], [0, 20]]
ANNULUS = [[5, 0], [10, 0], [10, 20], [5, 20]]
STEPPED_KNOB = [[0, 0], [25, 0], [25, 8], [12, 8], [12, 28], [28, 28], [28, 38], [0, 38]]
SOLID_VASE = [[0, 120], [24.19425, 120], [13.44125, 90], [53.765, 66], [18.81775, 18], [18.81775, 0], [0, 0]]
HOLLOW_VASE = [[0, 0], [35.8, 0], [46.9, 14.3], [51.4, 23], [47.5, 33.3], [28.6, 58.5], [25.3, 80.7],
               [30.1, 97.6], [41.4, 120], [37.4, 120], [26.1, 97.6], [21.3, 80.7], [24.6, 58.5],
               [43.5, 33.3], [47.4, 23], [42.9, 14.3], [34.9, 4], [0, 4]]

# Analytic volumes of revolution (Pappus), mm3, verified against the archived
# native probes in /tmp/brep-revolution-investigation (round-trip < 1.8e-8).
EXPECTED = {
    "cylinder": (CYLINDER, 6283.1853, [20.0, 20.0, 20.0]),
    "annulus": (ANNULUS, 4712.389, [20.0, 20.0, 20.0]),
    "stepped_knob": (STEPPED_KNOB, 49385.8365, [56.0, 56.0, 38.0]),
    "solid_vase": (SOLID_VASE, 363616.215, [107.53, 107.53, 120.0]),
    "hollow_vase": (HOLLOW_VASE, 117398.9634, [102.8, 102.8, 120.0]),
}


def _recipe(operations, parameters=None, output=None):
    return {"version": 1, "units": "mm", "name": "revolve fixture",
            "parameters": parameters or {}, "operations": operations,
            "output": output or operations[-1]["id"]}


def _revolve(profile, origin=(0, 0, 0), parameters=None, op_id="part"):
    return _recipe([{"id": op_id, "kind": "revolve", "origin": list(origin),
                     "axis": "z", "profile": profile}], parameters)


def _pappus(points):
    area = centroid_r = 0.0
    for i in range(len(points)):
        x1, y1 = points[i]
        x2, y2 = points[(i + 1) % len(points)]
        cross = x1 * y2 - x2 * y1
        area += cross
        centroid_r += (x1 + x2) * cross
    area /= 2.0
    centroid_r /= 6.0 * area
    return 2.0 * math.pi * abs(area * centroid_r)


# ---------- validator (no kernel needed) ----------

def test_revolve_resolves_profile_and_accepts_explicit_closure():
    closed = CYLINDER + [CYLINDER[0]]
    edited, resolved = validate_recipe(_recipe([
        {"id": "part", "kind": "revolve", "origin": [0, 0, 0], "axis": "z", "profile": closed}]))
    assert resolved[0]["profile"] == [[float(r), float(z)] for r, z in CYLINDER]
    assert edited["operations"][0]["profile"] == closed  # raw document is preserved


def test_revolve_numeric_fields_accept_parameter_expressions():
    profile = [["R", 0], ["R", "h"], [0, "h"]]
    params = {"R": {"value": 10, "min": 5, "max": 20}, "h": {"value": 30, "min": 10, "max": 60}}
    _, resolved = validate_recipe(_recipe([
        {"id": "cup", "kind": "revolve", "origin": [0, 0, 0], "axis": "z", "profile": profile}], params))
    assert resolved[0]["profile"] == [[10.0, 0.0], [10.0, 30.0], [0.0, 30.0]]


def test_revolve_version_2_contract():
    recipe = {
        "version": 2, "units": "mm", "name": "ring", "parameters": {},
        "operations": [{"id": "ring", "kind": "revolve", "origin": [0, 0, 0], "axis": "z",
                        "profile": ANNULUS, "frame": "world", "depends_on": [], "evidence": ["a1"]}],
        "output": "ring",
        "frames": {"world": {"origin": [0, 0, 0], "x": "width", "y": "depth", "z": "height"}},
        "bodies": [{"id": "part", "output": "ring"}],
        "evidence": {"observed": [], "inferred": [],
                     "assumptions": [{"id": "a1", "text": "Ring profile from drawing."}], "unresolved": []},
        "constraints": []}
    from doodle_to_cad.construction_recipe import validate_v2
    edited, _ = validate_v2(recipe)
    assert edited["operations"][0]["kind"] == "revolve"


@pytest.mark.parametrize("profile,message", [
    ([[-1, 0], [10, 0], [10, 10], [0, 10]], "Radius must be 0 or positive"),
    ([[0, 0], [10, 0], [0, 10], [10, 10]], "crosses or touches"),
    ([[0, 0], [0, 5], [0, 10]], "lies on the axis"),
    ([[1, 0], [2, 0], [3, 0]], "folds back"),
    ([[0, 0], [10, 0], [10, 0], [0, 10]], "repeated vertices"),
    ([[0, 0], [10, 0], [10, 10], [5, 0]], "crosses or touches"),
    ([[0, 0], [10, 0], [5, 0], [5, 5]], "folds back"),
    ([[0, 0], [10, 0]], "3-128"),
])
def test_revolve_profile_rejections(profile, message):
    with pytest.raises(ValueError) as err:
        validate_recipe(_recipe([
            {"id": "part", "kind": "revolve", "origin": [0, 0, 0], "axis": "z", "profile": profile}]))
    assert message in str(err.value)


def test_revolve_axis_and_field_contract():
    with pytest.raises(ValueError, match="Revolve supports the \\+Z axis only"):
        validate_recipe(_recipe([{"id": "part", "kind": "revolve", "origin": [0, 0, 0],
                                  "axis": "x", "profile": CYLINDER}]))
    with pytest.raises(ValueError, match="invalid fields"):
        validate_recipe(_recipe([{"id": "part", "kind": "revolve", "origin": [0, 0, 0],
                                  "axis": "z", "profile": CYLINDER, "height": 10}]))


def test_revolve_dimension_bounds_reject_oversize():
    with pytest.raises(ValueError):
        validate_recipe(_recipe([{"id": "part", "kind": "revolve", "origin": [0, 0, 0],
                                  "axis": "z", "profile": [[0, 0], [20000, 0], [0, 5]]}]))


# ---------- worker fixtures (real kernel) ----------

def _build(tmp_path, recipe):
    tmp_path.mkdir(parents=True, exist_ok=True)
    source = tmp_path / "model.recipe.json"
    source.write_text(json.dumps(recipe))
    run = tmp_path / "run"
    result = build_brep(BuildInput("usd-brep", source, run, render=False))
    return result, run


@pytest.mark.parametrize("name", sorted(EXPECTED))
@KERNEL
def test_revolve_fixtures_build_to_analytic_volume(tmp_path, name):
    profile, volume, extents = EXPECTED[name]
    result, run = _build(tmp_path, _revolve(profile))
    assert result.ok, result.log + json.dumps([vars(d) for d in result.diagnostics])
    diag = result.backend_details
    assert diag["usd_roundtrip"] is True
    assert abs(diag["solid_volume_mm3"] - volume) / volume < 1e-4
    for got, want in zip(diag["extents_mm"], extents):
        assert abs(got - want) < 0.5
    # The worker publishes only after its own guards; re-check the artifact independently.
    mesh = trimesh.load(result.stl, force="mesh")
    assert mesh.is_watertight and mesh.is_winding_consistent
    assert len(mesh.split()) == 1
    assert abs(mesh.volume - volume) / volume < 0.02


@KERNEL
def test_revolve_hollow_vase_has_cavity_volume_below_solid(tmp_path):
    _, hollow_volume, _ = EXPECTED["hollow_vase"]
    outer = [[r, z] for r, z in [(0, 0), (35.8, 0), (46.9, 14.3), (51.4, 23), (47.5, 33.3),
                                 (28.6, 58.5), (25.3, 80.7), (30.1, 97.6), (41.4, 120), (0, 120)]]
    # Same silhouette without the cavity must be far heavier than the vessel.
    assert _pappus(HOLLOW_VASE) < 0.5 * _pappus(outer)
    result, run = _build(tmp_path, _revolve(HOLLOW_VASE))
    assert result.ok, result.log + json.dumps([vars(d) for d in result.diagnostics])
    assert abs(result.backend_details["solid_volume_mm3"] - hollow_volume) / hollow_volume < 1e-4


@KERNEL
def test_revolve_parameter_edit_rebuilds_scaled_solid(tmp_path):
    profile = [["radius", 0], ["radius", "height"], [0, "height"]]
    params = {"radius": {"value": 10, "min": 5, "max": 40}, "height": {"value": 20, "min": 5, "max": 60}}
    small, small_run = _build(tmp_path / "a", _revolve(profile, parameters=params))
    assert small.ok, small.log + json.dumps([vars(d) for d in small.diagnostics])
    doubled = json.loads(json.dumps(params))
    doubled["radius"]["value"] = 20
    big, big_run = _build(tmp_path / "b", _revolve(profile, parameters=doubled))
    assert big.ok, big.log + json.dumps([vars(d) for d in big.diagnostics])
    v_small = small.backend_details["solid_volume_mm3"]
    v_big = big.backend_details["solid_volume_mm3"]
    assert abs(v_big / v_small - 4.0) < 1e-3  # same height, radius doubled


@KERNEL
def test_revolve_origin_translates_in_xy_but_bottom_stays_on_bed(tmp_path):
    result, run = _build(tmp_path, _revolve(CYLINDER, origin=(30, 40, 0)))
    assert result.ok, result.log + json.dumps([vars(d) for d in result.diagnostics])
    bounds = result.backend_details["bounds_mm"]
    # Cylinder r=10 h=20 with base centre at (30,40,0): spans [20,40]x[30,50]x[0,20].
    assert abs(bounds[0][2]) < 1e-3 and abs(bounds[1][2] - 20) < 0.5
    assert abs(bounds[0][0] - 20) < 0.5 and abs(bounds[1][0] - 40) < 0.5
    assert abs(bounds[0][1] - 30) < 0.5 and abs(bounds[1][1] - 50) < 0.5


@KERNEL
def test_revolve_placement_failure_is_reported_not_published(tmp_path):
    # Bottom must sit on Z=0: a raised profile is a placement failure with no published STL.
    result, run = _build(tmp_path, _revolve([[0, 5], [10, 5], [10, 25], [0, 25]]))
    assert not result.ok
    assert any(getattr(d, "code", None) == "placement_failed" for d in result.diagnostics)
    assert not list(run.glob("brep-*"))  # nothing published from a rejected build
