"""Known profile contract through native build, export and independent mesh sections."""
import json,shutil
from pathlib import Path
import trimesh
from doodle_to_cad.brep import build_brep
from doodle_to_cad.build_contract import BuildInput
from scripts.check_sweep_product import measure
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'docs/brep/task-10/reference';OUT.mkdir(parents=True,exist_ok=True)
report={}
for thickness in [8,10]:
 target=OUT/str(thickness);target.mkdir(exist_ok=True)
 recipe=json.loads((ROOT/'benchmarks/brep-sweeps/reference.recipe.json').read_text());recipe['parameters']['section_height']['value']=thickness
 source=target/'recipe.json';source.write_text(json.dumps(recipe,indent=2))
 result=build_brep(BuildInput('usd-brep',source,target,render=False))
 (target/'build.log').write_text(result.log);assert result.ok,result.log
 shutil.copy(result.stl,target/'part.stl')
 report[str(thickness)]=measure(target/'part.stl',thickness);assert report[str(thickness)]['passed'],report
box=trimesh.creation.box(extents=[46,38,8]);box.export(OUT/'negative-plain-box.stl')
report['negative_plain_box']=measure(OUT/'negative-plain-box.stl',8);assert not report['negative_plain_box']['passed']
(OUT/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
