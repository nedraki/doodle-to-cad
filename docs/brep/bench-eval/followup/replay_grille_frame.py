"""Controlled saved-response intervention for #81; never used by generation.

Only rotate the authored 2D body profile into the XZ plane stated in its
interpretation. Keep every cutter, parameter and outline point unchanged.
"""
import hashlib
import json
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[4]; sys.path.insert(0,str(ROOT))
from doodle_to_cad.openscad import compile_and_render, mesh_health
from doodle_to_cad.config import settings
HERE=Path(__file__).resolve().parent


def main():
    out=HERE/'grille-frame-replay'; out.mkdir(exist_ok=True)
    retained=out/'saved-response.scad'
    if not retained.exists():
        source=ROOT/'results/issue-81-followup-verified/d4b44ee63315/attempt-01/model.scad'
        retained.write_bytes(source.read_bytes())
    original=retained.read_text()
    needle='    linear_extrude(height = thickness, center = true) {'
    assert original.count(needle)==1
    corrected=original.replace(needle,'    rotate([90, 0, 0])\n'+needle)
    reports={}
    for name,text in [('before',original),('after',corrected)]:
        dest=out/name; dest.mkdir(exist_ok=True)
        path=dest/'model.scad'; path.write_text(text)
        stl,views,log=compile_and_render(path,dest,settings.openscad_bin)
        if stl is None: raise ValueError(log)
        reports[name]={'health':mesh_health(stl),'source_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'mesh_sha256':hashlib.sha256(stl.read_bytes()).hexdigest()}
        print(name,reports[name]['health'],flush=True)
    reports['intervention']='Manually add rotate([90,0,0]) around the body linear_extrude only. No production change or model regeneration. This tests whether generated body/cutter frames explain the missing openings.'
    reports['source_run']='d4b44ee63315/attempt-01'
    (out/'report.json').write_text(json.dumps(reports,indent=2)+'\n')
if __name__=='__main__': main()
