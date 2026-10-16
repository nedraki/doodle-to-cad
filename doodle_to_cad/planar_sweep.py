"""One planar circular bend with optional tangent straight ends and a rectangle."""
import math
from .planar_profile import endpoints,near


def resolve_sweep(op,values,scalar):
    if op['plane']!='xy' or op['frame_rule']!='normal_to_path_z_up':
        raise ValueError('Sweep supports XY paths with a Z-up section normal to the path')
    width=scalar(op['section_width'],values);height=scalar(op['section_height'],values)
    if not .01<=width<=256 or not .01<=height<=256:
        raise ValueError('Sweep section dimensions must be 0.01–256 mm')
    path=op['path']
    if not isinstance(path,list) or not 1<=len(path)<=3:
        raise ValueError('Sweep path requires one circular arc and optional tangent straight ends')
    resolved=[]
    def point(p):
        if not isinstance(p,list) or len(p)!=2:raise ValueError('Sweep path points require XY coordinates')
        return [scalar(x,values) for x in p]
    for edge in path:
        if not isinstance(edge,dict):raise ValueError('Invalid sweep path edge')
        if edge.get('kind')=='line' and set(edge)=={'kind','start','end'}:
            item={'kind':'line','start':point(edge['start']),'end':point(edge['end'])}
            if math.dist(item['start'],item['end'])<.01:raise ValueError('Sweep straight segment is too short')
        elif edge.get('kind')=='arc' and set(edge)=={'kind','center','radius','start_angle','end_angle'}:
            item={'kind':'arc','center':point(edge['center']),**{k:scalar(edge[k],values) for k in ['radius','start_angle','end_angle']}}
            if not width/2+.01<=item['radius']<=256 or not 1<=abs(item['end_angle']-item['start_angle'])<=180:
                raise ValueError('Sweep bend needs radius greater than half section width and angle magnitude 1–180 degrees')
        else:raise ValueError('Sweep path supports line and circular arc only')
        resolved.append(item)
    kinds=[e['kind'] for e in resolved]
    if kinds not in [['arc'],['line','arc'],['arc','line'],['line','arc','line']]:
        raise ValueError('Sweep supports one bend with optional straight ends, not multiple bends')
    # A line's endpoint order does not change its locus. Orient optional
    # straight ends toward/away from the authored arc; never move a point.
    arc_index=kinds.index('arc');arc=resolved[arc_index]
    arc_start,arc_end=endpoints(arc)
    if arc_index:
        line=resolved[0]
        if near(line['start'],arc_start):resolved[0]={**line,'start':line['end'],'end':line['start']}
    if arc_index<len(resolved)-1:
        line=resolved[-1]
        if near(line['end'],arc_end):resolved[-1]={**line,'start':line['end'],'end':line['start']}
    for index,(a,b) in enumerate(zip(resolved,resolved[1:]),1):
        if not near(endpoints(a)[1],endpoints(b)[0]):raise ValueError('Sweep path has a gap')
        if math.dist(tangent(a,True),tangent(b,False))>1e-6:raise ValueError(f'Sweep join {index}: incoming tangent {tangent(a,True)} differs from outgoing tangent {tangent(b,False)}. Reorder the path or correct arc angles; every join must be tangent and forward.')
    # The kernel expects CCW arcs. Reverse a clockwise chain without changing
    # its geometric locus or section. Keep the authored order in the recipe.
    arc=next(e for e in resolved if e['kind']=='arc')
    if arc['end_angle']<arc['start_angle']:
        canonical=[]
        for edge in reversed(resolved):
            if edge['kind']=='line':canonical.append({**edge,'start':edge['end'],'end':edge['start']})
            else:canonical.append({**edge,'start_angle':edge['end_angle'],'end_angle':edge['start_angle']})
        resolved=canonical
    return {'path':resolved,'section_width':width,'section_height':height}


def tangent(edge,end=False):
    if edge['kind']=='line':
        v=[b-a for a,b in zip(edge['start'],edge['end'])];length=math.hypot(*v)
        return [x/length for x in v]
    angle=math.radians(edge['end_angle' if end else 'start_angle'])
    direction=1 if edge['end_angle']>edge['start_angle'] else -1
    return [-direction*math.sin(angle),direction*math.cos(angle)]
