"""Exercise the live harness comparison; no CAD renderer required."""
import importlib.util
from pathlib import Path

import pytest

spec = importlib.util.spec_from_file_location("evaluate_brep_dimension", Path(__file__).resolve().parents[1] / "scripts/evaluate_brep.py")
eb = importlib.util.module_from_spec(spec)
spec.loader.exec_module(eb)


def measurement(extents):
    return dict(extents_mm=extents, watertight=True, components=1, genus=0, volume_mm3=1000)


@pytest.mark.parametrize("extent,expected", [(119, True), (118.5, False), (121.5, False), (121, True), (120, True)])
def test_supplied_dimension_boundary(extent, expected):
    checks, _ = eb.reference_checks(measurement([40, extent, 30]), {}, "120")
    assert checks['supplied_dimension_pass'] is expected


def test_separate_from_reference_and_overall():
    ref = measurement([100, 40, 30])
    checks, _ = eb.reference_checks(ref, ref, 120)
    checks['fidelity_pass'] = True
    assert checks['extents_pass'] is True
    assert checks['supplied_dimension_pass'] is False
    assert eb.overall_checks(checks) is True
    checks, _ = eb.reference_checks(measurement([120, 40, 30]), ref, 120)
    assert checks['extents_pass'] is False
    assert checks['supplied_dimension_pass'] is True
    assert eb.overall_checks(checks) is False


@pytest.mark.parametrize('extents', [[], [120], [120, 40], [120, 40, 30, 20], [120, float('nan'), 30], [120, float('inf'), 30], [120, -1, 30], [True, 120, 30]])
def test_invalid_measurement_fails_closed(extents):
    assert eb.reference_checks(measurement(extents), {}, 120)[0]['supplied_dimension_pass'] is False


@pytest.mark.parametrize('target', [True, -1, 0, float('nan'), float('inf'), 'abc'])
def test_invalid_plan_dimension_rejected(target):
    with pytest.raises((ValueError, TypeError)):
        eb.reference_checks(None, {}, target)


def test_missing_dimension_and_missing_mesh():
    checks, na = eb.reference_checks(measurement([120, 40, 30]), {})
    assert 'supplied_dimension_pass' not in checks
    assert 'supplied_dimension' in na
    assert eb.reference_checks(None, {}, 120)[0]['supplied_dimension_pass'] is False


@pytest.mark.parametrize('tolerance', [0, -1, float('nan'), float('inf'), True])
def test_invalid_tolerance_rejected(tolerance):
    with pytest.raises(ValueError):
        eb.reference_checks(None, {}, 120, tolerance)
