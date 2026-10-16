"""Known profile contract through native build, export and independent mesh sections."""
import json,shutil
from pathlib import Path
import trimesh
from doodle_to_cad.brep import build_brep
from doodle_to_cad.build_contract import BuildInput
from scripts.check_profile_product import measure
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'docs/brep/task-09/reference';OUT.mkdir(parents=True,exist_ok=True)
report={}
for thickness in [6,10]:
 target=OUT/str(thickness);target.mkdir(exist_ok=True)
 recipe=json.loads((ROOT/'benchmarks/brep-profiles/reference.recipe.json').read_text());recipe['parameters']['thickness']['value']=thickness
 source=target/'recipe.json';source.write_text(json.dumps(recipe,indent=2))
 result=build_brep(BuildInput('usd-brep',source,target,render=False))
 (target/'build.log').write_text(result.log);assert result.ok,result.log
 shutil.copy(result.stl,target/'part.stl')
 report[str(thickness)]=measure(target/'part.stl',thickness);assert report[str(thickness)]['passed'],report
box=trimesh.creation.box(extents=[60,40,6]);box.export(OUT/'negative-plain-box.stl')
report['negative_plain_box']=measure(OUT/'negative-plain-box.stl',6);assert not report['negative_plain_box']['passed']
(OUT/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
