"""Bounded closed line/arc profiles. Exact intersection tests precede construction."""
import math

EPS=1e-6
TAU=2*math.pi

def cross(a,b):return a[0]*b[1]-a[1]*b[0]
def sub(a,b):return [a[0]-b[0],a[1]-b[1]]
def near(a,b):return math.dist(a,b)<=EPS

def endpoints(e):
    if e['kind']=='line':return e['start'],e['end']
    c,r=e['center'],e['radius']
    return [[c[0]+r*math.cos(math.radians(t)),c[1]+r*math.sin(math.radians(t))] for t in [e['start_angle'],e['end_angle']]]

def on_arc(p,e):
    t=(math.atan2(p[1]-e['center'][1],p[0]-e['center'][0])-math.radians(e['start_angle']))%TAU
    return t<=math.radians(e['end_angle']-e['start_angle'])+EPS or TAU-t<EPS

def intersections(a,b):
    if a['kind']=='arc' and b['kind']=='line':return intersections(b,a)
    if a['kind']==b['kind']=='line':
        p,q=a['start'],b['start'];u,v=sub(a['end'],p),sub(b['end'],q);d=cross(u,v)
        if abs(d)<EPS:
            if abs(cross(sub(q,p),u))>EPS:return []
            # Collinear edges can meet at one endpoint, but cannot overlap.
            axis=0 if abs(u[0])>=abs(u[1]) else 1
            t=sorted([(x[axis]-p[axis])/u[axis] for x in [q,b['end']]])
            lo,hi=max(0,t[0]),min(1,t[1])
            if hi<lo-EPS:return []
            if hi-lo>EPS:raise ValueError('Profile edges overlap')
            return [[p[i]+lo*u[i] for i in range(2)]]
        t=cross(sub(q,p),v)/d;s=cross(sub(q,p),u)/d
        return [[p[i]+t*u[i] for i in range(2)]] if -EPS<=t<=1+EPS and -EPS<=s<=1+EPS else []
    if a['kind']=='line':
        p,u=a['start'],sub(a['end'],a['start']);w=sub(p,b['center'])
        aa=sum(x*x for x in u);bb=2*sum(x*y for x,y in zip(u,w));cc=sum(x*x for x in w)-b['radius']**2
        disc=bb*bb-4*aa*cc
        if disc < -EPS:return []
        roots=[(-bb+s*math.sqrt(max(0,disc)))/(2*aa) for s in [-1,1]]
        return [point for t in roots if -EPS<=t<=1+EPS and on_arc(point:=[p[i]+t*u[i] for i in range(2)],b)]
    c,d=a['center'],b['center'];r,s=a['radius'],b['radius'];dist=math.dist(c,d)
    if dist<EPS:
        if abs(r-s)<EPS:raise ValueError('Split arcs on the same circle are unsupported; use one arc')
        return []
    if dist>r+s+EPS or dist<abs(r-s)-EPS:return []
    x=(dist*dist+r*r-s*s)/(2*dist);h=math.sqrt(max(0,r*r-x*x));u=sub(d,c);base=[c[i]+x*u[i]/dist for i in range(2)]
    points=[[base[0]+sign*h*(-u[1])/dist,base[1]+sign*h*u[0]/dist] for sign in [-1,1]]
    return [p for p in points if on_arc(p,a) and on_arc(p,b)]

def samples(loop):
    points=[]
    for e in loop:
        if e['kind']=='line':points.append(e['start']);continue
        start,end=map(math.radians,[e['start_angle'],e['end_angle']]);r=e['radius']
        count=max(2,math.ceil((end-start)/(2*math.acos(max(-1,1-.001/r)))))
        for i in range(count):
            t=start+(end-start)*i/count
            points.append([e['center'][0]+r*math.cos(t),e['center'][1]+r*math.sin(t)])
    return points

def inside(p,polygon):
    result=False
    for a,b in zip(polygon,polygon[1:]+polygon[:1]):
        if (a[1]>p[1])!=(b[1]>p[1]) and p[0]<(b[0]-a[0])*(p[1]-a[1])/(b[1]-a[1])+a[0]:result=not result
    return result

def resolve_profile(loops,values,scalar):
    if not isinstance(loops,list) or not 1<=len(loops)<=16:raise ValueError('Expected an outer loop and at most 15 holes')
    resolved=[];total=0
    def point(p):
        if not isinstance(p,list) or len(p)!=2:raise ValueError('Profile points require two coordinates')
        return [scalar(x,values) for x in p]
    for loop in loops:
        if not isinstance(loop,list) or not 1<=len(loop)<=128:raise ValueError('Expected 1–128 profile edges')
        total+=len(loop)
        if total>128:raise ValueError('At most 128 total profile edges')
        out=[]
        for edge in loop:
            if not isinstance(edge,dict):raise ValueError('Invalid profile edge')
            if edge.get('kind')=='line' and set(edge)=={'kind','start','end'}:
                e={'kind':'line','start':point(edge['start']),'end':point(edge['end'])}
                if math.dist(e['start'],e['end'])<.01:raise ValueError('Profile lines must be at least 0.01 mm long')
            elif edge.get('kind')=='arc' and set(edge)=={'kind','center','radius','start_angle','end_angle'}:
                e={'kind':'arc','center':point(edge['center']),**{k:scalar(edge[k],values) for k in ['radius','start_angle','end_angle']}}
                if not .01<=e['radius']<=256 or not 0<e['end_angle']-e['start_angle']<=360:raise ValueError('Arc requires radius 0.01–256 and positive sweep up to 360 degrees')
            else:raise ValueError('Supported profile edges: line and circular arc')
            out.append(e)
        for a,b in zip(out,out[1:]+out[:1]):
            if not near(endpoints(a)[1],endpoints(b)[0]):raise ValueError('Profile loop is open or edges are out of order')
        resolved.append(out)
    edges=[(li,ei,e) for li,loop in enumerate(resolved) for ei,e in enumerate(loop)]
    for i,(li,ei,a) in enumerate(edges):
        for lj,ej,b in edges[i+1:]:
            allowed=[]
            if li==lj:
                if (ei+1)%len(resolved[li])==ej:allowed.append(endpoints(a)[1])
                if (ej+1)%len(resolved[li])==ei:allowed.append(endpoints(b)[1])
            if any(not any(near(p,q) for q in allowed) for p in intersections(a,b)):
                raise ValueError('Profile loops intersect, touch or self-intersect')
    polygons=[samples(loop) for loop in resolved]
    if sum(map(len,polygons))>8192:raise ValueError('Profile exceeds bounded sampling complexity')
    for points in polygons:
        if abs(sum(cross(a,b) for a,b in zip(points,points[1:]+points[:1])))<.0001:raise ValueError('Profile has no area')
    for i,hole in enumerate(polygons[1:],1):
        if not inside(hole[0],polygons[0]):raise ValueError('An inner loop lies outside the outer loop')
        if any(inside(hole[0],other) or inside(other[0],hole) for other in polygons[1:i]):raise ValueError('Nested or overlapping holes are unsupported')
    return resolved
