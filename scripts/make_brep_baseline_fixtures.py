"""Create labeled reference drawings and fixed contracts for task 01.

Synthetic cases are engineering diagrams, not samples of user handwriting.
Run from any directory with the application environment.
"""
import hashlib
import json
import math
from pathlib import Path
import shutil

from PIL import Image, ImageDraw

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'benchmarks/brep-baseline'


def synthetic_drawing(name):
    image=Image.new('RGB',(1000,650),'white');draw=ImageDraw.Draw(image)
    draw.text((25,15),name.replace('_',' ').upper()+' - SYNTHETIC REFERENCE',fill='black')
    def line(points):draw.line(points,fill='black',width=3)
    def circle(box):draw.ellipse(box,outline='black',width=3)
    if name=='wheel':
        draw.text((65,60),'FRONT (XZ)',fill='black');draw.text((690,60),'RIGHT (YZ)',fill='black')
        cx,cy,scale=310,330,3.5
        # Draw the rim and hub. Each spoke outline extends to their boundaries.
        for r in (60,54,16):circle((cx-r*scale,cy-r*scale,cx+r*scale,cy+r*scale))
        for i in range(8):
            angle=i*math.pi/4
            for side in (-1,1):
                points=[]
                for radius in (math.sqrt(16**2-4**2),math.sqrt(54**2-4**2)):
                    x=radius*math.cos(angle)-side*4*math.sin(angle)
                    z=radius*math.sin(angle)+side*4*math.cos(angle)
                    points.append((cx+x*scale,cy-z*scale))
                line(points)
        draw.rectangle((720,120,748,540),outline='black',width=3)
        draw.text((160,570),'OD 120 mm; thickness 8 mm; 8 spokes',fill='black')
    elif name=='curved_handle':
        draw.text((65,60),'TOP (XY)',fill='black');draw.text((690,60),'END SECTION',fill='black')
        # U path: two 30 mm straight legs joined by a 20 mm radius semicircle.
        cx,cy,s=310,330,5
        for r in (16,24):draw.arc((cx-r*s,cy-r*s,cx+r*s,cy+r*s),180,360,fill='black',width=3)
        for x in (-24,-16,16,24):line([(cx+x*s,cy),(cx+x*s,cy+30*s)])
        for lo,hi in [(-24,-16),(16,24)]:line([(cx+lo*s,cy+30*s),(cx+hi*s,cy+30*s)])
        circle((720,220,800,300));draw.text((705,320),'diameter 8 mm',fill='black')
        draw.text((120,550),'Bend centreline R20; straight legs 30 mm',fill='black')
    elif name=='transition':
        draw.text((65,60),'BOTTOM (XY)',fill='black');draw.text((400,60),'TOP (XY)',fill='black');draw.text((700,60),'FRONT (XZ)',fill='black')
        draw.rectangle((70,160,310,320),outline='black',width=3)
        circle((430,180,550,300))
        line([(680,420),(920,420),(860,180),(740,180),(680,420)])
        draw.text((65,350),'60 x 40 mm rectangle',fill='black');draw.text((410,350),'diameter 30 mm',fill='black')
        draw.text((680,460),'height 60 mm; solid',fill='black')
    return image


