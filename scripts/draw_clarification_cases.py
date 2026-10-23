"""Synthetic engineering drawings; no expected geometry is supplied in model requests."""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
out=Path('benchmarks/brep-clarification');out.mkdir(exist_ok=True)
font=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',20)
for clear in [False,True]:
 im=Image.new('RGB',(900,700),'white');d=ImageDraw.Draw(im)
 def text(x,y,s):d.text((x,y),s,font=font,fill='black')
 text(35,20,'BLOCK — dimensions in mm');text(35,55,'Body: 40 wide × 30 deep × 12 thick')
 text(70,105,'TOP (XY)');d.rectangle((70,150,470,450),outline='black',width=3)
 d.ellipse((230,260,310,340),outline='black',width=3)
 text(240,460,'40');text(20,285,'30');text(320,290,'Ø8');d.line((310,300,320,300),fill='black',width=2)
 text(70,510,'Opening centred in top face')
 if clear:
  text(530,105,'SECTION THROUGH CENTRE')
  for r in [(530,150,658,246),(722,150,850,246)]:d.rectangle(r,outline='black',width=3)
  # Section scale differs from top, explicitly dimensioned.
  text(535,300,'12 thick; Ø8 THROUGH')
  text(535,340,'No floor below opening')
 im.save(out/('clear-through.png' if clear else 'ambiguous.png'))
