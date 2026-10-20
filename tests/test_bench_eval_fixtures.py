"""Issue #81 evaluator-validation gate (bench-eval).

Two claims, each proven from retained artifacts or freshly compiled fixtures:

1. The evaluator's checks detect planted defects with known answers, and
   detect them ONLY with the check that was declared (fixtures/*.scad).
2. Some checks are structurally blind: they pass a wrong part and a correct
   part with identical scores (EV-4 acceptance insensitivity; opening
   position insensitivity), and the hidden-requirement fixture (EV-1) shows
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
    geometry checks alone cannot see opening position; only the projection
    path can — and there the position fidelity does not react either."""
    _, base = built["plate_5mm"]
    _, moved = built["plate_hole_moved"]
    assert base == moved, "geometry verdicts identical: position is invisible to them"


def test_ev4_product_acceptance_cannot_distinguish_plate_from_bracket(eb, tmp_path):
    """The archived model.scad (a flat PLATE — the wrong part; notes + GT
    require an L-bracket) and the reviewed bracket fixture, judged through
    the same projection_scores call against the same drawing evidence,
    receive IDENTICAL scores. This is why the product scored the plate 100.
    Freeze: a future acceptance fix that can tell them apart must update
    CASES.json EV-4 to 'fixed' and this assertion together with it."""
    item = ITEMS["007_angle_bracket_holes"]
    drawing = ROOT / item["drawing"]
    result7 = json.loads((RUNS / "007_angle_bracket_holes" / "openscad"
                          / "trial-01" / "result.json").read_text())
    evidence = result7["geometry"]
    assert evidence, "frozen evidence must exist"

    archived_plate = RUNS / "007_angle_bracket_holes" / "openscad" / "trial-01" / "model.scad"
    plate_scores, plate_topo = render_projection(
        eb, archived_plate, drawing, evidence, item["primary_view"], tmp_path / "plate")
    bracket_scores, bracket_topo = render_projection(
        eb, FIX / "bracket_l_reviewed.scad", drawing, evidence,
        item["primary_view"], tmp_path / "bracket")

    assert plate_scores and all(v >= 0.9 for v in plate_scores.values()), \
        "reproduces the accepted-at-100 behaviour"
    assert plate_scores == bracket_scores, \
        f"insensitivity broken? plate={plate_scores} bracket={bracket_scores}"
    assert plate_topo == bracket_topo
