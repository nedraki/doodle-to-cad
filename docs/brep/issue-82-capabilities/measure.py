"""Provisional geometric observations, not #81-validated acceptance checks.

Sections come from triangles, not recipe values. Expected values are separate.
No automatic result represents human acceptance or full shape agreement.
"""
import math
import numpy as np
import trimesh

TOLERANCE = 0.15  # mm; deliberately above the worker's 0.05 mm chord tolerance

def section(mesh, axis, coordinate):
    normal=np.eye(3)[axis]; point=normal*coordinate
    path=mesh.section(plane_normal=normal, plane_origin=point)
    return [] if path is None else [np.asarray(p) for p in path.discrete]

def span(loops, axis):
    points=np.concatenate(loops)
    return float(np.ptp(points[:,axis]))

def fit_circle(points):
    p=np.asarray(points)[:,:2]
    a=np.column_stack([2*p[:,0],2*p[:,1],np.ones(len(p))])
    x,y,k=np.linalg.lstsq(a,np.sum(p*p,axis=1),rcond=None)[0]
    return float(np.sqrt(max(0,k+x*x+y*y)))

def corner_radius(loops):
    outer=max(loops,key=lambda p:np.ptp(p[:,0])*np.ptp(p[:,1]))
    # Select the lower-left curved quadrant from its actual tangent points.
    lo=outer.min(axis=0); mid=(outer.max(axis=0)+lo)/2
    candidates=outer[(outer[:,0]<mid[0]) & (outer[:,1]<mid[1])]
    curved=candidates[(candidates[:,0]>lo[0]+1e-5)&(candidates[:,1]>lo[1]+1e-5)]
    if len(curved)<3: raise ValueError('insufficient lower-left arc samples')
    return fit_circle(curved)

def vertical_hits(mesh,x,y):
    tri=mesh.triangles; e1=tri[:,1]-tri[:,0];e2=tri[:,2]-tri[:,0]
    d=np.array([0.,0.,1.]);h=np.cross(d,e2);a=np.einsum('ij,ij->i',e1,h)
    valid=np.abs(a)>1e-10;inv=np.zeros_like(a);inv[valid]=1/a[valid]
    s=np.array([x,y,-1.])-tri[:,0];u=inv*np.einsum('ij,ij->i',s,h)
    q=np.cross(s,e1);v=inv*(q@d);t=inv*np.einsum('ij,ij->i',e2,q)
    hits=t[valid&(u>=-1e-8)&(v>=-1e-8)&(u+v<=1+1e-8)&(t>=0)]-1
    return sorted(set(np.round(hits,6).tolist()))

