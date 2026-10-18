import copy
import json
import os
from pathlib import Path

import pytest

from doodle_to_cad.brep import build_recipe, worker_available
from doodle_to_cad.brep_recipe import validate_recipe
from doodle_to_cad.construction_recipe import migrate_v1

ROOT = Path(__file__).resolve().parents[1]

def fixture(name='wheel'):
    return json.loads((ROOT / 'benchmarks/brep-v2' / f'{name}.json').read_text())


def test_migration_preserves_native_geometry_and_metadata():
    old = json.loads((ROOT / 'benchmarks/brep/bracket.json').read_text())
    original = copy.deepcopy(old)
    new = migrate_v1(old)
    assert old == original
    assert new['parameters'] == old['parameters']
    assert validate_recipe(new)[1] == validate_recipe(old)[1]
    changed, resolved = validate_recipe(new, {'hole1_width': 12})
    assert changed['parameters']['hole1_width']['value'] == 12
    assert resolved == validate_recipe(old, {'hole1_width': 12})[1]
    assert changed['frames'] == new['frames']
    assert changed['evidence'] == new['evidence']


@pytest.mark.parametrize('case,message', [
    ('operation','Unsupported operation'), ('dimension','positive'),
    ('cycle','dependency cycle'), ('unresolved','Resolve build values'),
    ('expression','Dimensions allow'), ('frame','canonical world frame'),
    ('evidence','unknown evidence'), ('body','Declared body'),
])
def test_invalid_fixtures(case, message):
    recipe=json.loads((ROOT/'benchmarks/brep-v2/invalid'/f'{case}.json').read_text())
    with pytest.raises(ValueError, match=message):
        validate_recipe(recipe)


@pytest.mark.skipif(not worker_available(), reason='Isolated worker not configured')
def test_wheel_connections_survive_radius_edit_and_reject_gap(tmp_path):
    wheel=fixture()
    base=build_recipe(tmp_path, wheel)
    changed=build_recipe(tmp_path, wheel, {'radius':80})
    for result,diameter in [(base,120),(changed,160)]:
        assert result['build']['source_format']=='brep-recipe-v2'
        assert result['build']['measurements']['components']==1
        assert result['diagnostics']['extents_mm']==pytest.approx([diameter,diameter,8])
        assert len(result['diagnostics']['connections'])==8
        assert all(c['passed'] and c['overlap_mm3']>=1 for c in result['diagnostics']['connections'])
    broken=copy.deepcopy(wheel)
    next(op for op in broken['operations'] if op['id']=='east')['size'][0]=5
    with pytest.raises(ValueError,match='east_rim: required connection failed'):
        build_recipe(tmp_path,broken)
    # A short spoke is still attached to the hub. The whole mesh can remain one
    # component through other spokes, so component count alone is not enough.
    assert len(list(tmp_path.glob('brep-*')))==2


@pytest.mark.skipif(not worker_available(), reason='Isolated worker not configured')
def test_existing_v1_result_and_migrated_bookend_edit(tmp_path):
    old=json.loads((ROOT/'benchmarks/brep/bracket.json').read_text())
    base=build_recipe(tmp_path,old)
    original=tmp_path/base['source'].split('/')[-2]/'model.recipe.json'
    before=original.read_bytes()
    updated=build_recipe(tmp_path,json.loads(before),{'hole1_width':12})
    migrated=build_recipe(tmp_path,migrate_v1(json.loads(before)),{'hole1_width':12})
    assert original.read_bytes()==before
    assert updated['diagnostics']['solid_volume_mm3']==pytest.approx(migrated['diagnostics']['solid_volume_mm3'])
    assert updated['params']==migrated['params']
    assert updated['build']['source_format']=='brep-recipe-v1'
    assert migrated['build']['source_format']=='brep-recipe-v2'


@pytest.mark.skipif(not worker_available(), reason='Isolated worker not configured')
def test_later_cut_cannot_remove_a_required_connection(tmp_path):
    wheel=fixture()
    wheel['operations'] += [
        dict(id='gap',kind='box',origin=[52,-5,-1],size=[6,10,10],frame='world',depends_on=[],evidence=[]),
        dict(id='cut_gap',kind='difference',left='join4',right='gap',frame='world',depends_on=['join4','gap'],evidence=[]),
    ]
    wheel['output']='cut_gap'
    wheel['bodies'][0]['output']='cut_gap'
    with pytest.raises(ValueError,match='east_rim: required connection failed'):
        build_recipe(tmp_path,wheel)
    assert not list(tmp_path.glob('brep-*'))
