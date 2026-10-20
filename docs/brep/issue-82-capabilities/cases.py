"""Manually authored, bounded feature contracts. No model-generated sources."""
from copy import deepcopy
from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[3]

def parameter(value, minimum=0.5, maximum=60):
    return {'value': value, 'min': minimum, 'max': maximum, 'unit': 'mm'}

def recipe(name, operations, parameters=None):
    return dict(version=1, units='mm', name=name, parameters=parameters or {},
                operations=operations, output=operations[-1]['id'])

def box(size):
    return dict(id='body', kind='box', origin=[0,0,0], size=size)

def fillet(body, radius, name='rounded'):
    return dict(id=name, kind='fillet', body=body, radius=radius, selector='outer_vertical')

def cases():
    result = {}
    def add(name, source, edit, value, continued, protected, steps, scad, note=''):
        result[name] = dict(recipe=source, edit=edit, value=value, continued=continued,
                            protected=protected, authoring_steps=steps, scad=scad, note=note)
    add('fillet', recipe('Rounded block with protected through hole', [box([60,40,20]),
        dict(id='hole',kind='cylinder',origin=[30,20,-1],radius=4,height=22,axis='z'),
        dict(id='cut',kind='difference',left='body',right='hole'),fillet('cut','radius')],
        {'radius':parameter(3,1,8)}), 'radius',5,6,
        ['outside_x','outside_y','outside_z','hole_diameter'],
        ['Create box','Create through cylinder','Subtract cylinder','Select outer_vertical edges and fillet'],
        'difference(){linear_extrude(20) offset(r=radius) translate([radius,radius]) square([60-2*radius,40-2*radius]); translate([30,20,-1]) cylinder(h=22,r=4);}',
        'Supported outer vertical edge family; no arbitrary bracket-junction selector.')
    add('chamfer', recipe('Horizontal block-edge chamfer', [box([50,40,20]),
        dict(id='bevel',kind='chamfer',body='body',radius='radius')], {'radius':parameter(3,1,6)}),
        'radius',5,4,['outside_x','outside_y','outside_z'],
        ['Create box','Apply chamfer operation (global kernel edge policy)'],
        'leg=radius/sqrt(2); hull(){translate([leg,leg,0]) cube([50-2*leg,40-2*leg,20]); translate([0,0,leg]) cube([50,40,20-2*leg]);}',
        'Measured convention: radius is bevel hypotenuse; setback=radius/sqrt(2), angle=45 degrees. No selective hole entrance API.')
    add('arc', recipe('Circular section half bend, WITHOUT straight ends', [dict(id='bend',kind='arc_pipe',
        origin=[0,0,4],bend_radius='radius',radius=4,angle=180)], {'radius':parameter(20,8,40)}),
        'radius',25,23,['tube_diameter','outside_z'], ['Create capped half arc pipe'],
        'translate([0,0,4]) rotate_extrude(angle=180) translate([radius,0]) circle(r=4);',
        'Arc-only case explicitly does not satisfy the straight-ended handle; separate rectangular sweep below does.')
    sweep=dict(id='handle',kind='sweep',origin=[0,0,0],plane='xy',frame_rule='normal_to_path_z_up',
        section_width=6,section_height=8,path=[
        dict(kind='line',start=['2*radius+3',0],end=['2*radius+3',15]),
        dict(kind='arc',center=['radius+3',15],radius='radius',start_angle=0,end_angle=180),
        dict(kind='line',start=[3,15],end=[3,0])])
    add('sweep',recipe('Rectangular handle with two tangent straight ends',[sweep],{'radius':parameter(20,8,40)}),
        'radius',25,23,['section_width','section_height','leg_length','minimum_x','minimum_y'],
        ['Define rectangular section','Define tangent line / half arc / tangent line path','Sweep with flat caps'],
        'linear_extrude(8) union(){translate([0,0]) square([6,15.01]); translate([2*radius,0]) square([6,15.01]); intersection(){translate([radius+3,15]) difference(){circle(r=radius+3);circle(r=radius-3);} translate([-1,15]) square([2*radius+8,radius+4]);}}',
        'Rectangular section, not a circular tube. Native sweep avoids separate join booleans.')
    loft=json.loads((ROOT/'docs/brep/bench-features/fixtures/loft_transition.json').read_text())
    # Fixed sampling correspondence is explicit in the OpenSCAD comparison, not claimed as an exact kernel surface.
    loft_scad='''n=96; h=50; r=15; d=30;
function q(a)=let(c=cos(a),s=sin(a),v=min((rect_width/2)/max(abs(c),0.000001),(d/2)/max(abs(s),0.000001))) [v*c,v*s,0];
p=concat([for(i=[0:n-1]) q(360*i/n)],[for(i=[0:n-1]) [r*cos(360*i/n),r*sin(360*i/n),h]]);
f=concat([[for(i=[n-1:-1:0]) i]],[[for(i=[0:n-1]) n+i]], [for(i=[0:n-1]) [i,(i+1)%n,n+(i+1)%n,n+i]]);
polyhedron(points=p,faces=f,convexity=10);'''
    add('loft',loft,'rect_width',48,44,['top_diameter','separation','bottom_depth'],
        ['Define rectangle','Define coaxial circle on parallel plane','Choose fixed corner-to-diagonal correspondence and loft'],loft_scad,
        'Solid transition only. OpenSCAD polar-correspondence polyhedron is an explicit approximation; intermediate surfaces may differ.')
    add('shell',recipe('Rounded open tray',[box([80,60,30]),fillet('body',8),
        dict(id='tray',kind='shell',body='rounded',thickness='thickness',opening='top',preserve='outer')],
        {'thickness':parameter(3,1,40)}),'thickness',4,5,['outside_x','outside_y','outside_z','outer_radius'],
        ['Create box','Round outer vertical edges to 8 mm','Shell inward with one open top'],
        'module rr(w,d,r){translate([r,r]) offset(r=r) square([w-2*r,d-2*r]);} difference(){linear_extrude(30) rr(80,60,8); translate([thickness,thickness,thickness]) linear_extrude(31) rr(80-2*thickness,60-2*thickness,8-thickness);}',
        'Uniform floor and wall thickness; varying wall/floor dimensions not exposed by shell.')
    add('combined',recipe('Rounded block with opening plus global chamfer',[box([60,40,20]),fillet('body',6),
        dict(id='hole',kind='cylinder',origin=[30,20,-1],radius=5,height=22,axis='z'),
        dict(id='cut',kind='difference',left='rounded',right='hole'),
        dict(id='bevel',kind='chamfer',body='cut',radius='radius')],{'radius':parameter(1,0.5,3)}),
        'radius',2,1.5,['outside_x','outside_y','outside_z','hole_core_diameter','outer_radius'],
        ['Create box','Round outer vertical edges','Create through cylinder','Subtract cylinder','Apply global chamfer'],
        None,'Combination probe: does global chamfer bevel the opening as well as exterior edges? No selected-hole chamfer claim. OpenSCAD comparator deferred until operation placement is measured.')
    pocket=json.loads((ROOT/'benchmarks/brep-targeted/pocket-block.json').read_text())
    add('pocket',pocket,'selected_pocket_depth',5,6,['outside_x','outside_y','outside_z','neighbor_2_depth','neighbor_3_depth'],
        ['Create block','Create and subtract pocket 1','Create and subtract pocket 2','Create and subtract pocket 3','Select pocket 1 by box_cutout rule'],
        'difference(){cube([60,40,20]); translate([8,8,20-selected_pocket_depth]) cube([12,12,selected_pocket_depth+1]); translate([40,8,18]) cube([12,12,3]); translate([8,24,15]) cube([12,12,6]);}',
        'Uses production targeted-edit planning and verification, not a whole-part text rewrite.')
    result['shell']['rejection_value']=30  # Valid parameter; production worker rejects a vanished cavity.
    return result

POCKET_RULE = {'kind':'box_cutout','owner':'cut1','cutter':'box_p1','expected_faces':5}
