"""Vocabulary expansion: kernel-backed recipe kinds beyond the original eight.

Validator tests run anywhere. KERNEL smoke builds run the real worker and
assert analytic volume/extents, pinning each primitive's placement semantics.
"""
import copy
import json
import math
import re

import pytest

from doodle_to_cad import brep
from doodle_to_cad.brep import build_brep
from doodle_to_cad.brep_recipe import validate_recipe
from doodle_to_cad.build_contract import BuildInput

KERNEL = pytest.mark.skipif(not brep.worker_available(), reason="BRep worker not configured")


def _v1(ops, output):
    return {"version": 1, "units": "mm", "parameters": {}, "operations": ops, "output": output}


def _op(oid, kind, **fields):
    return {"id": oid, "kind": kind, **fields}


def _build_probe(tmp_path, recipe, attempts=3):
    """Build the recipe. On placement_failed, lift every origin Z by the
    reported min_z_mm deficit and retry — the worker pins min_z to 0 exactly."""
    recipe = copy.deepcopy(recipe)
    for attempt in range(attempts):
        source = tmp_path / f"model-{attempt}.recipe.json"
        source.parent.mkdir(parents=True, exist_ok=True)
        source.write_text(json.dumps(recipe))
        run = tmp_path / f"run-{attempt}"
        result = build_brep(BuildInput("usd-brep", source, run, render=False))
        if result.ok:
            return result
        text = result.log or ""
        match = re.search(r"minimum_z_mm=(-?[0-9.eE+]+)", text)
        if attempt + 1 >= attempts or not match:
            return result
        deficit = -float(match.group(1))
        for op in recipe["operations"]:
            if "origin" in op:
                op["origin"] = [op["origin"][0], op["origin"][1], op["origin"][2] + deficit]
    raise AssertionError("unreachable")


def _assert(result, extents=None, volume=None, tol=0.5, rel=1e-3):
    assert result.ok, (result.log or "")[:2000]
    diag = result.backend_details
    assert diag["usd_roundtrip"] is True
    if extents:
        for got, want in zip(diag["extents_mm"], extents):
            assert abs(got - want) < tol, f"extents {diag['extents_mm']} vs {want}"
    if volume:
        assert abs(diag["solid_volume_mm3"] - volume) / volume < rel, diag["solid_volume_mm3"]


LINE = lambda a, b: {"kind": "line", "start": list(a), "end": list(b)}
SQUARE = [[LINE((0, 0), (10, 0)), LINE((10, 0), (10, 10)), LINE((10, 10), (0, 10)), LINE((0, 10), (0, 0))]]


@KERNEL
def test_sphere_builds_full_volume_on_the_plate(tmp_path):
    result = _build_probe(tmp_path, _v1([_op("b", "sphere", origin=[0, 0, 0], radius=10)], "b"))
    _assert(result, extents=[20, 20, 20], volume=4 / 3 * math.pi * 1000)


@KERNEL
def test_cone_frustum_apex_and_partial(tmp_path):
    frustum = _op("b", "cone", origin=[0, 0, 0], radius_base=6, radius_top=2, height=10, angle=360, axis="z")
    v = math.pi * 10 / 3 * (36 + 12 + 4)
    _assert(_build_probe(tmp_path, _v1([frustum], "b")), volume=v)
    apex = _op("b", "cone", origin=[0, 0, 0], radius_base=6, radius_top=0, height=10, angle=360, axis="z")
    _assert(_build_probe(tmp_path / "apex", _v1([apex], "b")), volume=math.pi * 36 * 10 / 3)
    quarter = _op("b", "cone", origin=[0, 0, 0], radius_base=6, radius_top=6, height=10, angle=90, axis="z")
    _assert(_build_probe(tmp_path / "quarter", _v1([quarter], "b")), volume=math.pi * 36 * 10 / 4)


@KERNEL
def test_torus_sits_on_the_plate(tmp_path):
    torus = _op("b", "torus", origin=[0, 0, 0], bend_radius=8, radius=2, angle=360, axis="z")
    _assert(_build_probe(tmp_path, _v1([torus], "b")), extents=[20, 20, 4], volume=2 * math.pi ** 2 * 8 * 4)


@KERNEL
def test_wedge_is_a_angular_cylinder_slice(tmp_path):
    wedge = _op("b", "wedge", origin=[0, 0, 0], radius=10, height=5, start_angle=0, end_angle=90, axis="z")
    _assert(_build_probe(tmp_path, _v1([wedge], "b")), volume=math.pi * 100 * 5 / 4)


@KERNEL
def test_pyramid_and_arc_block_build(tmp_path):
    pyramid = _op("b", "pyramid", origin=[0, 0, 0], base=10, height=6)
    _assert(_build_probe(tmp_path, _v1([pyramid], "b")), volume=100 * 6 / 3)
    arc = _op("b", "arc_block", origin=[0, 0, 0], length=5, inside_radius=4, outside_radius=10,
              start_angle=0, end_angle=90)
    _assert(_build_probe(tmp_path / "arc", _v1([arc], "b")), volume=math.pi * (100 - 16) / 4 * 5)


