"""Issue #67: view registration must not silently drop internal profiles.

A doodle opening is a small round STROKE RING. When the ring is drawn inside a
view group but not geometrically enclosed by the view outline (hook
elevations, stepped brackets — motor holder 103's right elevation proves it),
it sits at hierarchy depth 0/1 and the old depth>=2 registration rule dropped
it from every count, so no per-view gate could demand the lost openings.

These fixtures plant exactly that error: a synthetic sheet whose bottom-left
"hook elevation" carries two circles the old code counted nowhere.
"""
from __future__ import annotations

import cv2
import numpy as np
import pytest

from doodle_to_cad import evaluation as evaluation_module
from doodle_to_cad.evaluation import (_crop_internal_profile_count,
                                      assign_view_groups, evaluate_candidate,
                                      openings_through_check)
from doodle_to_cad.geometry import analyze_image

W, H = 1024, 768
INK = (0, 0, 0)


def _wobbly_circle(canvas, center, radius, thickness):
    """Deterministic hand-inked circle: two offset passes of a thick pen."""
    cv2.circle(canvas, center, radius, INK, thickness, lineType=cv2.LINE_8)
    cv2.circle(canvas, (center[0] + 1, center[1]), radius - 1, INK, 2, lineType=cv2.LINE_8)


def _hook_sheet() -> bytes:
    """Three-view sheet, motor-103 layout.

    view_A (top): closed bracket outline with TWO enclosed circles (the old
      depth>=2 rule counted these).
    view_B (lower left, the "hook elevation"): OPEN outline (a U-shape whose
      closed side faces away from the circles) with TWO circles inside the
      layout region — geometrically unenclosed islands. This is the planted
      error: the old registration counted 0 openings here.
    view_C (lower right): closed rectangle, no circles.
    """
    canvas = np.full((H, W, 3), 255, np.uint8)
    # view_A: closed bracket outline, upper middle.
    outline_a = np.array([[410, 50], [620, 50], [620, 285], [470, 285], [410, 230]], np.int32)
    cv2.polylines(canvas, [outline_a], True, INK, 4, lineType=cv2.LINE_8)
    _wobbly_circle(canvas, (470, 235), 12, 3)   # enclosed -> depth 2
    _wobbly_circle(canvas, (585, 90), 12, 3)    # enclosed -> depth 2
    # view_B: OPEN hook outline (left side open), lower middle.
    outline_b = np.array([[455, 420], [625, 420], [625, 515], [455, 515]], np.int32)
    cv2.polylines(canvas, [outline_b], False, INK, 9, lineType=cv2.LINE_8)
    _wobbly_circle(canvas, (510, 465), 12, 3)   # ORPHAN island -> depth 0/1
    _wobbly_circle(canvas, (580, 465), 12, 3)   # ORPHAN island -> depth 0/1
    # view_C: plain closed rectangle, lower right.
    cv2.rectangle(canvas, (780, 420), (1020, 515), INK, 4, lineType=cv2.LINE_8)
    ok, encoded = cv2.imencode(".png", canvas)
    assert ok
    return encoded.tobytes()


def _old_sheet_count(evidence) -> int:
    """Reproduce the pre-#67 sheet rule (depth>=2 only) from the evidence."""
    return sum(1 for s in evidence["closed_internal_profiles"] if s["hierarchy_depth"] >= 2)


