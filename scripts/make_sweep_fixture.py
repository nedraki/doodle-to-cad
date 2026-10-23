"""Rectangular-section bent handle; recipe is never input to the model."""
import json,math
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
from doodle_to_cad.construction_recipe import migrate_v1
OUT=Path('benchmarks/brep-sweeps');OUT.mkdir(exist_ok=True)
r={'version':1,'units':'mm','name':'rectangular_handle','parameters':{'section_width':{'value':6,'min':2,'max':10},'section_height':{'value':8,'min':2,'max':12}},'operations':[{'id':'handle','kind':'sweep','origin':[0,0,0],'plane':'xy','frame_rule':'normal_to_path_z_up','section_width':'section_width','section_height':'section_height','path':[{'kind':'line','start':[43,0],'end':[43,15]},{'kind':'arc','center':[23,15],'radius':20,'start_angle':0,'end_angle':180},{'kind':'line','start':[3,15],'end':[3,0]}]}],'output':'handle'}
(OUT/'reference.recipe.json').write_text(json.dumps(migrate_v1(r),indent=2))
im=Image.new('RGB',(1100,850),'white');d=ImageDraw.Draw(im);font=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',20)
def text(x,y,s):d.text((x,y),s,font=font,fill='black')
def pt(x,y):return (100+12*x,570-12*y)
points=[[46,0],[46,15]]+[[23+23*math.cos(math.radians(a)),15+23*math.sin(math.radians(a))] for a in range(0,181,2)]+[[0,0],[6,0],[6,15]]+[[23+17*math.cos(math.radians(a)),15+17*math.sin(math.radians(a))] for a in range(180,-1,-2)]+[[40,0],[46,0]]
d.line([pt(*v) for v in points],fill='black',width=3)
text(45,25,'BENT HANDLE — all dimensions in mm');text(100,70,'TOP (XY)')
text(710,150,'180° bend');text(710,190,'Centreline radius R20');text(710,230,'Inner radius R17');text(710,270,'Outer radius R23');text(710,330,'Both straight ends: 15 long');text(710,370,'Same 6 × 8 section throughout');text(710,410,'Flat ends. No holes.');text(710,450,'No rounding of section corners.')
text(300,595,'Overall width: 46');text(100,640,'END SECTION — rectangle')
d.rectangle((150,690,222,786),outline='black',width=3);text(175,805,'6');text(240,730,'8 (Z height)')
text(550,700,'One solid part.');text(550,740,'Bend and straight ends lie in XY.');text(550,780,'Section remains upright along Z.')
im.save(OUT/'drawing.png')
