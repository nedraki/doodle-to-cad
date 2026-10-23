"""Offline orthographic mesh renders and true section overlays, using Pillow.
No model calls, screenshots of other runs, or reconstructed evidence images.
"""
import argparse,html,json,math
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw,ImageFont
import trimesh

FONT='/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
def font(size):return ImageFont.truetype(FONT,size)
BLUE=(35,102,160);ORANGE=(211,105,35);INK=(32,44,57)

def title(draw,xy,text,size=20):draw.text(xy,text,font=font(size),fill=INK)

def project(points):
    # Fixed orthographic camera shared by BEFORE and AFTER.
    matrix=np.array([[.866,-.5,0],[.25,.433,.866],[.433,.75,-.5]])
    return np.asarray(points)@matrix.T

def view(draw,rect,mesh,color,bounds):
    pts=project(mesh.vertices);lo,hi=bounds
    x0,y0,x1,y1=rect;scale=min((x1-x0)/(hi[0]-lo[0]),(y1-y0)/(hi[1]-lo[1]))*.9
    xy=(pts[:,:2]-(lo[:2]+hi[:2])/2)*scale
    xy[:,0]+=(x0+x1)/2;xy[:,1]=(y0+y1)/2-xy[:,1]
    normals=mesh.face_normals
    light=np.array([-.3,-.5,1.]);light/=np.linalg.norm(light)
    order=np.argsort(pts[mesh.faces,2].mean(axis=1))[::-1]
    for i in order:
        shade=.55+.45*abs(float(normals[i]@light))
        c=tuple(int(v*shade) for v in color)
        draw.polygon([tuple(p) for p in xy[mesh.faces[i]]],fill=c)

def curves(draw,rect,groups,axes=(0,1)):
    points=[np.asarray(p)[:,axes] for loops,col in groups for p in loops if len(p)>1]
    if not points:return
    allp=np.concatenate(points);lo=allp.min(axis=0);hi=allp.max(axis=0)
    x0,y0,x1,y1=rect;scale=min((x1-x0)/max(hi[0]-lo[0],1),(y1-y0)/max(hi[1]-lo[1],1))*.9
    for loops,col in groups:
        for p in loops:
            q=(np.asarray(p)[:,axes]-(lo+hi)/2)*scale
            q[:,0]+=(x0+x1)/2;q[:,1]=(y0+y1)/2-q[:,1]
            draw.line([tuple(v) for v in q],fill=col,width=2)

def panel(run,name,data):
    case_dir=run/name
    records={r['role']:r for r in data['attempts'] if r.get('stl_sha256')}
    before=case_dir/records['initial']['attempt'] if 'initial' in records else None
    after=case_dir/records['edited']['attempt'] if 'edited' in records else None
    image=Image.new('RGB',(1400,920),(247,249,251));d=ImageDraw.Draw(image)
    case=json.loads((run/'plan.json').read_text())['cases'][name]
    title(d,(30,20),f'{name.upper()} | manually authored construction / edit',28)
    title(d,(30,65),f'Request: {case["edit"]} -> {case["value"]} mm; then -> {case["continued"]} mm',20)
    title(d,(30,100),'Provisional measurements. User visual review and #81 validation are pending.',17)
    if not before:
        title(d,(30,180),data.get('error',data['outcome']));image.save(case_dir/'review.png');return
    meshes=[trimesh.load(p/'model.stl',force='mesh') for p in [before,after] if p]
    xyz=project(np.concatenate([m.vertices for m in meshes]));bounds=(xyz.min(axis=0),xyz.max(axis=0))
    title(d,(40,145),'BEFORE — exported STL',21);view(d,(30,180,680,480),meshes[0],BLUE,bounds)
    title(d,(740,145),'AFTER — exported STL' if after else 'EDIT NOT RECORDED',21)
    if after:view(d,(720,180,1370,480),meshes[1],ORANGE,bounds)
    obs=[]
    for p in [before,after]:
        if p and (p/'mesh-observations.json').exists():obs.append(json.loads((p/'mesh-observations.json').read_text()))
    if obs:
        title(d,(30,510),'XY mid-section: before blue / after orange',19)
        groups=[(list(o['xy_sections'].values())[2],col) for o,col in zip(obs,[BLUE,ORANGE])]
        curves(d,(30,550,660,820),groups)
        title(d,(720,510),'XZ centre-section: before blue / after orange',19)
        curves(d,(720,550,1370,820),[(o['xz_section'],col) for o,col in zip(obs,[BLUE,ORANGE])],(0,2))
    title(d,(30,850),'Same camera and scale. Section overlays reveal changed geometry; see raw measurements for dimensions.',16)
    title(d,(30,880),f'Outcome: {data["outcome"]} | native USD and STL are separate artifacts; neither implies user acceptance.',16)
    image.save(case_dir/'review.png')
    # Dedicated sections, including loft intermediates and local fillet/chamfer intersections.
    if obs:
        image=Image.new('RGB',(1400,850),(247,249,251));d=ImageDraw.Draw(image)
        title(d,(30,20),f'{name.upper()} | matching section close-ups',28)
        for idx in range(5):
            col=idx%3;row=idx//3;rect=(20+col*460,120+row*350,450+col*460,410+row*350)
            key=list(obs[0]['xy_sections'])[idx]
            title(d,(rect[0],rect[1]-35),f'XY at Z={key} mm',18)
            curves(d,rect,[(list(o['xy_sections'].values())[idx],c) for o,c in zip(obs,[BLUE,ORANGE])])
        title(d,(30,810),'Blue = before; orange = edited. Triangular mesh plane intersections, not illustrative sketches.',17)
        image.save(case_dir/'sections.png')