def main():
    OUT.mkdir(exist_ok=True)
    cases={
      'bookend':dict(existing='001_l_bookend_multiview',dimensions_mm={'extents_xyz':[80,50,100],'wall':3},features=[{'id':'cut1','box_xz_mm':[18.4,18,31.2,59]},{'id':'cut2','box_xz_mm':[7.2,72,32.8,90]},{'id':'cut3','box_xz_mm':[38.8,42,46,73]},{'id':'cut4','box_xz_mm':[56.4,20,63.6,57]}],relations=['Base and panel overlap and form one solid.','Four cutouts pass through the panel along Y.'],unknown=['Manufacturing method and material are not supplied.','Projection standard is not supplied.','Reference dimensions are CAD authority; not all are written on the doodle.']),
      'enclosure':dict(existing='008_open_enclosure_window',dimensions_mm={'extents_xyz':[120,80,40],'wall':3,'floor':3},features=[{'id':'cavity','bounds_xyz_mm':[[3,3,3],[117,77,40]],'open_top':True},{'id':'window','box_xz_mm':[30,8,90,32],'axis':'y'}],relations=['Walls and floor form one solid.','The top is open.','The front window opens into the cavity.'],unknown=['Material and edge treatment are unspecified.','Wall thickness is reference intent; ask if input evidence does not resolve it.']),
      'wheel':dict(dimensions_mm={'extents_xyz':[120,8,120],'outer_diameter':120,'inner_rim_diameter':108,'hub_diameter':32,'spoke_width':8},features=[{'id':'hub','center_xyz_mm':[60,4,60]},{'id':'spokes','count':8,'angles_degrees':[0,45,90,135,180,225,270,315]}],relations=['Every spoke overlaps the hub and rim.','All material forms one solid.'],unknown=['Synthetic eight-spoke reference; it is not a reconstruction of the user screenshot.','Material, edge treatment and axle bore are unspecified.','No axle bore is part of this test contract.']),
      'curved_handle':dict(dimensions_mm={'extents_xyz':[48,54,8],'section_diameter':8,'bend_centerline_radius':20,'straight_leg_length':30},features=[{'id':'path','start_xyz_mm':[-20,-30,4],'left_tangent_xyz_mm':[-20,0,4],'arc_center_xyz_mm':[0,0,4],'right_tangent_xyz_mm':[20,0,4],'end_xyz_mm':[20,-30,4]}],relations=['The two legs and bend form one solid.','The circular section stays constant.','The ends are capped.'],unknown=['No mounting interface or load requirement is supplied.','Synthetic reference awaits user review.']),
      'transition':dict(dimensions_mm={'extents_xyz':[60,40,60],'bottom_rectangle':[60,40],'top_diameter':30,'height':60},features=[{'id':'bottom','center_xyz_mm':[0,0,0]},{'id':'top','center_xyz_mm':[0,0,60]}],relations=['Both profiles share the Z axis.','The transition is solid and capped.'],unknown=['Intermediate surface curvature is not specified. Do not score it as an exact reference.','No hollow passage or wall thickness is specified.','Synthetic reference awaits user review.'])
    }
    wheel='''$fn=128;
// Wheel lies in XZ. Spokes overlap the hub and rim by 1 mm.
translate([60,8,60]) rotate([90,0,0]) union(){
difference(){cylinder(d=120,h=8);translate([0,0,-1])cylinder(d=108,h=10);}
cylinder(d=32,h=8);
for(a=[0:45:315])rotate([0,0,a])translate([15,-4,0])cube([40,8,8]);}
'''
    handle='''$fn=128;
translate([0,0,4]) union(){rotate_extrude(angle=180)translate([20,0])circle(r=4);
for(x=[-20,20])translate([x,0,0])rotate([90,0,0])cylinder(r=4,h=30);}
'''
    transition='''$fn=128;
// A convex-hull reference; this does not specify a unique loft surface.
hull(){translate([-30,-20,0])cube([60,40,0.01]);translate([0,0,59.99])cylinder(d=30,h=0.01);}
'''
    for name,case in cases.items():
        dest=OUT/name;dest.mkdir(exist_ok=True)
        existing=case.pop('existing',None)
        if existing:
            source=ROOT/'benchmarks/cases'/existing
            shutil.copyfile(source/'source/drawing.png',dest/'drawing.png')
            shutil.copyfile(source/'ground_truth/model.scad',dest/'reference.scad')
            provenance={'kind':'existing_repository_reference','source_case':existing,'authority':'See original case manifest. Intent confirmation can remain pending.'}
        else:
            synthetic_drawing(name).save(dest/'drawing.png')
            (dest/'reference.scad').write_text({'wheel':wheel,'curved_handle':handle,'transition':transition}[name])
            provenance={'kind':'synthetic_engineering_diagram','generator':'scripts/make_brep_baseline_fixtures.py','authority':'Proposed test intent. Not a user doodle or production design.'}
        manifest=dict(schema_version=1,id=name,provenance=provenance,**case,
          controls={'primary_view':'front' if name not in ('curved_handle',) else 'top','target_max_dimension_mm':max(case['dimensions_mm']['extents_xyz']),'notes':''},
          expected={'components':1,'watertight':True},
          tolerances={'reference_dimension_abs_mm':0.05,'generated_dimension_relative':0.02,'feature_position_abs_mm':1.0,'feature_size_abs_mm':1.0,'wall_thickness_abs_mm':0.5,'count_error':0,'connection_gap_mm':0.0},
          evidence_policy='Fix these tolerances before future trials. Do not change them to pass a candidate. Log assumptions and unsupported checks.',
          sha256={f:hashlib.sha256((dest/f).read_bytes()).hexdigest() for f in ['drawing.png','reference.scad']})
        (dest/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print('Saved five reference drawings, sources, and fixed test contracts.')

if __name__=='__main__':main()
