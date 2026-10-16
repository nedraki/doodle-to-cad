import copy,json,os
from pathlib import Path
import pytest
from doodle_to_cad.brep_recipe import validate_recipe
from doodle_to_cad.brep import build_brep
from doodle_to_cad.build_contract import BuildInput

FIXTURE=Path('benchmarks/brep-profiles/reference.recipe.json')
def recipe():return json.loads(FIXTURE.read_text())

def test_depth_edit_preserves_profile_and_resolves_expressions():
    source=recipe();edited,ops=validate_recipe(source,{'thickness':10})
    assert ops[0]['depth']==10 and source['parameters']['thickness']['value']==6
    assert edited['operations']==source['operations']
    assert ops[0]['loops'][1][0]['radius']==4

@pytest.mark.parametrize('failure',['open','cross','outside','tangent','nested','zero_depth','direction','unknown_edge','plane'])
def test_invalid_profiles_fail_before_worker(failure):
    r=recipe();o=r['operations'][0]
    if failure=='open':o['loops'][0][0]['end']=[59,0]
    if failure=='cross':
        p=[[0,0],[60,40],[0,40],[60,0],[0,0]]
        o['loops'][0]=[{'kind':'line','start':a,'end':b} for a,b in zip(p,p[1:])]
    if failure=='outside':o['loops'][1][0]['center']=[80,15]
    if failure=='tangent':o['loops'][1][0]['center']=[4,15]
    if failure=='nested':
        o['loops'].append([{'kind':'arc','center':[12,15],'radius':2,'start_angle':0,'end_angle':360}])
    if failure=='zero_depth':o['depth']=0
    if failure=='plane':o['plane']='xz'
    if failure=='direction':o['direction']=True
    if failure=='unknown_edge':o['loops'][1][0]['kind']='spline'
    with pytest.raises(ValueError):validate_recipe(r)

@pytest.mark.skipif(not os.getenv('DOODLE_BREP_PYTHON'),reason='Worker not configured')
@pytest.mark.parametrize('direction',[1,-1])
def test_native_extrusion_direction_and_inner_loop(tmp_path,direction):
    r=recipe();r['operations'][0]['direction']=direction
    if direction==-1:r['operations'][0]['origin'][2]=6
    path=tmp_path/'recipe.json';path.write_text(json.dumps(r))
    result=build_brep(BuildInput('usd-brep',path,tmp_path,render=False))
    assert result.ok,result.log
    assert result.measurements['components']==1
    assert result.measurements['extents_mm']==pytest.approx([60,40,6],abs=.05)
    import math
    area=60*40-20*10-(36-9*math.pi)-16*math.pi
    assert result.backend_details['solid_volume_mm3']==pytest.approx(area*6,rel=1e-5)


def test_semicircle_and_diameter_form_a_closed_profile():
    r=recipe();r['operations'][0]['loops']=[[
        {'kind':'arc','center':[10,10],'radius':10,'start_angle':0,'end_angle':180},
        {'kind':'line','start':[0,10],'end':[20,10]},
    ]]
    _,ops=validate_recipe(r)
    assert len(ops[0]['loops'])==1


@pytest.mark.parametrize('failure',['arc_crossing','circle_overlap','same_circle','too_many_edges'])
def test_arc_intersections_and_complexity_are_rejected(failure):
    r=recipe();o=r['operations'][0]
    if failure=='arc_crossing':o['loops'][1][0].update(center=[57,37],radius=3)
    if failure=='circle_overlap':
        o['loops'].append([{'kind':'arc','center':[16,15],'radius':4,'start_angle':0,'end_angle':360}])
    if failure=='same_circle':
        o['loops'][1]=[{'kind':'arc','center':[12,15],'radius':4,'start_angle':0,'end_angle':180},{'kind':'arc','center':[12,15],'radius':4,'start_angle':180,'end_angle':360}]
    if failure=='too_many_edges':o['loops'][0]*=20
    with pytest.raises(ValueError):validate_recipe(r)