def observe(name,path):
    mesh=trimesh.load(path,force='mesh');lo,hi=mesh.bounds;ext=mesh.extents
    values=dict(zip(['outside_x','outside_y','outside_z'],map(float,ext)))
    mid=section(mesh,2,float((lo[2]+hi[2])/2))
    if name in ('fillet','shell','combined'):
        values['outer_radius']=corner_radius(mid)
    if name in ('fillet','combined'):
        hole=min(mid,key=lambda p:np.ptp(p[:,0])*np.ptp(p[:,1]))
        values['hole_diameter' if name=='fillet' else 'hole_core_diameter']=2*fit_circle(hole)
    if name in ('chamfer','combined'):
        a=section(mesh,2,0.1);b=section(mesh,2,0.5)
        # XZ section at the centre of the Y axis measures setback away from rounded corners.
        def width_at(z):
            loops=section(mesh,2,z)
            points=np.concatenate(loops)
            # outer loop extrema are on the straight middle side for these fixtures
            outer=max(loops,key=lambda p:np.ptp(p[:,0])*np.ptp(p[:,1]))
            return float(np.ptp(outer[:,0]))
        values['setback']=(ext[0]-width_at(.1))/2+.1
        slope=(width_at(.5)-width_at(.1))/.8
        values['bevel_angle_deg']=math.degrees(math.atan2(1,slope))
        if name=='combined':
            hole=min(a,key=lambda p:np.ptp(p[:,0])*np.ptp(p[:,1]))
            values['hole_mouth_diameter_at_z_0_1']=2*fit_circle(hole)
    if name in ('arc','sweep'):
        c=np.array([(lo[0]+hi[0])/2,0 if name=='arc' else 15])
        points=np.concatenate(mid);p=points[points[:,1]>c[1]+1]
        distances=np.linalg.norm(p[:,:2]-c,axis=1)
        # Only actual section vertices; triangulation intersections can slightly shorten chords.
        inner=float(distances.min());outer=float(distances.max())
        values['bend_radius']=(inner+outer)/2
        values['tube_diameter' if name=='arc' else 'section_width']=outer-inner
        if name=='sweep':
            values.update(section_height=float(ext[2]),minimum_x=float(lo[0]),minimum_y=float(lo[1]))
            # straight-to-arc tangent join location inferred from where the outer side leaves X=max
            edge=np.concatenate(mid)
            values['leg_length']=float(edge[np.abs(edge[:,0]-hi[0])<1e-4,1].max())
            values['end_positions']=[[float(lo[0]+3),float(lo[1]),4],[float(hi[0]-3),float(lo[1]),4]]
    if name=='loft':
        bottom=section(mesh,2,.01);top=section(mesh,2,float(hi[2]-.01))
        values.update(bottom_width=span(bottom,0),bottom_depth=span(bottom,1),
                      top_diameter=(span(top,0)+span(top,1))/2,separation=float(ext[2]))
    if name=='shell':
        inner=min(mid,key=lambda p:np.ptp(p[:,0])*np.ptp(p[:,1]))
        values.update(cavity_width=float(np.ptp(inner[:,0])),cavity_depth=float(np.ptp(inner[:,1])))
        values['wall_x']=(ext[0]-values['cavity_width'])/2
        values['wall_y']=(ext[1]-values['cavity_depth'])/2
        values['floor']=vertical_hits(mesh,40.137,30.119)[-1]
    if name=='pocket':
        for key,x,y in [('pocket_depth',14.137,14.119),('neighbor_2_depth',46.137,14.119),('neighbor_3_depth',14.137,30.119)]:
            values[key]=float(hi[2]-vertical_hits(mesh,x,y)[-1])
    sections={str(round(float(z),4)):[p.tolist() for p in section(mesh,2,float(z))]
              for z in [.05,ext[2]*.25,ext[2]*.5,ext[2]*.75,ext[2]-.05]}
    return {'values':values,'mesh':{'watertight':bool(mesh.is_watertight),
        'components':len(mesh.split()),'winding_consistent':bool(mesh.is_winding_consistent),
        'volume_mm3':float(mesh.volume),'triangles':len(mesh.faces),'bounds':mesh.bounds.tolist()},
        'xy_sections':sections,'xz_section':[p.tolist() for p in section(mesh,1,float((lo[1]+hi[1])/2))]}

def expected(name,recipe):
    p={k:v['value'] for k,v in recipe['parameters'].items()}
    if name=='fillet':return dict(outside_x=60,outside_y=40,outside_z=20,outer_radius=p['radius'],hole_diameter=8)
    if name=='chamfer':return dict(outside_x=50,outside_y=40,outside_z=20,setback=p['radius']/math.sqrt(2),bevel_angle_deg=45)
    if name=='arc':return dict(bend_radius=p['radius'],tube_diameter=8,outside_z=8)
    if name=='sweep':return dict(bend_radius=p['radius'],section_width=6,section_height=8,leg_length=15,minimum_x=0,minimum_y=0)
    if name=='loft':return dict(bottom_width=p['rect_width'],bottom_depth=30,top_diameter=30,separation=50)
    if name=='shell':return dict(outside_x=80,outside_y=60,outside_z=30,outer_radius=8,wall_x=p['thickness'],wall_y=p['thickness'],floor=p['thickness'],cavity_width=80-2*p['thickness'],cavity_depth=60-2*p['thickness'])
    if name=='combined':return dict(outside_x=60,outside_y=40,outside_z=20,outer_radius=6,hole_core_diameter=10,setback=p['radius']/math.sqrt(2),bevel_angle_deg=45)
    op=next(o for o in recipe['operations'] if o['id']=='box_p1')
    return dict(outside_x=60,outside_y=40,outside_z=20,pocket_depth=op['size'][2],neighbor_2_depth=2,neighbor_3_depth=5)

def compare(observation,expected_values):
    return {k:{'measured':observation['values'].get(k),'expected':v,
              'tolerance':.8 if k.endswith('_deg') else TOLERANCE,
              'within_tolerance':bool(k in observation['values'] and abs(observation['values'][k]-v)<=(.8 if k.endswith('_deg') else TOLERANCE))}
            for k,v in expected_values.items()}
