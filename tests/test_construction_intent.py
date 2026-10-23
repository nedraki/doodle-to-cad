import copy
import pytest
from doodle_to_cad.construction_intent import validate_plan

PLAN={'view_frame':'Top XY, section thickness Z','features':[{'id':'curve','shape':'arc','section':'circular','axis_or_plane':'XY','dimensions':'visible diameter','placement':'centre above bed','evidence':'labelled end section'}],'connections':[],'edit_rules':['Preserve section diameter'],'unresolved':[]}

def test_plan_keeps_uncertainty_and_evidence_without_executing_it():
    plan=copy.deepcopy(PLAN);plan['unresolved']=['Mounting interface is not drawn']
    assert validate_plan(plan)==plan

@pytest.mark.parametrize('change',['missing','duplicate','numeric'])
def test_rejects_malformed_plan(change):
    plan=copy.deepcopy(PLAN)
    if change=='missing':del plan['view_frame']
    elif change=='duplicate':plan['features']*=2
    else:plan['features'][0]['section']=42
    with pytest.raises(ValueError):validate_plan(plan)


def test_plan_accepts_dimension_statements_as_a_list():
    plan=copy.deepcopy(PLAN);plan['features'][0]['dimensions']=['Diameter 8 mm','Radius 20 mm']
    assert validate_plan(plan)==plan
