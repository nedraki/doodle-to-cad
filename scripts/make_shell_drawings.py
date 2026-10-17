"""Rounded open tray with a section; clear and missing-thickness variants."""
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
OUT=Path('benchmarks/brep-shells');OUT.mkdir(exist_ok=True)
for unknown in [False,True]:
 im=Image.new('RGB',(1200,930),'white');d=ImageDraw.Draw(im);font=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',21)
 def text(x,y,s):d.text((x,y),s,font=font,fill='black')
 text(40,20,'ROUNDED OPEN TRAY — dimensions in mm');text(100,65,'TOP (XY)')
 d.rounded_rectangle((100,120,700,520),radius=60,outline='black',width=3);d.rounded_rectangle((120,140,680,500),radius=40,outline='black',width=3)
 text(380,540,'60');text(50,300,'40');text(750,150,'Outer vertical corners: R6');text(750,195,'Outside: 60 × 40 × 20');text(750,240,'Open top. No lid.');text(750,285,'Flat top rim and outside floor.')
 if unknown:
  text(750,345,'Same wall and floor thickness.');text(750,390,'Thickness value is not given.')
 else:
  text(750,345,'Uniform wall thickness: 2');text(750,390,'Floor thickness: 2')
 text(100,590,'SECTION XZ — through the middle')
 d.line([(100,650),(100,850),(700,850),(700,650),(680,650),(680,830),(120,830),(120,650),(100,650)],fill='black',width=3)
 text(350,715,'EMPTY');text(750,650,'Height: 20');text(750,700,'Keep all outside dimensions.');text(750,750,'Change wall and floor together.');text(350,875,'60')
 im.save(OUT/('missing-thickness.png' if unknown else 'drawing.png'))
