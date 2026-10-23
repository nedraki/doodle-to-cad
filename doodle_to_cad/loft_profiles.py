"""Two parallel, concentric profiles with fixed corner-to-quadrant correspondence."""
import math


def resolve_loft(op,values,scalar):
    if op['plane']!='xy' or op['correspondence']!='rectangle_corners_to_circle_diagonals':
        raise ValueError('Loft requires XY profiles with rectangle corners matched to circle diagonals')
    profiles=op['profiles']
    if not isinstance(profiles,list) or len(profiles)!=2:
        raise ValueError('Loft requires a rectangle followed by a circle')
    resolved=[]
    for index,profile in enumerate(profiles):
        shape='rectangle' if index==0 else 'circle'
        fields={'shape','center','width','height'} if index==0 else {'shape','center','radius'}
        if not isinstance(profile,dict) or set(profile)!=fields or profile['shape']!=shape:
            raise ValueError('Loft requires rectangle width/height then circle radius')
        if not isinstance(profile['center'],list) or len(profile['center'])!=3:
            raise ValueError('Loft profile center requires three coordinates')
        item={'shape':shape,'center':[scalar(v,values) for v in profile['center']]}
        for key in fields-{'shape','center'}:
            item[key]=scalar(profile[key],values)
            if not .01<=item[key]<=128:raise ValueError('Loft profile dimensions must be 0.01–128 mm')
        resolved.append(item)
    a,b=resolved
    if math.dist(a['center'][:2],b['center'][:2])>1e-6:
        raise ValueError('Loft currently requires profiles with the same XY center')
    if not .01<=b['center'][2]-a['center'][2]<=256:
        raise ValueError('Loft circle must be 0.01–256 mm above the rectangle')
    return resolved
