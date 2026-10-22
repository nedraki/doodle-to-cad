"""Render evidence montages from archived images; no generated geometry."""
import json
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageOps
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
FONT = '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
font = ImageFont.truetype(FONT, 21)
small = ImageFont.truetype(FONT, 17)


def panel(canvas, path, xy, size=(340,270)):
    image = Image.open(path).convert('RGB')
    image = ImageOps.contain(image, size)
    x,y=xy
    canvas.paste(image,(x+(size[0]-image.width)//2,y+(size[1]-image.height)//2))


def main():
    canvas = Image.new('RGB',(1480,850),'#f3f5f7'); d=ImageDraw.Draw(canvas)
    d.text((24,18),'Issue 81: before / after view registration — identical CAD mesh',font=font,fill='#17212b')
    d.text((24,51),'Black regions are projected material. Alignment changes the comparison, not the generated part.',font=small,fill='#405469')
    for row, (case,backend,trial,label) in enumerate([
        ('004_flat_mounting_plate','usd-brep',1,'Plate with expected openings: registration explains the mismatch'),
        ('007_angle_bracket_holes','usd-brep',1,'Wrong flat bracket: registration does not restore the missing bend')]):
        y=100+row*360; d.text((24,y),label,font=font,fill='#17212b')
        base=HERE/'replay'/case/backend/f'trial-{trial:02d}'
        archive=ROOT/'docs/brep/bench-final/runs'/case/backend/f'trial-{trial:02d}'
        report=json.loads((base/'report.json').read_text())['orientation']
        for col,(path,title) in enumerate([(archive/'input.png','Original drawing'),(archive/'views/isometric.png','Generated CAD (unchanged)'),(base/'front-identity.png',f"Before: front IoU {report['identity']['scores']['front']:.3f}"),(base/'front-registered.png',f"After: front IoU {report['registered']['scores']['front']:.3f}")]):
            x=24+col*365; d.text((x,y+33),title,font=small,fill='#405469'); panel(canvas,path,(x,y+60))
    d.text((24,817),'Diagnostic only. One rotation fits all views; these IoU values are not the historical acceptance score.',font=small,fill='#405469')
    canvas.save(HERE/'before-after.png')
if __name__=='__main__': main()
