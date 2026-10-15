import numpy as np
import trimesh
from doodle_to_cad.brep_checks import evaluate_drawing, section_check


def test_openings_cannot_be_satisfied_in_wrong_wall(monkeypatch):
    import doodle_to_cad.brep_checks as checks
    monkeypatch.setattr(checks,'projection_scores',lambda *a,**kw:({'front':.9,'top':.9},{
        'front':{'crop_internal_profiles':4,'rendered_internal_profiles':0},
        'top':{'crop_internal_profiles':0,'rendered_internal_profiles':4}}))
    result=evaluate_drawing(b'',{}, {},{'watertight':True,'components':1,'extents_mm':[80,50,100]}, {},100)
    assert result['status']=='failed' and 'front openings' in result['failures']
    assert result['geometry_status']=='passed'


def test_disconnected_solid_and_absent_drawing_never_pass():
    result=evaluate_drawing(b'',{}, {},{'watertight':True,'components':2,'extents_mm':[20,10,5]}, {},20)
    assert result['geometry_status']=='failed' and not result['accepted']
    assert result['projection_status']=='unverified'


def test_sections_distinguish_round_from_rectangular_profile():
    angle=np.linspace(0,2*np.pi,257)
    circle=np.c_[4*np.cos(angle),4*np.sin(angle)]
    cylinder=trimesh.creation.cylinder(radius=4,height=10,sections=128)
    box=trimesh.creation.box(extents=[8,8,10])
    assert section_check(cylinder,2,0,[circle],.25)['status']=='passed'
    assert section_check(box,2,0,[circle],.25)['status']=='failed'


def test_empty_section_and_missing_inner_loop_fail():
    box=trimesh.creation.box(extents=[8,8,10])
    rectangle=[[-4,-4],[4,-4],[4,4],[-4,4],[-4,-4]]
    assert section_check(box,2,0,[rectangle],.25)['status']=='passed'
    assert section_check(box,2,7,[rectangle],.25)['status']=='failed'
    assert section_check(box,2,0,[rectangle,rectangle],.25)['status']=='failed'
