"""Issue #81 evaluator-validation gate (bench-eval).

Two claims, each proven from retained artifacts or freshly compiled fixtures:

1. The evaluator's checks detect planted defects with known answers, and
   detect them ONLY with the check that was declared (fixtures/*.scad).
2. Some geometry checks are structurally blind: they pass moved and original
   openings with identical scores (opening position insensitivity), and the hidden-requirement fixture (EV-1) shows
   a policy-compliant model can never pass a reference-only dimension.

The gate freezes today's verified behaviour. If a product fix changes any of
these numbers (for the better), the matching test fails on purpose and the
CASES.json status must be re-audited. OpenSCAD binary required (docker shim).
"""
import importlib.util
import json
import shutil
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from doodle_to_cad.config import settings
from doodle_to_cad.openscad import available, render_views, run

pytestmark = pytest.mark.skipif(
    not available(settings.openscad_bin), reason="OpenSCAD binary not available")

FIX = ROOT / "docs" / "brep" / "bench-eval" / "fixtures"
RUNS = ROOT / "docs" / "brep" / "bench-final" / "runs"
CASES = json.loads((ROOT / "docs" / "brep" / "bench-eval" / "CASES.json").read_text())
REFS = json.loads((ROOT / "docs" / "brep" / "bench-final" / "references"
                   / "reference-measurements.json").read_text())
PLAN = json.loads((ROOT / "docs" / "brep" / "bench-final" / "TRIAL-PLAN.json").read_text())
ITEMS = {it["id"]: it for k, v in PLAN.items()
         if isinstance(v, list) and v and isinstance(v[0], dict) and "drawing" in v[0]
         for it in v}

GEOMETRY_FIXTURES = ["plate_5mm", "plate_3mm_policy", "plate_hole_moved",
                     "plate_hole_removed", "plate_blind_hole", "plate_split"]


