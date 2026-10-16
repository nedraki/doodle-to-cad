"""Deterministic fixture and independent drawing. Reference recipe is never model input."""
import json
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
from doodle_to_cad.construction_recipe import migrate_v1
OUT=Path('benchmarks/brep-profiles');OUT.mkdir(exist_ok=True)
points=[[0,0],[60,0],[60,34]]
outer=[{'kind':'line','start':a,'end':b} for a,b in zip(points,points[1:])]
outer += [{'kind':'arc','center':[54,34],'radius':6,'start_angle':0,'end_angle':90}]
points=[[54,40],[40,40],[40,30],[20,30],[20,40],[0,40],[0,0]]
outer += [{'kind':'line','start':a,'end':b} for a,b in zip(points,points[1:])]
recipe={'version':1,'units':'mm','name':'notched_plate','parameters':{'thickness':{'value':6,'min':2,'max':12,'label':'Plate thickness'},'hole_radius':{'value':4,'min':2,'max':8,'label':'Hole radius'}},'operations':[{'id':'plate','kind':'extrude','origin':[0,0,0],'plane':'xy','direction':1,'depth':'thickness','loops':[outer,[{'kind':'arc','center':[12,15],'radius':'hole_radius','start_angle':0,'end_angle':360}]]}],'output':'plate'}
(OUT/'reference.recipe.json').write_text(json.dumps(migrate_v1(recipe),indent=2))
im=Image.new('RGB',(1100,850),'white');d=ImageDraw.Draw(im);font=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',20)
def text(x,y,s):d.text((x,y),s,font=font,fill='black')
def pt(x,y):return (100+10*x,550-10*y)
text(50,25,'NOTCHED PLATE — dimensions in mm');text(100,90,'TOP (XY)')
import math
outline=[[0,0],[60,0],[60,34]]+[[54+6*math.cos(math.radians(a)),34+6*math.sin(math.radians(a))] for a in range(0,91,2)]+points
# points starts with [54,40], then defines the notch and closes the outline.
d.line([pt(*v) for v in outline],fill='black',width=3)
x,y=pt(12,15);d.ellipse((x-40,y-40,x+40,y+40),outline='black',width=3)
text(290,570,'60');text(45,330,'40');text(280,395,'Ø8 THROUGH')
text(730,170,'Top-right corner R6 only');text(730,205,'Notch: 20 wide × 10 deep');text(730,240,'Notch centred on top edge')
text(730,310,'Hole centre:');text(730,345,'12 from left edge');text(730,380,'15 from bottom edge')
text(100,640,'FRONT (XZ)');d.rectangle((100,690,700,750),outline='black',width=3);text(730,705,'6 thick')
text(100,790,'Same outline through full thickness. Flat top and bottom faces.')
im.save(OUT/'drawing.png')
