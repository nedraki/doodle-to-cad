"""Apply drawing checks to saved candidates. No generation or recipe substitution."""
import json
from pathlib import Path
from doodle_to_cad.brep_checks import evaluate_drawing
from doodle_to_cad.feature_evidence import view_assignment_evidence
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'docs/brep/task-07'
source=ROOT/'docs/brep/task-06/correction-01'
report={}
for name in ['wheel','bookend','knob','random']:
    run=next((source/name/'artifacts').iterdir())
    result=json.loads((run/'result.json').read_text())
    views={name:run/Path(url).relative_to('/results/'+run.name) for name,url in result['files']['views'].items()}
    geometry=view_assignment_evidence(json.loads((run/'geometry.json').read_text()))
    checks=evaluate_drawing((run/'input.png').read_bytes(),geometry,views,result['build']['measurements'],result['controls'],120)
    result['evaluation']=checks
    report[name]={'run':run.name,'checks':checks}
    (OUT/(name+'-checked-result.json')).write_text(json.dumps(result,indent=2)+'\n')
(OUT/'saved-drawing-report.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({k:{'status':v['checks']['status'],'failures':v['checks']['failures']} for k,v in report.items()},indent=2))
