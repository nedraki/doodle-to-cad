import copy

import pytest

from doodle_to_cad.feature_evidence import region_catalog, validate_interpretation

CATALOG=[{'view_id':'v1','region_id':'view','kind':'view'},
         {'view_id':'v1','region_id':'profile_1','kind':'outer'},
         {'view_id':'v2','region_id':'view','kind':'view'}]


def sample():
    return {'version':1,'object_hypothesis':'Unknown outlined body',
            'features':[{'id':'body','type':'body','description':'Rectangular outline',
                         'status':'observed','evidence':[{'view_id':'v1','region_id':'profile_1'}],
                         'reason':'Visible outer contour'}],
            'relationships':[], 'assumptions':[], 'unresolved':['Depth is not supplied.'],
            'conflicts':['Different views may show different widths.']}


def test_outer_outline_cannot_establish_hidden_walls():
    raw=sample();raw['features'][0]['type']='wall'
    before=copy.deepcopy(raw)
    result=validate_interpretation(raw,CATALOG)
    assert result['features'][0]['status']=='unresolved'
    assert result['features'][0]['model_status']=='observed'
    assert 'Outer outlines' in result['features'][0]['review_note']
    assert result['conflicts']==raw['conflicts']
    assert raw==before
    assert not result['review']['executable']
    assert not result['review']['drawing_fidelity_verified']


def test_invented_region_is_rejected():
    raw=sample();raw['features'][0]['evidence'][0]['region_id']='invented'
    with pytest.raises(ValueError,match='unknown measured region'):
        validate_interpretation(raw,CATALOG)


def test_shared_dimension_needs_distinct_views():
    raw=sample()
    raw['relationships']=[{'id':'width','type':'shared_dimension','features':['body'],
                          'description':'Width shared across projections','status':'inferred',
                          'evidence':[{'view_id':'v1','region_id':'view'}], 'reason':'Same part'}]
    assert validate_interpretation(raw,CATALOG)['relationships'][0]['status']=='unresolved'
    raw['relationships'][0]['evidence'].append({'view_id':'v2','region_id':'view'})
    assert validate_interpretation(raw,CATALOG)['relationships'][0]['status']=='inferred'


def test_unsupported_claim_is_retained_as_unresolved():
    raw=sample();raw['features'][0]['evidence']=[]
    result=validate_interpretation(raw,CATALOG)
    assert result['features'][0]['status']=='unresolved'
    assert result['features'][0]['description']=='Rectangular outline'


def test_relationship_requires_existing_feature():
    raw=sample()
    raw['relationships']=[{'id':'connection','type':'connected','features':['unknown'],
                          'description':'A joint','status':'inferred','evidence':[], 'reason':'Hypothesis'}]
    with pytest.raises(ValueError,match='unknown feature'):
        validate_interpretation(raw,CATALOG)


def test_region_catalog_keeps_measured_coordinates_and_view_assignment():
    evidence={'view_geometry':[{'view_id':1,'direction':'front','sheet_bbox_normalized':[.1,.2,.3,.4],
        'measured_span_pixels':{'horizontal_axis_u':120,'vertical_axis_v':80},
        'cad_mapping':{'plane':'XZ'},'outer_profile':{'profile_id':7,'bbox_view_normalized':[0,0,1,1]},
        'internal_profiles':[{'profile_id':8,'bbox_view_normalized':[.2,.3,.1,.4]}]}]}
    catalog=region_catalog(evidence)
    assert catalog[-1]['region_id']=='profile_8'
    assert catalog[-1]['bbox_view_normalized']==[.2,.3,.1,.4]
    assert catalog[-1]['view_id']=='1'
    assert catalog[-1]['view_assignment']=='spatial heuristic'
    assert catalog[-1]['cad_mapping']=={'plane':'XZ'}


def test_shared_axes_compare_only_matching_projection_axes():
    from doodle_to_cad.feature_evidence import shared_axis_evidence
    catalog=[{'kind':'view','view_id':'front','cad_mapping':{'u_maps_to':'+X','v_maps_to':'-Z'},
              'measured_span_pixels':{'horizontal_axis_u':200,'vertical_axis_v':100}},
             {'kind':'view','view_id':'right','cad_mapping':{'u_maps_to':'+Y','v_maps_to':'-Z'},
              'measured_span_pixels':{'horizontal_axis_u':50,'vertical_axis_v':102}}]
    result=shared_axis_evidence(catalog)
    assert len(result)==1 and result[0]['axis']=='Z'
    assert result[0]['status']=='consistent_spans'
    assert not result[0]['physical_dimension_verified']
    catalog[1]['measured_span_pixels']['vertical_axis_v']=150
    assert shared_axis_evidence(catalog)[0]['status']=='review_required'


def test_projected_connection_is_not_reported_as_proven_solid():
    raw=sample();raw['relationships']=[{'id':'join','type':'connected','features':['body'],
        'description':'Continuous projected region','reason':'Visible ink continuity','status':'observed',
        'evidence':[{'view_id':'v1','region_id':'view'}]}]
    result=validate_interpretation(raw,CATALOG)
    claim=result['relationships'][0]
    assert claim['status']=='inferred' and claim['model_status']=='observed'
    assert result['unresolved']==raw['unresolved']
    assert result['review']['policy_warnings']


def test_text_sized_groups_do_not_displace_real_wheel_views():
    from doodle_to_cad.feature_evidence import view_assignment_evidence
    from doodle_to_cad.evaluation import assign_view_groups
    groups=[{'view_id':'label','bbox_normalized':[.1,.05,.1,.02],'center_normalized':[.15,.06]},
            {'view_id':'front','bbox_normalized':[.1,.2,.4,.6],'center_normalized':[.3,.5]},
            {'view_id':'side','bbox_normalized':[.7,.2,.05,.6],'center_normalized':[.725,.5]}]
    original={'view_groups':groups,'view_geometry':[{'view_id':'label'}]}
    filtered=view_assignment_evidence(original)
    assigned=assign_view_groups(filtered)
    assert assigned['front']['view_id']=='front'
    assert assigned['right']['view_id']=='side'
    assert filtered['view_geometry']==original['view_geometry']
    assert len(original['view_groups'])==3
    assert filtered['interpretation_view_filter']['excluded_from_direction_assignment']==['label']
