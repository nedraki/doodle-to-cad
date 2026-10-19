"""Issue #60 routing rules: deterministic backend recommendation."""
import json
from pathlib import Path

from doodle_to_cad.backend_router import route, scan_kernel_history, image_sha256


def ev(views=1, profiles=0, circular=0):
    shapes = [{"circularity": 0.9} for _ in range(circular)]
    return {"view_group_count": views, "closed_internal_profile_count": profiles,
            "closed_internal_profiles": shapes}


def test_kernel_history_beats_everything():
    r = route(ev(views=1), notes="fillet the edges", dimension="60", kernel_history_hit=True)
    assert r["backend"] == "openscad" and r["rule"] == "K"


def test_fillet_notes_favor_usd_brep():
    for note in ["fillet the top edges", "chamfer it", "hollow shell tray", "loft between circles"]:
        r = route(ev(views=1), notes=note)
        assert r["backend"] == "usd-brep" and r["rule"] == "F", note


def test_multi_view_favors_openscad():
    r = route(ev(views=2), notes="grille", dimension="100")
    assert r["backend"] == "openscad" and r["rule"] == "V"
    assert any("24/40" in item["text"] for item in r["rationale"])


def test_circular_pattern_heavy_favors_openscad_until_kernel_fixed():
    r = route(ev(views=1, circular=6), dimension="60")
    assert r["backend"] == "openscad" and r["rule"] == "C"


def test_single_view_with_dimension_favors_usd_brep():
    r = route(ev(views=1), dimension="60")
    assert r["backend"] == "usd-brep" and r["rule"] == "D"


def test_default_is_the_incumbent():
    r = route(ev(views=1))
    assert r["backend"] == "openscad" and r["rule"] == "-"


def test_priority_order_f_before_v_before_c_before_d():
    # F beats V (a fillet request on a 2-view drawing still goes to the kernel that has fillet)
    assert route(ev(views=2), notes="chamfer")["rule"] == "F"
    # V beats D
    assert route(ev(views=3), dimension="50")["rule"] == "V"
    # C beats D (kernel-prone circular rows even with a dimension)
    assert route(ev(views=1, circular=8), dimension="50")["rule"] == "C"


def test_every_recommendation_is_explained():
    for r in [route(ev()), route(ev(views=2)), route(ev(), notes="fillet"),
              route(ev(views=1, circular=7)), route(ev(), dimension="10"),
              route(ev(), kernel_history_hit=True)]:
        assert r["rationale"] and all(item["rule"] and item["text"] for item in r["rationale"])
        assert r["backend"] in {"openscad", "usd-brep"}


def test_signals_are_recorded_for_telemetry():
    r = route(ev(views=2, circular=3), notes="fillet", dimension="50")
    assert r["signals"] == {"view_group_count": 2, "closed_internal_profile_count": 0,
                            "circular_profile_count": 3, "notes_keywords": "yes",
                            "dimension_given": True, "kernel_history_hit": False}


def _write_kernel_history(tmp_path, image_bytes, code, message):
    out = tmp_path / "run1"
    out.mkdir()
    (out / "input.png").write_bytes(image_bytes)
    (out / "job.json").write_text(json.dumps(
        {"job_id": "run1", "status": "error", "stage": "failed",
         "error": {"code": code, "message": message}}))


def test_history_scan_matches_same_image_and_kernel_code(tmp_path):
    img = b"\x89PNG fake"
    _write_kernel_history(tmp_path, img, "kernel_unavailable", "boom")
    assert scan_kernel_history(tmp_path, image_sha256(img)) is True


def test_history_scan_ignores_non_kernel_errors(tmp_path):
    img = b"\x89PNG fake"
    _write_kernel_history(tmp_path, img, "build_failed", "Expected one connected part")
    assert scan_kernel_history(tmp_path, image_sha256(img)) is False


def test_history_scan_ignores_other_drawings(tmp_path):
    _write_kernel_history(tmp_path, b"\x89PNG other", "kernel_unavailable", "boom")
    assert scan_kernel_history(tmp_path, image_sha256(b"\x89PNG fake")) is False


def test_history_scan_fires_on_raw_signatures_before_reclassification(tmp_path):
    img = b"\x89PNG fake"
    _write_kernel_history(tmp_path, img, "build_failed", "No module named '_omni_solid'")
    assert scan_kernel_history(tmp_path, image_sha256(img)) is True


def test_frozen_curved_handle_class_routes_away_from_the_kernel():
    # The 3 frozen crash rows were single-object curved handles -> C or V rules,
    # never D/F, until the kernel defect is fixed upstream.
    r = route(ev(views=1, circular=7))
    assert r["backend"] == "openscad" and r["rule"] == "C"
