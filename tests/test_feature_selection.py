from copy import deepcopy
import json
import pytest
from fastapi import HTTPException
from doodle_to_cad.feature_selection import resolve,choose
from doodle_to_cad import revisions
from doodle_to_cad.brep import worker_available


def target():
 return {'id':'cutout1','label':'Cutout 1','rule':{'kind':'box_cutout','owner':'cut','cutter':'tool','expected_faces':4},'geometry':{'triangles':[]},'match_count':4}


def test_resolve_rule_not_raw_index_and_reject_changed_targets():
 t=target();saved={'rule':t['rule'],'label':t['label'],'selected_in_revision':'original'}
 result={'diagnostics':{'selection_catalog':{'targets':[t]}}}
 assert resolve(result,saved)['status']=='matched'
 changed=deepcopy(t);changed['rule']['expected_faces']=6
 result['diagnostics']['selection_catalog']['targets']=[changed]
 assert resolve(result,saved)['status']=='ambiguous'
 result['diagnostics']['selection_catalog']['targets']=[]
 assert resolve(result,saved)['status']=='lost'
 result['diagnostics']['selection_catalog']['unresolved']=[{'rule':t['rule'],'status':'ambiguous','reason':'split'}]
 assert resolve(result,saved)['status']=='ambiguous'


def test_selection_saved_with_revision_and_conflict_guard(tmp_path):
 out=tmp_path/'abc123';out.mkdir();t=target()
 r={'id':'abc123','backend':'usd-brep','files':{},'diagnostics':{'selection_catalog':{'targets':[t]}}}
 recipe=json.loads(open('benchmarks/brep-shells/reference.recipe.json').read())
 (out/'model.recipe.json').write_text(json.dumps(recipe));(out/'result.json').write_text(json.dumps(r))
 payload={'revision_id':'original','target_id':'cutout1','target_version':0,'selection_version':0}
 selected=choose(out,payload)
 assert selected['target_selection']['status']=='matched'
 assert selected['target_selection']['selected_in_revision']=='original'
 assert revisions.selected_result(out)['target_selection']==selected['target_selection']
 with pytest.raises(HTTPException) as e:choose(out,payload)
 assert e.value.status_code==409
 with pytest.raises(HTTPException):choose(out,{**payload,'target_version':1,'target_id':'invented'})
 assert choose(out,{**payload,'target_version':1,'target_id':None})['target_selection']['status']=='none'


@pytest.mark.parametrize('fixture,bridge_z,expected',[('bookend',None,'matched'),('split-bookend',40,'matched'),('split-bookend',56,'ambiguous')])
def test_native_catalog_tracks_all_cutouts_and_split(tmp_path,fixture,bridge_z,expected):
 import os
 if not worker_available():pytest.skip('Native worker not configured')
 from pathlib import Path
 from doodle_to_cad.brep import build_brep
 from doodle_to_cad.build_contract import BuildInput
 recipe=json.loads(Path(f'benchmarks/brep-selection/{fixture}.json').read_text())
 if bridge_z is not None:recipe['parameters']['bridge_z']['value']=bridge_z
 source=tmp_path/'recipe.json';source.write_text(json.dumps(recipe))
 built=build_brep(BuildInput('usd-brep',source,tmp_path,render=False));assert built.ok,built.log
 catalog=built.backend_details['selection_catalog'];assert catalog['status']=='available'
 assert any(t['rule'].get('owner')=='cut1' for t in catalog['targets'])
 saved={'rule':{'kind':'box_cutout','owner':'cut4','cutter':'cutter4','expected_faces':4},'label':'Opening','selected_in_revision':'original'}
 assert resolve({'diagnostics':built.backend_details},saved)['status']==expected
