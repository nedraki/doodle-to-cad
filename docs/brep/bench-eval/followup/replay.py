"""Re-score archived bytes; never rewrite a frozen row."""
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
from scripts.bench_orientation import evaluate_orientation
from scripts.evaluate_brep import reference_checks
from doodle_to_cad.feature_evidence import view_assignment_evidence

HERE = Path(__file__).resolve().parent
ARCHIVE = HERE.parents[1] / 'bench-final'
PLAN = json.loads((ARCHIVE / 'TRIAL-PLAN.json').read_text())
ITEMS = {i['id']: i for i in PLAN['corpus']}
# Cases declared before replay: correct plate/control, wrong bracket and wheel.
CELLS = [('004_flat_mounting_plate','usd-brep',1), ('004_flat_mounting_plate','openscad',1),
         ('007_angle_bracket_holes','usd-brep',1), ('wheel','usd-brep',2)]


def main():
    records = []
    for case, backend, trial in CELLS:
        cell = ARCHIVE / 'runs' / case / backend / f'trial-{trial:02d}'
        row_path = cell/'row.json'; row = json.loads(row_path.read_text())
        mesh = cell/'stl/model.stl'
        digest = hashlib.sha256(mesh.read_bytes()).hexdigest()
        if digest != row['build']['sha256']:
            raise ValueError(f'Mesh hash mismatch: {cell}')
        result = json.loads((cell/'result.json').read_text())
        evidence = result.get('geometry')
        if backend == 'usd-brep':
            evidence = view_assignment_evidence(json.loads((cell/'geometry.json').read_text()))
        item = ITEMS[case]
        # Use actual archived input, not a potentially changed corpus PNG.
        source = (cell/'input.png').read_bytes()
        request = json.loads((cell/'request.json').read_text())
        if hashlib.sha256(source).hexdigest() != request['image_sha256']:
            raise ValueError(f'Input hash mismatch: {cell}')
        out = HERE/'replay'/case/backend/f'trial-{trial:02d}'
        orientation = evaluate_orientation(mesh, source, evidence, out, item['primary_view'])
        record = {'case':case, 'backend':backend, 'trial':trial,
                  'source_row':str(row_path.relative_to(ROOT)),
                  'source_row_sha256':hashlib.sha256(row_path.read_bytes()).hexdigest(),
                  'mesh_sha256':digest,'input_sha256':request['image_sha256'],
                  'historical_fidelity':row['fidelity'],
                  'supplied_dimension_pass':reference_checks(row['build'], {}, item['dimension'])[0]['supplied_dimension_pass'],
                  'orientation':orientation}
        (out/'report.json').write_text(json.dumps(record,indent=2)+'\n'); records.append(record)
        print(case, backend, 'identity', orientation['identity']['scores'], 'registered',orientation['registered']['scores'], flush=True)
    (HERE/'replay.json').write_text(json.dumps(records,indent=2)+'\n')

if __name__ == '__main__': main()
