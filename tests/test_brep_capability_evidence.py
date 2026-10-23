"""Issue #82: evidence integrity and non-vacuous change/preservation observations.

No live model, worker, service or network needed. Optional analysis dependency:
uv pip install -r docs/brep/issue-82-capabilities/requirements-analysis.txt
"""
import importlib.util
import json
from pathlib import Path
import shutil
import sys

import pytest

pytest.importorskip('scipy',reason='Install issue-82 requirements-analysis.txt for mesh sections')
ROOT=Path(__file__).resolve().parents[1]
HERE=ROOT/'docs/brep/issue-82-capabilities'
sys.path.insert(0,str(HERE))
# Unique module names avoid colliding with other benchmark audit modules.
def module(name,filename):
    spec=importlib.util.spec_from_file_location(name,HERE/filename)
    value=importlib.util.module_from_spec(spec);spec.loader.exec_module(value);return value

audit82=module('capability_audit82','audit.py')
measure82=module('capability_measure82','measure.py')
sys.path.remove(str(HERE))


def test_published_evidence_is_complete_and_recomputes():
    assert audit82.check()['cases']==8


def test_unchanged_model_does_not_satisfy_requested_edit():
    run=HERE/'evidence/run-005'
    for name in json.loads((run/'plan.json').read_text())['cases']:
        initial=measure82.observe(name,run/name/'01-initial/model.stl')
        edited=json.loads((run/name/'02-edited/model.recipe.json').read_text())
        checks=measure82.compare(initial,measure82.expected(name,edited))
        assert not all(v['within_tolerance'] for v in checks.values()),name


def test_geometric_preservation_probe_rejects_changed_outside_width(tmp_path):
    import trimesh
    run=HERE/'evidence/run-005/fillet'
    mesh=trimesh.load(run/'02-edited/model.stl',force='mesh');mesh.apply_scale([1.1,1,1])
    wrong=tmp_path/'widened.stl';mesh.export(wrong)
    obs=measure82.observe('fillet',wrong)
    expected=measure82.expected('fillet',json.loads((run/'02-edited/model.recipe.json').read_text()))
    assert not measure82.compare(obs,expected)['outside_x']['within_tolerance']


@pytest.mark.parametrize('path,mutation',[
    ('evidence/run-005/summary.json','corrupt'),
    ('evidence/run-005/fillet/02-edited/model.stl','delete'),
    ('evidence/run-005/fillet/02-edited/model.recipe.json','corrupt'),
    ('evidence/run-005/fillet/review.png','corrupt'),
])
def test_gate_rejects_artifact_loss_or_drift(tmp_path,path,mutation):
    root=tmp_path/'pack';shutil.copytree(HERE,root,ignore=shutil.ignore_patterns('__pycache__'))
    target=root/path
    if mutation=='delete':target.unlink()
    else:target.write_bytes(b'planted corruption')
    with pytest.raises(AssertionError,match='seal mismatch'):audit82.check(root,recompute=False)


def test_resealed_summary_tamper_is_not_accepted(tmp_path):
    root=tmp_path/'pack';shutil.copytree(HERE,root,ignore=shutil.ignore_patterns('__pycache__'))
    p=root/'evidence/run-005/summary.json';d=json.loads(p.read_text())
    d['fillet']['preservation']['outside_x']['after']=999;p.write_text(json.dumps(d))
    (root/'MANIFEST.json').write_text(json.dumps(audit82.seal(root)))
    with pytest.raises(AssertionError,match='summary disagrees'):audit82.check(root,recompute=False)