@pytest.fixture(scope="module")
def eb():
    spec = importlib.util.spec_from_file_location(
        "evaluate_brep", ROOT / "scripts" / "evaluate_brep.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def built(eb, tmp_path_factory):
    """Compile every fixture once; measure + judge with the SHARED harness code."""
    out = tmp_path_factory.mktemp("bench-eval-fixtures")
    built = {}
    for name in GEOMETRY_FIXTURES:
        d = out / name
        d.mkdir()
        shutil.copyfile(FIX / f"{name}.scad", d / "f.scad")
        ok, log = run([settings.openscad_bin, "-o", "f.stl", "f.scad"], cwd=d, timeout=240)
        assert ok and (d / "f.stl").exists(), f"{name} failed to compile: {log[-400:]}"
        measurement = eb._measure_stl(d / "f.stl")
        checks, _na = eb.reference_checks(measurement, REFS["004_flat_mounting_plate"])
        built[name] = (measurement, checks)
    return built


def render_projection(eb_module, scad_src: Path, drawing: Path, evidence: dict,
                      primary_view: str, out_dir: Path) -> tuple[dict, dict]:
    from doodle_to_cad.evaluation import projection_scores
    out_dir.mkdir(parents=True, exist_ok=True)
    # the docker OpenSCAD shim mounts only the render cwd: keep the source inside it
    src = out_dir / "s.scad"
    shutil.copyfile(scad_src, src)
    views, log = render_views(src, out_dir, settings.openscad_bin)
    assert views, f"no views rendered: {log[-400:]}"
    scores, topology = projection_scores(
        drawing.read_bytes(), evidence, views, primary_view, "third-angle")
    return ({k: round(v, 4) for k, v in scores.items()},
            {k: (t.get("crop_internal_profiles"), t.get("rendered_internal_profiles"),
                 t.get("feature_position_fidelity")) for k, t in topology.items()})


# ---- 1. the evaluator can pass a known-correct answer ---------------------

def test_known_correct_answer_passes(built):
    m, c = built["plate_5mm"]
    assert c == {"build_success": True, "extents_pass": True,
                 "genus_pass": True, "volume_pass": True}
    assert m["genus"] == REFS["004_flat_mounting_plate"]["genus"] == 3


# ---- 2. planted defects, each detected by exactly its declared check ------

def test_planted_removed_opening_detected_by_genus_only(built):
    m, c = built["plate_hole_removed"]
    assert c["build_success"] is True and c["extents_pass"] is True \
        and c["volume_pass"] is True, "stability checks must stay green"
    assert c["genus_pass"] is False, "genus must catch the removed opening"
    assert m["genus"] == 2


def test_planted_blind_hole_detected_by_genus_only(built):
    m, c = built["plate_blind_hole"]
    assert c["build_success"] is True and c["extents_pass"] is True \
        and c["volume_pass"] is True, "blind hole adds back only 0.1% volume"
    assert c["genus_pass"] is False, "genus must catch the closed tunnel"
    assert m["genus"] == 2


def test_planted_disconnected_body_detected_by_build(built):
    m, c = built["plate_split"]
    assert c["build_success"] is False
    assert m["components"] == 2


# ---- 3. EV-1: hidden requirement — policy-compliant model cannot pass -----

def test_ev1_hidden_reference_thickness(built):
    """A model that obeys the frozen clarification policy (3 mm) on a case
    whose reference thickness (5 mm) exists nowhere the model can see:
    the visible-ink checks (build, genus) pass, the reference-only checks
    (extents, volume) fail for EVERY compliant model."""
    m, c = built["plate_3mm_policy"]
    assert c["build_success"] is True
    assert c["genus_pass"] is True, "visible-ink requirements are satisfiable"
    assert c["extents_pass"] is False and c["volume_pass"] is False
    # the requirement really is hidden per the frozen record:
    req = [r for r in CASES["cases"]["004_flat_mounting_plate"]["requirements"]
           if r["id"] == "thickness"][0]
    assert req.get("hidden_requirement") is True and req["source"] == "reference-only"


# ---- 4. structurally blind checks (frozen evidence of insensitivity) ------

def test_d1_geometry_checks_blind_to_opening_position(built):
    """A 20 mm hole move leaves extents/genus/volume byte-identical: the
    geometry checks alone cannot see opening position; the separate projection-position fixture below detects the move."""
    _, base = built["plate_5mm"]
    _, moved = built["plate_hole_moved"]
    assert base == moved, "geometry verdicts identical: position is invisible to them"


def test_ev4_refuted_the_bench_did_catch_the_wrong_part():
    """The v1 claim 'the product accepted a plate at 100.0' was a row mix-up.
    The bytes say: the accepted-100.0 openscad rows are shape-correct
    L-brackets, and the actual plate (usd-brep trial-01, [80,40,5]) was
    caught by BOTH the harness fidelity (front 0.35 < 0.45) and the product
    (accepted=False). Freeze that correct behaviour: if a future product
    change accepts the plate, this test fails and acceptance must be
    re-audited."""
    plate = json.loads((RUNS / "007_angle_bracket_holes" / "usd-brep" / "trial-01"
                        / "row.json").read_text())
    bracket = json.loads((RUNS / "007_angle_bracket_holes" / "openscad" / "trial-01"
                          / "row.json").read_text())
    assert plate["build"]["extents_mm"] == [80.0, 40.0, 5.0]  # flat plate
    assert plate["fidelity"]["pass"] is False
    assert plate["fidelity"]["scores"]["front"] < 0.45
    assert plate["product"]["accepted"] is False
    assert bracket["product"]["accepted"] is True and bracket["product"]["score"] == 100.0
    assert bracket["checks"]["genus_pass"] is True  # correct bracket topology


def test_ev7_fidelity_is_orientation_dependent_on_004():
    """Same part, opposite verdicts: openscad (plate on edge, holes facing
    front) passes fidelity; usd-brep (plate flat, holes facing up) fails
    with topology 'front expects 3, renders 0 / top expects 0, renders 3'.
    Freeze the defect so an orientation-normalization fix must break this
    test and re-label CASES.json EV-7 together."""
    occ = json.loads((RUNS / "004_flat_mounting_plate" / "openscad" / "trial-01"
                      / "row.json").read_text())
    ucb = json.loads((RUNS / "004_flat_mounting_plate" / "usd-brep" / "trial-01"
                      / "row.json").read_text())
    assert occ["fidelity"]["pass"] is True
    assert ucb["fidelity"]["pass"] is False
    topo = ucb["fidelity"]["topology"]
    assert topo["front"]["expected"] == 3 and topo["front"]["actual"] == 0
    assert topo["top"]["expected"] == 0 and topo["top"]["actual"] == 3


def test_planted_position_and_stated_thickness_detected(built, eb, tmp_path):
    """Use canonical projections of trusted geometry, not noisy ink labels.

    The existing move fixture is invisible to genus/extents/volume. A 20 mm
    move must exceed 0.1 of the normalized view while those checks stay green.
    Stating the 5 mm thickness makes the 3 mm fixture a real dimension defect,
    in contrast to the historical drawing where that requirement was hidden.
    """
    import numpy as np
    import trimesh
    from scripts.bench_orientation import render_mask, normalize_mask, opening_displacement
    masks = {}
    for name in ('plate_5mm', 'plate_hole_moved'):
        d = tmp_path / name; d.mkdir()
        shutil.copyfile(FIX / f'{name}.scad', d/'f.scad')
        ok, log = run([settings.openscad_bin, '-o', 'f.stl', 'f.scad'], cwd=d, timeout=240)
        assert ok, log
        mesh = trimesh.load_mesh(d/'f.stl')
        masks[name] = normalize_mask(render_mask(mesh, np.eye(3), 'top'))
    control = opening_displacement(masks['plate_5mm'], masks['plate_5mm'])
    defect = opening_displacement(masks['plate_5mm'], masks['plate_hole_moved'])
    assert control['max_nearest_center_shift'] == 0
    assert defect['expected_count'] == defect['actual_count'] == 3
    assert defect['max_nearest_center_shift'] > .1
    assert built['plate_5mm'][1] == built['plate_hole_moved'][1]
    assert built['plate_5mm'][1]['extents_pass'] is True
    assert built['plate_3mm_policy'][1]['extents_pass'] is False


# ---- 6. #102 supplied-dimension contract ----------------------------------
# A dimension the user actually gave must be honoured in the mesh within
# +/-1 mm. Reference-only dimensions are NOT part of this contract; they stay
# on the 2% extents check. Reported as a separate track from overall_pass.

def _meas(extents, watertight=True, components=1):
    return {"watertight": watertight, "components": components,
            "extents_mm": extents, "volume_mm3": 1000.0}

NO_GT = {"kind": "no_ground_truth"}


def _eb():
    import importlib.util
    from pathlib import Path as _P
    spec = importlib.util.spec_from_file_location(
        "evaluate_brep_102", _P(__file__).resolve().parents[1] / "scripts" / "evaluate_brep.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_supplied_dimension_honoured_within_1mm():
    eb = _eb()
    checks, na = eb.reference_checks(_meas([119.5, 60.0, 120.0]), NO_GT, supplied_dimension=120.0)
    assert checks["supplied_dimension_pass"] is True
    assert "supplied_dimension" not in na
    # boundary inclusive: exactly 1.0 mm off passes, 1.1 mm off fails (both sides)
    assert eb.reference_checks(_meas([119.0, 50.0, 100.0]), NO_GT, supplied_dimension=120.0)[0]["supplied_dimension_pass"] is True
    assert eb.reference_checks(_meas([118.9, 50.0, 100.0]), NO_GT, supplied_dimension=120.0)[0]["supplied_dimension_pass"] is False
    assert eb.reference_checks(_meas([121.0, 50.0, 100.0]), NO_GT, supplied_dimension=120.0)[0]["supplied_dimension_pass"] is True
    assert eb.reference_checks(_meas([121.1, 50.0, 100.0]), NO_GT, supplied_dimension=120.0)[0]["supplied_dimension_pass"] is False


def test_supplied_dimension_contract_is_independent_of_reference_checks():
    """A mesh that fails the reference-only extents check can still honour the
    supplied contract (and vice versa) - the two tracks never gate each other."""
    eb = _eb()
    ref = {"kind": "measured", "genus": 0, "extents_mm": [200.0, 200.0, 200.0], "volume_mm3": 1.0e6}
    checks, na = eb.reference_checks(_meas([119.9, 119.9, 120.0]), ref, supplied_dimension=120.0)
    assert checks["extents_pass"] is False       # reference-only expectation missed
    assert checks["supplied_dimension_pass"] is True  # user's number honoured


def test_supplied_dimension_na_and_failed_build():
    eb = _eb()
    # no dimension supplied -> not applicable (key absent, never a false failure)
    checks, na = eb.reference_checks(_meas([119.0, 60.0, 120.0]), NO_GT)
    assert "supplied_dimension_pass" not in checks
    assert "supplied_dimension" in na
    # build never happened -> contract cannot be honoured
    checks, _ = eb.reference_checks(None, NO_GT, supplied_dimension=120.0)
    assert checks["supplied_dimension_pass"] is False


def test_run_trial_wires_plan_dimension_and_plan_declares_tolerance():
    # The async behavioral call-path test is in test_supplied_dimension.py.
    plan = json.loads((ROOT / "docs" / "brep" / "bench-final" / "TRIAL-PLAN.json").read_text())
    assert plan["tolerances"]["supplied_dimension_mm"] == 1.0
    assert plan["pass_criteria"]["supplied_dimension_pass"]
    revisions = json.dumps(plan["plan_revisions"])
    assert "supplied_dimension" in revisions  # governance: declared via revision entry
