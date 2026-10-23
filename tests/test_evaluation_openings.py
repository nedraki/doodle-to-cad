"""Issue #62: genus floor — rendered openings must be true through-openings.

Unit tests for the decision helper plus integration tests on REAL meshes built
by OpenSCAD: a 3-hole through-plate must pass and a blind-pocket plate that
renders identically in the front view must be rejected. Together they prove
the checker fires on the defect and stays quiet on the good part.
"""
import pytest

from doodle_to_cad.evaluation import openings_through_check, evaluate_candidate
from doodle_to_cad.openscad import available, run, mesh_health
from doodle_to_cad.config import Settings


def _health(holes, watertight=True, components=1):
    return {"watertight": watertight, "components": components, "triangles": 200,
            "through_holes": holes, "extents_mm": [60, 4, 40], "volume_mm3": 9000}


class TestOpeningsThroughCheck:
    def test_blind_pockets_rejected(self):
        ok, msg = openings_through_check(_health(0), expected=3, best_direction="front", strict=True)
        assert ok is False
        assert "blind pockets" in msg and "3 openings" in msg

    def test_true_through_holes_pass(self):
        ok, msg = openings_through_check(_health(3), expected=3, best_direction="front", strict=True)
        assert ok is True and msg == ""

    def test_extra_holes_pass(self):
        ok, _ = openings_through_check(_health(4), expected=3, best_direction="front", strict=True)
        assert ok is True

    def test_non_strict_skips(self):
        ok, _ = openings_through_check(_health(0), expected=3, best_direction="front", strict=False)
        assert ok is True

    def test_missing_genus_data_skips(self):
        health = _health(0); health["through_holes"] = None
        ok, _ = openings_through_check(health, expected=3, best_direction="front", strict=True)
        assert ok is True

    def test_no_openings_demanded_skips(self):
        ok, _ = openings_through_check(_health(0), expected=0, best_direction="front", strict=True)
        assert ok is True

    def test_multi_component_skips(self):
        ok, _ = openings_through_check(_health(0, components=2), expected=3, best_direction="front", strict=True)
        assert ok is True

    def test_non_watertight_skips(self):
        ok, _ = openings_through_check(_health(0, watertight=False), expected=3, best_direction="front", strict=True)
        assert ok is True

    def test_single_opening_pluralization(self):
        ok, msg = openings_through_check(_health(0), expected=1, best_direction="top", strict=True)
        assert ok is False and "1 opening" in msg and "0 true through-hole" in msg


PLATE = """
plate = 3;
module through_holes() {{ {cutters} }}
difference() {{
    cube([60, 4, 40], center = true);
    through_holes();
}}
"""
THROUGH = PLATE.format(cutters="\n    ".join(
    f'translate([{x}, 0, 0]) rotate([90, 0, 0]) cylinder(h = 6, r = 4, center = true);'
    for x in (-20, 0, 20)))
POCKETS = PLATE.format(cutters="\n    ".join(
    f'translate([{x}, -1.5, 0]) rotate([90, 0, 0]) cylinder(h = 3, r = 4, center = true);'
    for x in (-20, 0, 20)))


def _build(tmp_path, name, scad_text):
    settings = Settings()
    if not available(settings.openscad_bin):
        pytest.skip("openscad binary not available")
    src = tmp_path / f"{name}.scad"; src.write_text(scad_text)
    ok, log = run([settings.openscad_bin, "-o", f"{name}.stl", src.name], cwd=tmp_path)
    assert ok and (tmp_path / f"{name}.stl").is_file(), log
    return tmp_path / f"{name}.stl"


def _evaluate(stl):
    import numpy as np
    image = np.full((240, 360, 3), 255, dtype=np.uint8)
    import cv2
    cv2.circle(image, (90, 120), 15, (0, 0, 0), 2)
    cv2.circle(image, (180, 120), 15, (0, 0, 0), 2)
    cv2.circle(image, (270, 120), 15, (0, 0, 0), 2)
    cv2.circle(image, (180, 120), 35, (0, 0, 0), 2)
    ok, buf = cv2.imencode(".png", image)
    source = buf.tobytes()
    health = mesh_health(stl)
    ev = evaluate_candidate(stl=stl, health=health, scad="", views={}, source=source,
                            evidence={"closed_internal_profile_count": 3, "view_geometry": []},
                            spec={}, target_dimension="", strict=True)
    return ev, health


class TestGenusFloorEndToEnd:
    """End-to-end through evaluate_candidate: pocket plate rejected, through
    plate accepted on the same evidence — the checker discriminates real
    topology, not fixtures."""

    def test_blind_pocket_plate_rejected(self, tmp_path):
        stl = _build(tmp_path, "pockets", POCKETS)
        ev, health = _evaluate(stl)
        assert health["watertight"] and health["through_holes"] == 0
        assert ev["mandatory_gates"]["openings_through"] is False
        assert any("blind pockets" in f for f in ev["failures"])
        assert ev["accepted"] is False

    def test_through_hole_plate_passes_gate(self, tmp_path):
        stl = _build(tmp_path, "through", THROUGH)
        ev, health = _evaluate(stl)
        assert health["watertight"] and health["through_holes"] == 3
        assert ev["mandatory_gates"]["openings_through"] is True
        assert not any("blind pockets" in f for f in ev["failures"])