def _old_crop_count(image: np.ndarray) -> int:
    """Reproduce the pre-#67 crop rule (depth==2 only)."""
    ink = cv2.threshold(cv2.cvtColor(image, cv2.COLOR_BGR2GRAY), 190, 255, cv2.THRESH_BINARY_INV)[1]
    ink = cv2.morphologyEx(ink, cv2.MORPH_CLOSE, np.ones((3, 3), np.uint8))
    contours, hierarchy = cv2.findContours(ink, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
    if not contours or hierarchy is None:
        return 0
    hierarchy = hierarchy[0]
    depths = []
    for i in range(len(contours)):
        depth, parent = 0, int(hierarchy[i][3])
        while parent >= 0:
            depth += 1
            parent = int(hierarchy[parent][3])
        depths.append(depth)
    return sum(1 for i, d in enumerate(depths)
               if d == 2 and cv2.contourArea(contours[i]) > ink.size * .0005)


@pytest.fixture(scope="module")
def sheet():
    data = _hook_sheet()
    evidence, _ = analyze_image(data)
    return data, evidence


class TestPlantedErrorFailsWithoutFix:
    def test_fixtures_reproduce_the_dropped_pair(self, sheet):
        _, evidence = sheet
        # The planted error: under the OLD depth>=2 rule the sheet registers
        # only the two enclosed circles; the hook elevation's pair is lost.
        assert _old_sheet_count(evidence) == 2
        orphans = [s for s in evidence["closed_internal_profiles"] if s.get("orphan_opening_ring")]
        assert len(orphans) == 2
        assert all(s["hierarchy_depth"] == 0 for s in orphans)

    def test_crop_gate_would_have_missed_them(self, sheet):
        data, evidence = sheet
        image = cv2.imdecode(np.frombuffer(data, np.uint8), cv2.IMREAD_COLOR)
        groups = assign_view_groups(evidence, "front", "third-angle")
        assert set(groups) == {"front", "top", "right"}
        hook_group = groups["front"]  # the open-outline view is the primary/front
        x, y, gw, gh = hook_group["bbox_normalized"]
        crop = image[int(y * H):int((y + gh) * H), int(x * W):int((x + gw) * W)]
        assert _old_crop_count(crop) == 0        # old rule: openings vanish
        assert _crop_internal_profile_count(crop) == 2  # fixed rule: both counted


class TestRegistrationCountsOpenings:
    def test_sheet_counts_all_four_circles(self, sheet):
        _, evidence = sheet
        assert evidence["closed_internal_profile_count"] == 4

    def test_per_view_geometry_assigns_two_per_circle_view(self, sheet):
        _, evidence = sheet
        per_view = {v["view_id"]: len(v["internal_profiles"]) for v in evidence["view_geometry"]}
        assert sorted(per_view.values()) == [0, 2, 2]

    def test_registered_crop_counts_sum_to_sheet_total(self, sheet):
        data, evidence = sheet
        image = cv2.imdecode(np.frombuffer(data, np.uint8), cv2.IMREAD_COLOR)
        groups = assign_view_groups(evidence, "front", "third-angle")
        total = 0
        for group in groups.values():
            x, y, gw, gh = group["bbox_normalized"]
            crop = image[int(y * H):int((y + gh) * H), int(x * W):int((x + gw) * W)]
            total += _crop_internal_profile_count(crop)
        assert total == evidence["closed_internal_profile_count"] == 4


def _run_eval(monkeypatch, *, crops_by_view, rendered_by_view, sheet_total, health=None):
    projections = {d: 0.9 for d in crops_by_view}
    topology = {d: {"crop_internal_profiles": c, "rendered_internal_profiles": rendered_by_view.get(d, 0)}
                for d, c in crops_by_view.items()}
    monkeypatch.setattr(evaluation_module, "projection_scores",
                        lambda *a, **k: (projections, topology))
    return evaluate_candidate(stl=None, health=health, scad="", views={}, source=b"",
                              evidence={"closed_internal_profile_count": sheet_total},
                              spec={}, target_dimension="", strict=True,
                              primary_view="front", projection_standard="third-angle")


def _health(holes):
    return {"watertight": True, "components": 1, "triangles": 200,
            "through_holes": holes, "extents_mm": [60, 60, 27], "volume_mm3": 9000}


class TestDemandedOpeningsGuard:
    def test_consistent_registration_demands_the_sum(self, monkeypatch):
        # Motor-103 after the fix: 2 openings in top + 2 in the hook elevation.
        ev = _run_eval(monkeypatch, crops_by_view={"front": 0, "top": 2, "right": 2},
                       rendered_by_view={"top": 2, "right": 2}, sheet_total=4,
                       health=_health(4))
        demanded = ev["demanded_openings"]
        assert demanded == {"total": 4, "per_view": {"front": 0, "top": 2, "right": 2},
                            "sheet_total": 4, "registration_gap": 0}
        assert ev["mandatory_gates"]["openings_through"] is True

    def test_mesh_with_two_of_four_bores_is_rejected(self, monkeypatch):
        # The exact #67 product defect: accepted at 95.8 with 2 of 4 bores.
        ev = _run_eval(monkeypatch, crops_by_view={"front": 0, "top": 2, "right": 2},
                       rendered_by_view={"top": 2}, sheet_total=4, health=_health(2))
        assert ev["accepted"] is False
        assert ev["mandatory_gates"]["openings_through"] is False
        assert any("4 openings" in f for f in ev["failures"])
        assert ev["demanded_openings"]["total"] == 4

    def test_single_view_sheet_is_a_measured_noop(self, monkeypatch):
        # Every frozen #34 row: openings in ONE view only -> total == best-view max.
        ev = _run_eval(monkeypatch, crops_by_view={"front": 4, "right": 0},
                       rendered_by_view={"front": 4}, sheet_total=4, health=_health(4))
        assert ev["demanded_openings"]["total"] == 4
        assert ev["mandatory_gates"]["features"] is True
        assert ev["mandatory_gates"]["openings_through"] is True

    def test_registration_gap_fails_safe_to_sheet_total(self, monkeypatch):
        # Crop detection that loses openings (gap > 1) must NOT excuse the mesh.
        ev = _run_eval(monkeypatch, crops_by_view={"front": 1},
                       rendered_by_view={"front": 1}, sheet_total=4, health=_health(1))
        assert ev["demanded_openings"]["registration_gap"] == 3
        assert ev["demanded_openings"]["total"] == 4
        assert ev["mandatory_gates"]["features"] is False
        assert ev["mandatory_gates"]["openings_through"] is False

    def test_one_profile_noise_does_not_escalate(self, monkeypatch):
        # A gap of exactly 1 (e.g. one marginal ring) stays with registered counts.
        ev = _run_eval(monkeypatch, crops_by_view={"front": 2},
                       rendered_by_view={"front": 2}, sheet_total=3, health=_health(2))
        assert ev["demanded_openings"]["registration_gap"] == 1
        assert ev["demanded_openings"]["total"] == 2
        assert ev["mandatory_gates"]["features"] is True

    def test_per_view_gate_catches_view_that_renders_nothing(self, monkeypatch):
        # Old best-view-max rule passed this: top satisfied the demand, the hook
        # elevation rendered nothing. Per-view comparison now fails it.
        ev = _run_eval(monkeypatch, crops_by_view={"top": 2, "right": 2},
                       rendered_by_view={"top": 2, "right": 0}, sheet_total=4,
                       health=_health(4))
        assert ev["mandatory_gates"]["features"] is False
        assert ev["mandatory_gates"]["openings_through"] is True  # genus is fine


class TestOpeningsCheckTotalDemand:
    def test_total_demand_across_views(self):
        ok, msg = openings_through_check(_health(2), expected=4, best_direction="right", strict=True)
        assert ok is False
        assert "4 openings" in msg and "registered views" in msg
