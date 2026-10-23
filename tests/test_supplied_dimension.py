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


def test_live_trial_uses_plan_dimension_without_changing_overall(tmp_path, monkeypatch):
    """Exercise the actual async call path, not a source-code string assertion."""
    import asyncio
    import json
    from types import SimpleNamespace
    import trimesh
    from doodle_to_cad import config, evaluation

    run = tmp_path/'results'/'trial'; run.mkdir(parents=True)
    mesh = trimesh.creation.box(extents=[118.5, 30, 20]); mesh.export(run/'model.stl')
    measured = eb._measure_stl(run/'model.stl')
    refs = tmp_path/'references'; refs.mkdir()
    (refs/'reference-measurements.json').write_text(json.dumps({'case':measured}))
    (tmp_path/'drawing.png').write_bytes(b'fixture')
    (run/'front.png').write_bytes(b'fixture')
    (run/'result.json').write_text(json.dumps({'geometry':{'fixture':True}, 'files':{'stl':'/results/trial/model.stl','views':{'front':'/results/trial/front.png'}}}))
    monkeypatch.setattr(eb, 'ROOT', tmp_path)
    monkeypatch.setattr(config, 'settings', SimpleNamespace(results_dir=tmp_path/'results'))
    monkeypatch.setattr(eb, '_ENV_STATIC', {'tested_commit':'fixture'})
    monkeypatch.setattr(evaluation, 'projection_scores', lambda *a: ({'front':1.0},{}))
    class Response:
        status_code = 200
        def __init__(self, data): self.data = data
        def json(self): return self.data
        def raise_for_status(self): pass
    class Client:
        async def post(self, url, **kwargs):
            assert kwargs['data']['dimension'] == '120'
            return Response({'job_id':'trial'})
        async def get(self, url):
            return Response({'status':'done'} if url.startswith('/api/generate/') else {'params':[]})
    plan = {'_plan_dir':str(tmp_path), 'infrastructure':{'poll_timeout_seconds':10},
            'tolerances':{'supplied_dimension_mm':1.0,'projection_similarity_min':.45}}
    item = {'id':'case','drawing':'drawing.png','notes':'','dimension':'120','primary_view':'front'}
    row = asyncio.run(eb._run_trial(Client(), plan, item, 'openscad', 1, tmp_path/'out', asyncio.Semaphore(1)))
    assert row['checks']['overall_pass'] is True
    assert row['checks']['supplied_dimension_pass'] is False
    saved = json.loads((tmp_path/'out/case/openscad/trial-01/row.json').read_text())
    assert saved['checks'] == row['checks']


def test_measurement_error_with_reference_still_records_dimension_failure():
    checks, _ = eb.reference_checks({'measure_error':'invalid STL'}, measurement([120,30,20]), 120)
    assert checks['supplied_dimension_pass'] is False
    assert checks['extents_pass'] is False
    assert checks['volume_pass'] is False
    assert checks['build_success'] is False
