import json,os,math
from pathlib import Path
import pytest
from doodle_to_cad.brep_recipe import validate_recipe
from doodle_to_cad.brep import build_brep, worker_available
from doodle_to_cad.build_contract import BuildInput

def recipe():return json.loads(Path('benchmarks/brep-shells/reference.recipe.json').read_text())

@pytest.mark.parametrize('failure',['opening','preserve','zero','missing_body'])
def test_shell_rejects_unsupported_contract(failure):
 r=recipe();o=r['operations'][-1]
 if failure=='opening':o['opening']='side'
 if failure=='preserve':o['preserve']='inner'
 if failure=='zero':o['thickness']=0
 if failure=='missing_body':o['body']='missing'
 with pytest.raises(ValueError):validate_recipe(r)

@pytest.mark.skipif(not worker_available(),reason='Worker not configured')
@pytest.mark.parametrize('thickness',[2,3,25])
def test_native_rounded_tray_and_impossible_thickness(tmp_path,thickness):
 r=recipe();r['parameters']['thickness']['value']=thickness
 p=tmp_path/'recipe.json';p.write_text(json.dumps(r));b=build_brep(BuildInput('usd-brep',p,tmp_path,render=False))
 if thickness==25:
  assert not b.ok and 'required interior or floor' in b.log
  assert not list(tmp_path.glob('brep-*/model.stl'))
  return
 assert b.ok,b.log
 assert b.measurements['extents_mm']==pytest.approx([60,40,20],abs=.05)
 assert b.measurements['components']==1
 expected=20*(2400-(4-math.pi)*36)-(20-thickness)*((60-2*thickness)*(40-2*thickness)-(4-math.pi)*(6-thickness)**2)
 assert b.backend_details['solid_volume_mm3']==pytest.approx(expected,rel=1e-5)
