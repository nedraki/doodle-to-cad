"""One registry of bench jobs shared by run_bench.py (build+measure) and
audit.py (recompute every claim from saved artifacts).

Expected values are derived from fixture parameter values by explicit rules,
never hand-picked. A planted-error job builds geometry with one parameter
deliberately wrong and asserts the checker fails.
"""
from __future__ import annotations

import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
FIXTURES = HERE / "fixtures"


def fixture_params(name):
    doc = json.loads((FIXTURES / f"{name}.json").read_text())
    return {k: v["value"] for k, v in doc["parameters"].items()}


def _fillet_job():
    p = fixture_params("fillet_block")
    radius = p["block_width"] / 4  # derived: width/4, same rule as the recipe
    return {
        "name": "fillet_block", "category": "feature", "fixture": "fillet_block",
        "overrides": {}, "expected_fail": False,
        "checker": "verify_fillet",
        "args": [p["block_width"], p["block_depth"], p["block_height"], radius],
        "extra": {"fillet_radius_rule": "block_width / 4", "expected_face_delta": 4},
    }


def _chamfer_job():
    p = fixture_params("chamfer_box")
    return {
        "name": "chamfer_box", "category": "feature", "fixture": "chamfer_box",
        "overrides": {}, "expected_fail": False,
        "checker": "verify_chamfer",
        "args": [p["body_width"], p["body_depth"], p["body_height"], p["chamfer_radius"]],
    }


def _chamfer_planted_job():
    p = fixture_params("chamfer_box")
    built_radius = 1.0  # planted: geometry built at 1.0 mm...
    return {
        "name": "chamfer_planted_wrong_radius", "category": "planted-error",
        "fixture": "chamfer_box", "overrides": {"chamfer_radius": built_radius},
        "expected_fail": True,
        "checker": "verify_chamfer",
        # ...but presented to the checker as the nominal 3 mm chamfer.
        "args": [p["body_width"], p["body_depth"], p["body_height"], p["chamfer_radius"]],
        "note": (f"Built with chamfer_radius={built_radius} mm, verified against the "
                 f"nominal {p['chamfer_radius']} mm fixture expectation. The checker "
                 "must fail; a checker that passes here is worthless."),
    }


def _arc_job(name, theta_mid):
    doc = json.loads((FIXTURES / f"{name}.json").read_text())
    op = next(o for o in doc["operations"] if o["kind"] == "arc_pipe")
    p = {k: v["value"] for k, v in doc["parameters"].items()}
    assert op["angle"] == 2 * theta_mid, "mid-angle must be half the sweep"
    return {
        "name": name, "category": "feature", "fixture": name,
        "overrides": {}, "expected_fail": False,
        "checker": "verify_arc_pipe",
        "args": [p["bend_radius"], p["tube_radius"], op["angle"], theta_mid],
    }


def _loft_job():
    p = fixture_params("loft_transition")
    return {
        "name": "loft_transition", "category": "feature", "fixture": "loft_transition",
        "overrides": {}, "expected_fail": False,
        "checker": "verify_loft",
        "args": [p["rect_width"], p["rect_depth"], p["circle_radius"], p["transition_height"]],
    }


def _shell_job():
    p = fixture_params("shell_tray")
    return {
        "name": "shell_tray", "category": "feature", "fixture": "shell_tray",
        "overrides": {}, "expected_fail": False,
        "checker": "verify_shell",
        "args": [p["tray_width"], p["tray_depth"], p["tray_height"], p["wall_thickness"]],
    }


def _probe(name, note):
    return {"name": name, "category": "regression-probe", "fixture": name,
            "overrides": {}, "expected_fail": False, "checker": None, "note": note}


JOBS = [
    _fillet_job(),
    _chamfer_job(),
    _chamfer_planted_job(),
    _arc_job("arc_pipe_quarter", 45),
    _arc_job("arc_pipe_half", 90),
    _loft_job(),
    _shell_job(),
    _probe("wheel_spokes",
           "Circular-pattern spoke union. Cross-ref issue #61 (usd_brep 1.0.0 "
           "tessellate _omni_solid defect on spoke/circular patterns): a kernel "
           "crash here is published data, never a hidden skip."),
    _probe("curved_handle",
           "arc_pipe + cylinder legs union: combination probe for pipe/boolean "
           "interaction on top of the plain arc_pipe fixtures."),
]

ARTIFACTS = HERE / "artifacts"
MEASUREMENTS = HERE / "measurements"
