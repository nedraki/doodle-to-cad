import json,os,math
from pathlib import Path
import pytest
from doodle_to_cad.brep_recipe import validate_recipe
from doodle_to_cad.brep import build_brep, worker_available
from doodle_to_cad.build_contract import BuildInput

def recipe():return json.loads(Path('benchmarks/brep-sweeps/reference.recipe.json').read_text())

@pytest.mark.parametrize('failure',['gap','reverse','sharp_join','too_wide','plane','frame','spline','multiple_bends','long_bend','zero_height'])
def test_invalid_sweep_rejected(failure):
 r=recipe();o=r['operations'][0]
 if failure=='gap':o['path'][0]['end']=[43,14]
 if failure=='reverse':o['path'][0]['start']=[43,20]
 if failure=='sharp_join':o['path'][0]['start']=[40,0]
 if failure=='too_wide':o['section_width']=40
 if failure=='plane':o['plane']='xz'
 if failure=='frame':o['frame_rule']='free'
 if failure=='spline':o['path'][1]['kind']='spline'
 if failure=='multiple_bends':o['path']=[o['path'][1],o['path'][1]]
 if failure=='long_bend':o['path'][1]['end_angle']=270
 if failure=='zero_height':o['section_height']=0
 with pytest.raises(ValueError,match="handle:"):validate_recipe(r)

@pytest.mark.skipif(not worker_available(),reason='Worker not configured')
@pytest.mark.parametrize('height',[8,10])
def test_native_rectangular_sweep_and_height_edit(tmp_path,height):
 r=recipe();r['parameters']['section_height']['value']=height
 p=tmp_path/'recipe.json';p.write_text(json.dumps(r));b=build_brep(BuildInput('usd-brep',p,tmp_path,render=False))
 assert b.ok,b.log
 assert b.measurements['components']==1
 assert b.measurements['extents_mm']==pytest.approx([46,38,height],abs=.05)
 assert b.backend_details['solid_volume_mm3']==pytest.approx(6*height*(30+20*math.pi),rel=1e-5)

@pytest.mark.skipif(not worker_available(),reason='Worker not configured')
@pytest.mark.parametrize('start_angle',[0,45,90,315])
def test_quarter_bend_keeps_rectangular_frame(tmp_path,start_angle):
 r=recipe();o=r['operations'][0];o['path']=[{'kind':'arc','center':[23,23],'radius':20,'start_angle':start_angle,'end_angle':start_angle+90}]
 p=tmp_path/'recipe.json';p.write_text(json.dumps(r));b=build_brep(BuildInput('usd-brep',p,tmp_path,render=False))
 assert b.ok,b.log
 assert b.measurements['extents_mm'][2]==pytest.approx(8,abs=.05)
 assert b.backend_details['solid_volume_mm3']==pytest.approx(6*8*20*math.pi/2,rel=1e-5)

@pytest.mark.skipif(not worker_available(),reason='Worker not configured')
@pytest.mark.parametrize("reverse_lines",[False,True])
def test_clockwise_authored_path_preserves_geometry(tmp_path,reverse_lines):
 r=recipe();path=r['operations'][0]['path']
 r['operations'][0]['path']=[{**path[2],'start':path[2]['end'],'end':path[2]['start']},{**path[1],'start_angle':180,'end_angle':0},{**path[0],'start':path[0]['end'],'end':path[0]['start']}]
 if reverse_lines:
  for edge in r["operations"][0]["path"]:
   if edge["kind"]=="line":edge["start"],edge["end"]=edge["end"],edge["start"]
 edited,resolved=validate_recipe(r)
 assert edited['operations'][0]['path'][1]['start_angle']==180
 assert resolved[0]['path']==path
 p=tmp_path/'recipe.json';p.write_text(json.dumps(r));b=build_brep(BuildInput('usd-brep',p,tmp_path,render=False));assert b.ok,b.log
 from scripts.check_sweep_product import measure
 assert measure(b.stl,8)['passed']
