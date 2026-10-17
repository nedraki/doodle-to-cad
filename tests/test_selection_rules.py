from doodle_to_cad.selection_rules import match_faces,outer_vertical_edges


def test_extreme_face_survives_dimension_change_but_not_split():
    rule={'kind':'extreme_face','owner':'tray','axis':0,'side':'max'}
    for width in [60,70]:
        bounds=[[0,0,0],[width,40,20]];face=[[width,0,0],[width,40,20]]
        assert match_faces(rule,'tray',bounds,[face],[],{})['status']=='matched'
        assert match_faces(rule,'tray',bounds,[face,face],[],{})['status']=='ambiguous'
    assert match_faces(rule,'other',bounds,[face],[],{})['status']=='lost'


def test_cutout_removed_split_or_moved():
    rule={'kind':'box_cutout','owner':'hole','cutter':'tool','expected_faces':4}
    ops=[{'id':'result','kind':'union','left':'hole','right':'blank'},{'id':'hole','kind':'difference','right':'tool'},{'id':'tool','kind':'box'}]
    for x in [10,15]:
        tool=[[x,-1,20],[x+10,6,35]]
        faces=[[[x,0,20],[x,5,35]],[[x+10,0,20],[x+10,5,35]],[[x,0,20],[x+10,5,20]],[[x,0,35],[x+10,5,35]]]
        assert match_faces(rule,'result',[],faces,ops,{'tool':tool})['status']=='matched'
        assert match_faces(rule,'result',[],faces+faces[:1],ops,{'tool':tool})['status']=='ambiguous'
        assert match_faces(rule,'result',[],faces,[],{})['status']=='lost'
        assert match_faces(rule,'unused',[],faces,ops,{'tool':tool})['status']=='lost'


def test_outer_edges_exclude_internal_hole_and_horizontal_edges():
    bounds=[[0,0,0],[60,40,20]]
    edges=[[[0,0,0],[0,0,20]],[[10,10,0],[10,10,20]],[[0,0,20],[60,0,20]]]
    assert outer_vertical_edges(bounds,edges)==[0]
