"""Draw synthetic engineering fixtures for issue 42. No CAD or model calls."""
from pathlib import Path
import math
from PIL import Image, ImageDraw, ImageFont
ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'benchmarks/brep-features'
FONT = '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
def sheet(name):
    im=Image.new('RGB',(1200,800),'white'); d=ImageDraw.Draw(im)
    text=lambda xy,t,size=22:d.text(xy,t,font=ImageFont.truetype(FONT,size),fill='black')
    text((35,20),name,28);text((35,62),'Synthetic engineering drawing | dimensions in mm',18)
    return im,d,text

def save(im,name):
    p=OUT/name;p.mkdir(parents=True,exist_ok=True);im.save(p/'drawing.png')

def main():
    im,d,t=sheet('ROUNDED HOUSING BLANK')
    t((70,130),'TOP (XY)');t((650,130),'FRONT (XZ)')
    d.rounded_rectangle((70,210,550,510),radius=36,outline='black',width=3)
    d.rectangle((650,210,1130,390),outline='black',width=3)
    for x in (686,1094):d.line((x,210,x,390),fill='black',width=2)
    t((240,535),'80');t((20,345),'50');t((820,415),'80');t((1140,285),'30')
    d.line([(86,225),(130,195),(300,195)],fill='black',width=2);t((145,165),'4 corners: R6')
    t((70,610),'Solid blank. Same corner shape through the full height.')
    t((70,650),'Top and bottom perimeter edges remain sharp. No cavity.')
    save(im,'rounded_housing')
    im,d,t=sheet('BEVELLED BLOCK')
    t((70,130),'TOP (XY)');t((650,130),'FRONT (XZ)')
    for x,y,w,h in [(70,210,480,320),(650,210,480,160)]:
        c=16
        d.line([(x+c,y),(x+w-c,y),(x+w,y+c),(x+w,y+h-c),(x+w-c,y+h),(x+c,y+h),(x,y+h-c),(x,y+c),(x+c,y)],fill='black',width=3)
        d.rectangle((x+c,y+c,x+w-c,y+h-c),outline='black',width=2)
    t((250,550),'60');t((20,350),'40');t((830,395),'60');t((1140,270),'20')
    t((70,630),'All edges: 2 mm x 45 degrees. Solid block.')
    t((70,675),'Outer dimensions: 60 x 40 x 20.')
    save(im,'bevelled_block')
    im,d,t=sheet('CURVED HANDLE - RECTANGULAR SECTION')
    t((80,130),'TOP (XY)');t((770,130),'END SECTION')
    # Tangent-continuous S path: straight, quarter circle, opposite quarter circle, straight.
    path=[((0,-10),(-1,0)),((0,0),(-1,0))]
    for i in range(1,65):
        a=math.pi-i*math.pi/128;path.append(((20+20*math.cos(a),20*math.sin(a)),(math.cos(a),math.sin(a))))
    for i in range(1,65):
        a=-math.pi/2+i*math.pi/128;path.append(((20+20*math.cos(a),40+20*math.sin(a)),(-math.cos(a),-math.sin(a))))
    path.append(((40,50),(-1,0)))
    def xy(p):return (180+7*p[0],570-7*p[1])
    sides=[]
    for sign in (1,-1):sides.append([xy((p[0]+sign*3*n[0],p[1]+sign*3*n[1])) for p,n in path])
    contour=sides[0]+list(reversed(sides[1]));d.line(contour+[contour[0]],fill='black',width=3)
    points=[xy(p) for p,_ in path]
    for i in range(0,len(points)-1,4):d.line(points[i:i+3],fill='gray',width=1)
    d.rectangle((820,260,940,340),outline='black',width=3)
    t((867,365),'6');t((960,285),'4');t((760,420),'6 wide in the path plane')
    t((760,460),'4 thick normal to the plane')
    t((80,665),'Two opposite quarter bends: centreline R20 each. Straight ends: 10 each.')
    t((80,710),'End centre offset: X=40, Y=60. Constant section. Ends capped.')
    save(im,'rectangular_sweep')
if __name__=='__main__':main()
