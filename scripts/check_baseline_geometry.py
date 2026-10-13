"""Reproduce task 01 geometry checks without changing production code."""
import hashlib
import json
import os
from importlib.metadata import version
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import time
from urllib.parse import urlsplit

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from doodle_to_cad.brep import build_recipe,worker_python
from doodle_to_cad.config import settings
from doodle_to_cad.openscad import compile_stl_only,mesh_health
from scripts.evaluate_brep import REFERENCES,EDITS

OUT=ROOT/'docs/brep/baseline-01'


def main():
    OUT.mkdir(parents=True,exist_ok=True)
    rows=[]
    for name,scad in REFERENCES.items():
        recipe=json.loads((ROOT/f'benchmarks/brep/{name}.json').read_text())
        dest=ROOT/'results/baseline-01-recipes'/name
        start=time.monotonic();built=build_recipe(dest,recipe);build_time=time.monotonic()-start
        start=time.monotonic();edited=build_recipe(dest,recipe,EDITS[name]);edit_time=time.monotonic()-start
        url,error=compile_stl_only(dest,scad,'reference',settings.openscad_bin)
        assert url,error
        health=mesh_health(dest/'reference.stl')
        assert health['watertight'] and health['components']==1
        assert all(abs(a-b)<0.05 for a,b in zip(health['extents_mm'],built['diagnostics']['extents_mm']))
        for result in (built,edited):
            assert result['diagnostics']['watertight'] and result['diagnostics']['usd_roundtrip']
        for label,result in [('base',built),('edited',edited)]:
            revision=dest/result['stl'].split('/')[-2]
            shutil.copytree(revision,OUT/'recipe-runs'/name/label,dirs_exist_ok=True)
        rows.append(dict(case=name,build=built['diagnostics'],edit=edited['diagnostics'],build_seconds=build_time,edit_seconds=edit_time,openscad=health))
    (OUT/'recipe-checks.json').write_text(json.dumps(rows,indent=2)+'\n')
    references=[]
    for path in sorted((ROOT/'benchmarks/brep-baseline').iterdir()):
        if not path.is_dir():continue
        manifest=json.loads((path/'manifest.json').read_text())
        for file,digest in manifest['sha256'].items():
            assert hashlib.sha256((path/file).read_bytes()).hexdigest()==digest
        dest=ROOT/'results/baseline-reference-checks'/path.name;dest.mkdir(parents=True,exist_ok=True)
        url,error=compile_stl_only(dest,(path/'reference.scad').read_text(),'reference',settings.openscad_bin)
        assert url,error
        health=mesh_health(dest/'reference.stl')
        assert health['watertight'] and health['components']==1,(path,health)
        tolerance=manifest['tolerances']['reference_dimension_abs_mm']
        assert all(abs(a-b)<=tolerance for a,b in zip(health['extents_mm'],manifest['dimensions_mm']['extents_xyz']))
        references.append(dict(case=path.name,health=health,reference_dimension_check='pass'))
    (OUT/'reference-checks.json').write_text(json.dumps(references,indent=2)+'\n')
    allowed=['requested_model','max_tokens','timeout','agent_max_attempts','agent_accept_score','enable_thinking','structured_enable_thinking','code_enable_thinking','code_max_tokens','openscad_bin']
    record={key:getattr(settings,key) for key in allowed}
    record.update(python=sys.version,platform=platform.platform(),worker=worker_python(),tested_commit=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),model_host=urlsplit(settings.base_url).hostname)
    record['worker_packages']=json.loads(subprocess.check_output(['uv','pip','list','--python',worker_python(),'--format','json'],text=True))
    record['application_packages']={name:version(name) for name in ['fastapi','httpx','numpy','trimesh','networkx','pillow','playwright']}
    record['openscad_docker_image']=os.getenv('DOODLE_OPENSCAD_DOCKER')
    if record['openscad_docker_image']:
        record['openscad_docker_image_id']=subprocess.check_output(['docker','image','inspect',record['openscad_docker_image'],'--format','{{.Id}}'],text=True).strip()
    (OUT/'environment.json').write_text(json.dumps(record,indent=2)+'\n')
    print('PASS: three BRep builds and edits; three SCAD equivalents; five reference solids.')

if __name__=='__main__':main()
