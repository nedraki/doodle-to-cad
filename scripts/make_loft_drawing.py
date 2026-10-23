"""Dimensioned profile and side views for the rectangular-to-round solid."""
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
OUT=Path('benchmarks/brep-lofts');OUT.mkdir(exist_ok=True)
im=Image.new('RGB',(1200,900),'white');d=ImageDraw.Draw(im);font=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',21)
def text(x,y,s):d.text((x,y),s,font=font,fill='black')
text(40,25,'SOLID TRANSITION — all dimensions in mm')
text(70,95,'END A — rectangle, XY at Z=0');d.rectangle((110,170,430,410),outline='black',width=3);text(240,430,'40');text(60,275,'30')
text(630,95,'END B — circle, XY at Z=50');d.ellipse((720,210,880,370),outline='black',width=3);text(900,280,'Ø20')
text(80,480,'FRONT (XZ) — outer silhouette')
d.line([(150,800),(390,800),(330,500),(210,500),(150,800)],fill='black',width=3)
text(405,640,'50 long along Z');text(240,820,'40');text(235,530,'20')
text(630,490,'Both profiles have the same XY centre.');text(630,535,'Rectangle sides are parallel to X and Y.');text(630,580,'Smooth transition; no twist.');text(630,625,'Solid throughout. No cavity or holes.');text(630,670,'Flat closed ends.');text(630,730,'Change in outline is along Z.');text(630,775,'Rectangle at bottom; circle at top.')
im.save(OUT/'drawing.png')
