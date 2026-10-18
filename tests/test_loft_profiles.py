import json,os
from pathlib import Path
import pytest
from doodle_to_cad.brep_recipe import validate_recipe
from doodle_to_cad.brep import build_brep, worker_available
from doodle_to_cad.build_contract import BuildInput

def recipe():return json.loads(Path('benchmarks/brep-lofts/reference.recipe.json').read_text())

@pytest.mark.parametrize('failure',['plane','mapping','offset','zero_length','reversed','zero_width','extra_profile','extra_rotation'])
def test_unsupported_loft_fails_before_worker(failure):
 r=recipe();o=r['operations'][0]
 if failure=='plane':o['plane']='xz'
 if failure=='mapping':o['correspondence']='twist'
 if failure=='offset':o['profiles'][1]['center'][0]=2
 if failure=='zero_length':o['profiles'][1]['center'][2]=0
 if failure=='reversed':o['profiles'].reverse()
 if failure=='zero_width':o['profiles'][0]['width']=0
 if failure=='extra_profile':o['profiles'].append(o['profiles'][1])
 if failure=='extra_rotation':o['profiles'][0]['rotation']=45
 with pytest.raises(ValueError,match='transition:'):validate_recipe(r)

@pytest.mark.skipif(not worker_available(),reason='Worker not configured')
@pytest.mark.parametrize('width',[40,48])
def test_native_loft_and_end_edit(tmp_path,width):
 r=recipe();r['parameters']['rectangle_width']['value']=width
 p=tmp_path/'recipe.json';p.write_text(json.dumps(r));b=build_brep(BuildInput('usd-brep',p,tmp_path,render=False))
 assert b.ok,b.log
 assert b.measurements['extents_mm']==pytest.approx([width,30,50],abs=.05)
 assert b.measurements['components']==1
 from scripts.check_loft_reference import measure
 assert measure(b.stl,width)['passed']