def comparison(run,name):
    folder=run/name
    a=folder/'02-edited/model.stl';b=folder/'openscad-edited/model.stl'
    if not (a.exists() and b.exists()):return False
    meshes=[trimesh.load(p,force='mesh') for p in (a,b)]
    xyz=project(np.concatenate([m.vertices for m in meshes]));bounds=(xyz.min(axis=0),xyz.max(axis=0))
    image=Image.new('RGB',(1400,850),(247,249,251));d=ImageDraw.Draw(image)
    title(d,(30,20),f'{name.upper()} | manual constructions, edited state',28)
    title(d,(30,65),'BRep export — blue',21);title(d,(740,65),'OpenSCAD export — orange',21)
    for mesh,col,rect in zip(meshes,[BLUE,ORANGE],[(30,100,680,430),(720,100,1370,430)]):
        view(d,rect,mesh,col,bounds)
    obs=[json.loads((p.parent/'mesh-observations.json').read_text()) for p in (a,b)]
    title(d,(30,465),'XY mid-section overlay',20);title(d,(720,465),'XZ centre-section overlay',20)
    curves(d,(30,510,680,760),[(list(o['xy_sections'].values())[2],c) for o,c in zip(obs,[BLUE,ORANGE])])
    curves(d,(720,510,1370,760),[(o['xz_section'],c) for o,c in zip(obs,[BLUE,ORANGE])],(0,2))
    title(d,(30,800),'Same camera and scale. Loft correspondence differs: these are not claimed to be identical native surfaces.',16)
    image.save(folder/'comparison.png');return True

def main():
    ap=argparse.ArgumentParser();ap.add_argument('run',type=Path);a=ap.parse_args();run=a.run.resolve()
    data=json.loads((run/'summary.json').read_text());plan=json.loads((run/'plan.json').read_text())
    lines=['<!doctype html><meta charset="utf-8"><title>BRep capability review — issue 82</title>',
        '<style>body{font:16px system-ui;max-width:1300px;margin:36px auto;color:#202c39;background:#f7f9fb}img{width:100%}table{border-collapse:collapse}td,th{padding:8px;border:1px solid #ccd5dd}pre{white-space:pre-wrap}section{margin:48px 0}a{color:#2366a0}</style>',
        '<h1>BRep construction and edit review</h1><p>Manual fixtures only. No model calls. Measurements are provisional until #81; user acceptance is pending. All failed attempts are retained.</p>',
        '<p>Read <a href="plan.json">the frozen input contracts</a>, <a href="summary.json">all outcomes</a>, and <a href="review.json">the unfilled user review record</a>.</p>']
    for name,case in data.items():
        panel(run,name,case);has_comparison=comparison(run,name);contract=plan['cases'][name]
        lines += [f'<section><h2>{html.escape(name)}</h2><p>{html.escape(contract["note"])}</p>',
            f'<p><b>Input:</b> {html.escape(contract["recipe"]["name"])}. <b>Requested edit:</b> {html.escape(contract["edit"])} → {contract["value"]} mm.</p>',
            f'<p><b>Protected:</b> {html.escape(", ".join(contract["protected"]))}</p>',
            f'<img src="{name}/review.png" alt="{name} before and after with matching sections">',
            f'<p><a href="{name}/sections.png">Section close-ups</a> · <a href="{name}/case.json">Build, selection and recovery record</a></p>',
            '<table><tr><th>Attempt</th><th>Build</th><th>Time (s)</th><th>Artifacts / measurements</th></tr>']
        for r in case['attempts']:
            base=f'{name}/{r["attempt"]}'
            links=f'<a href="{base}/attempt.json">record</a>'
            if r.get('stl_sha256'):
                links+=f' · <a href="{base}/model.stl">STL</a> · <a href="{base}/model.usda">native USD</a> · <a href="{base}/mesh-observations.json">mesh</a> · <a href="{base}/native-observations.json">native</a>'
            lines.append(f'<tr><td>{r["role"]}</td><td>{r.get("build_ok")}</td><td>{r.get("seconds","n/a")}</td><td>{links}</td></tr>')
        lines+=['</table><h3>OpenSCAD comparison</h3>',f'<pre>{html.escape(json.dumps(case.get("openscad"),indent=2))}</pre>',
                (f'<img src="{name}/comparison.png" alt="Edited BRep and OpenSCAD comparison"><p><a href="{name}/openscad-initial/model.scad">Initial OpenSCAD source</a> · <a href="{name}/openscad-edited/model.scad">Edited OpenSCAD source</a> · <a href="{name}/openscad-edited/model.stl">Edited OpenSCAD STL</a></p>' if has_comparison else ''),
                '<p><b>User decision:</b> pending — inspect shape, section quality, and usefulness independently of the automatic observations.</p></section>']
    (run/'review.html').write_text('\n'.join(lines)+'\n')
if __name__=='__main__':main()
