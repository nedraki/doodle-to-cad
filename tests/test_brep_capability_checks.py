"""Regression checks against independently retained meshes, including no-op edits."""
import importlib.util
import json
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parents[1] / 'docs/brep/bench-capabilities'

@pytest.fixture
def runner(monkeypatch):
    monkeypatch.syspath_prepend(str(HERE))
    spec = importlib.util.spec_from_file_location('capability_runner', HERE / 'build_capabilities.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

@pytest.mark.parametrize('index', [1, 2, 3, 4, 5])
def test_real_edit_passes_and_noop_fails(runner, index):
    case = runner.CASES[index]
    base = runner._build_recipe(case)
    edited = runner.edit_variants(case, base)
    initial = HERE / 'evidence' / case['id'] / 'initial/model.stl'
    final = HERE / 'evidence' / case['id'] / 'edited/model.stl'
    checks = runner.feature_checks(final, case, edited)
    assert all(c['pass'] for c in checks), checks
    assert not all(c['pass'] for c in runner.feature_checks(initial, case, edited))
    # A requested feature change does not license unrelated dimensional drift.
    protected = json.loads(json.dumps(edited))
    key = {1:'length', 2:'leg', 3:'rect', 4:'fillet_r', 5:'wall'}[index]
    protected['parameters'][key]['value'] += 1
    assert not all(c['pass'] for c in runner.feature_checks(final, case, protected))

def test_existing_run_refused_without_modification(runner, tmp_path, monkeypatch):
    marker = tmp_path / 'results.json'
    marker.write_text('retained')
    monkeypatch.setattr(sys, 'argv', ['runner', '--output', str(tmp_path)])
    with pytest.raises(FileExistsError):
        runner.main()
    assert marker.read_text() == 'retained'

def test_timeout_retained_and_attempt_cannot_be_replaced(runner, tmp_path, monkeypatch):
    monkeypatch.setattr(runner, 'OUT', tmp_path)
    def timeout(*args, **kwargs):
        raise runner.subprocess.TimeoutExpired('worker', 300, output=b'partial output', stderr=b'partial error')
    monkeypatch.setattr(runner.subprocess, 'run', timeout)
    result = runner.build({'input': 'retained'}, 'case/initial')
    assert result['worker_exit'] != 0
    assert (tmp_path/'case/initial/stdout.log').read_text() == 'partial output'
    assert (tmp_path/'case/initial/stderr.log').read_text() == 'partial error'
    with pytest.raises(FileExistsError):
        runner.build({}, 'case/initial')
    assert json.loads((tmp_path/'case/initial/model.recipe.json').read_text()) == {'input':'retained'}

def test_failed_cell_returns_nonzero_and_keeps_result(runner, tmp_path, monkeypatch):
    output = tmp_path / 'new-run'
    monkeypatch.setattr(sys, 'argv', ['runner', '--output', str(output)])
    monkeypatch.setattr(runner, 'CASES', [runner.CASES[0]])
    monkeypatch.setattr(runner, 'build', lambda *a: {'worker_exit': 1, 'construction_error': {'reason': 'guard'}})
    assert runner.main() == 1
    result = json.loads((output/'results.json').read_text())
    assert result['cases'][0]['initial']['status'] == 'failed'
    assert 'edit' not in result['cases'][0]
    assert (output/'plan.json').exists()