@KERNEL
def test_helix_spring_builds(tmp_path):
    helix = _op("b", "helix", origin=[0, 0, 0], height=20, radius_start=10, radius_end=10, turns=4, tube_radius=2.0)
    path = 4 * math.hypot(2 * math.pi * 10, 20 / 4)
    _assert(_build_probe(tmp_path, _v1([helix], "b")), volume=math.pi * 4.0 * path, tol=0.5, rel=0.01)
    # The worker's 2% mesh-volume guard rejects thinner tubes; the validator must too.
    from doodle_to_cad.brep_recipe import validate_recipe
    with pytest.raises(ValueError, match="tube_radius"):
        validate_recipe(_v1([_op("b", "helix", origin=[0, 0, 0], height=20, radius_start=10, radius_end=10,
                                 turns=4, tube_radius=0.5)], "b"))


@KERNEL
def test_draft_extrude_tapers_inward(tmp_path):
    op = _op("b", "drafted_extrude", origin=[0, 0, 0], plane="xy", direction=1, depth=5, draft_angle=45, loops=SQUARE)
    result = _build_probe(tmp_path, _v1([op], "b"))
    # Verified kernel semantics: positive draft_angle shrinks the section going up.
    # At 45 deg over 5 mm a 10 mm square converges to a point: pyramid volume 100*5/3.
    _assert(result, extents=[10, 10, 5], volume=100 * 5 / 3)


def _reject(recipe, needle):
    with pytest.raises(ValueError) as excinfo:
        validate_recipe(recipe)
    assert needle in str(excinfo.value)


def test_validator_matrix_rejects_bad_new_kinds():
    _reject(_v1([_op("b", "sphere", origin=[0, 0, 0])], "b"), "invalid fields")
    _reject(_v1([_op("b", "cone", origin=[0, 0, 0], radius_base=2, radius_top=6, height=10, angle=360, axis="z")], "b"),
            "radius_top must not exceed")
    _reject(_v1([_op("b", "cone", origin=[0, 0, 0], radius_base=6, radius_top=2, height=10, angle=400, axis="z")], "b"),
            "cone angle must be")
    _reject(_v1([_op("b", "torus", origin=[0, 0, 0], bend_radius=2, radius=8, angle=360, axis="z")], "b"),
            "radius < bend_radius")
    _reject(_v1([_op("b", "wedge", origin=[0, 0, 0], radius=10, height=5, start_angle=100, end_angle=90, axis="z")], "b"),
            "start_angle must be")
    _reject(_v1([_op("b", "arc_block", origin=[0, 0, 0], length=5, inside_radius=10, outside_radius=4,
                     start_angle=0, end_angle=90)], "b"), "outside_radius must exceed")
    _reject(_v1([_op("b", "helix", origin=[0, 0, 0], height=20, radius_start=10, radius_end=10, turns=65,
                     tube_radius=2.0)], "b"), "turns must be")
    _reject(_v1([_op("b", "helix", origin=[0, 0, 0], height=20, radius_start=10, radius_end=10, turns=4,
                     tube_radius=0.5)], "b"), "tube_radius must be")
    _reject(_v1([_op("b", "drafted_extrude", origin=[0, 0, 0], plane="xz", direction=1, depth=5,
                     draft_angle=45, loops=SQUARE)], "b"), "plane xy")
    _reject(_v1([_op("b", "drafted_extrude", origin=[0, 0, 0], plane="xy", direction=1, depth=5,
                     draft_angle=46, loops=SQUARE)], "b"), "draft_angle must be")
    _reject(_v1([_op("b", "cone", origin=[0, 0, 0], radius_base=6, radius_top=2, height=10, angle=90, axis="q")], "b"),
            "Axis must be")


def test_validator_accepts_parameter_expressions_on_new_kinds():
    recipe = _v1([
        _op("b", "cone", origin=[0, 0, 0], radius_base="h/2", radius_top=2, height="h", angle="a", axis="z"),
    ], "b")
    recipe["parameters"] = {"h": {"value": 20, "min": 5, "max": 40}, "a": {"value": 90, "min": 10, "max": 350}}
    _, resolved = validate_recipe(recipe)
    assert resolved[0]["radius_base"] == 10 and resolved[0]["angle"] == 90


def test_v2_wrapper_accepts_new_kinds():
    from doodle_to_cad.construction_recipe import validate_v2
    recipe = {
        "version": 2, "units": "mm", "name": "ring", "parameters": {},
        "operations": [{**_op("b", "torus", origin=[0, 0, 0], bend_radius=8, radius=2, angle=360, axis="z"),
                        "frame": "world", "depends_on": [], "evidence": ["e1"]}],
        "output": "b", "frames": {"world": {"origin": [0, 0, 0], "x": "width", "y": "depth", "z": "height"}},
        "bodies": [{"id": "part", "output": "b"}],
        "evidence": {"observed": [{"id": "e1", "text": "Ring drawn in all three views."}],
                     "inferred": [], "assumptions": [], "unresolved": []},
        "constraints": [],
    }
    validate_v2(recipe)
