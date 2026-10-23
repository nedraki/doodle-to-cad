import json
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import pytest
from fastapi import HTTPException
from doodle_to_cad import revisions


def setup_run(tmp_path):
    out = tmp_path / 'abcdef123456';out.mkdir()
    recipe = json.loads(Path('benchmarks/brep-shells/reference.recipe.json').read_text())
    recipe['parameters']['width']={'value':60,'min':40,'max':80,'label':'Outer width'}
    recipe['operations'][0]['size'][0]='width'
    (out/'model.recipe.json').write_text(json.dumps(recipe))
    result = {'id': out.name, 'backend': 'usd-brep', 'success': True,
              'evaluation': {'status': 'passed'}, 'files': {'source': '/results/'+out.name+'/model.recipe.json', 'stl': 'original.stl'}}
    (out/'result.json').write_text(json.dumps(result))
    return out


def builder(out, recipe, updates):
    from doodle_to_cad.brep_recipe import validate_recipe, recipe_params
    recipe, _ = validate_recipe(recipe, updates)
    import uuid
    directory=out/uuid.uuid4().hex;directory.mkdir()
    (directory/'recipe.json').write_text(json.dumps(recipe))
    url='/results/'+out.name+'/'+directory.name
    return {'ok':True,'source':url+'/recipe.json','stl':url+'/model.stl',
            'usd':url+'/model.usda','views':{},'params':recipe_params(recipe),
            'build':{'status':'passed'},'diagnostics':{'watertight':True}}


def test_two_edits_keep_reload_and_original_unchanged(tmp_path):
    out=setup_run(tmp_path);original=(out/'result.json').read_bytes()
    one=revisions.preview(out,{'parent_id':'original','selection_version':0,'updates':{'thickness':3}},builder)
    assert revisions.selected_result(out)['revision']['id']=='original'
    two=revisions.preview(out,{'parent_id':one['revision']['id'],'selection_version':0,'updates':{'width':70}},builder)
    selected=revisions.keep(out,{'revision_id':two['revision']['id'],'selection_version':0})
    assert revisions.selected_result(out)==selected
    assert selected['revision']['parent_id']==one['revision']['id']
    store=revisions.read_store(out)
    assert json.loads(store['revisions'][two['revision']['id']]['source_text'])['parameters']['thickness']['value']==3
    assert json.loads(store['revisions'][two['revision']['id']]['source_text'])['parameters']['width']['value']==70
    assert selected['evaluation']['status']=='unverified'
    assert selected['files']==two['files'] and selected['original_files']['stl']=='original.stl'
    assert (out/'result.json').read_bytes()==original


def test_failed_preview_and_conflicting_keep_preserve_selection(tmp_path):
    out=setup_run(tmp_path)
    candidate=revisions.preview(out,{'parent_id':'original','selection_version':0,'updates':{'thickness':3}},builder)
    saved=revisions.keep(out,{'revision_id':candidate['revision']['id'],'selection_version':0})
    with pytest.raises(HTTPException) as error:
        revisions.keep(out,{'revision_id':'original','selection_version':0})
    assert error.value.status_code==409
    def failure(*args):raise ValueError('bad shell')
    with pytest.raises(ValueError):revisions.preview(out,{'parent_id':candidate['revision']['id'],'selection_version':1,'updates':{}},failure)
    assert revisions.selected_result(out)==saved


def test_selection_changes_during_build_cannot_publish_candidate(tmp_path):
    out=setup_run(tmp_path)
    def racing_builder(*args):
        revisions.keep(out,{'revision_id':'original','selection_version':0})
        return builder(*args)
    with pytest.raises(HTTPException) as error:
        revisions.preview(out,{'parent_id':'original','selection_version':0,'updates':{}},racing_builder)
    assert error.value.status_code==409
    assert len(revisions.read_store(out)['revisions'])==1


def test_concurrent_keep_has_one_winner(tmp_path):
    out=setup_run(tmp_path)
    def save(_):
        try:revisions.keep(out,{'revision_id':'original','selection_version':0});return 200
        except HTTPException as e:return e.status_code
    with ThreadPoolExecutor(max_workers=2) as executor:
        assert sorted(executor.map(save,range(2)))==[200,409]


def test_unknown_revision_and_invalid_contract(tmp_path):
    out=setup_run(tmp_path)
    with pytest.raises(HTTPException) as error:revisions.keep(out,{'revision_id':'../../other','selection_version':0})
    assert error.value.status_code==404
    with pytest.raises(HTTPException):revisions.preview(out,{'updates':{}},builder)
