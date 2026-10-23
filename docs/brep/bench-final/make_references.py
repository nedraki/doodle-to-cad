"""Generate references/reference-measurements.json for the bench-final plan.

Benchmark cases: measured from each case's ground_truth/model.stl with
trimesh (euler_number -> genus). Feature drawings without a trusted STL get
kind=no_ground_truth so extents/genus/volume checks are recorded as n/a,
never guessed. Reuses the #34 reference file for the six baseline drawings
whose STLs it already certifies.
"""
import json
import shutil
from pathlib import Path

import trimesh

ROOT = Path(__file__).resolve().parents[3]  # repo root: never a hard-coded author dir
HERE = Path(__file__).resolve().parent
plan = json.loads((HERE / 'TRIAL-PLAN.json').read_text())
base34 = json.loads((ROOT / 'docs/brep/task-17-comparison/references/reference-measurements.json').read_text())

refdir = HERE / 'references'
refdir.mkdir(exist_ok=True)
for f in (ROOT / 'docs/brep/task-17-comparison/references').glob('*.stl'):
    shutil.copy2(f, refdir / f.name)

refs = {}
for item in plan['corpus']:
    iid = item['id']
    stl = ROOT / 'benchmarks/cases' / iid / 'ground_truth' / 'model.stl'
    base_name = iid.split('_', 1)[-1] if iid[0].isdigit() else iid
    if stl.is_file():
        m = trimesh.load(stl, force='mesh')
        genus = (2 - m.euler_number) // 2
        refs[iid] = {'kind': 'ground_truth_stl', 'source': str(stl.relative_to(ROOT)),
                     'watertight': bool(m.is_watertight), 'components': int(m.is_watertight and 1 or len(m.split(only_watertight=False))),
                     'extents_mm': [round(v, 2) for v in m.extents],
                     'volume_mm3': round(float(m.volume), 1), 'genus': int(genus)}
    elif iid in base34:
        refs[iid] = base34[iid]
    else:
        alias = {"solid_transition": "transition", "constant_radius_handle": "curved_handle"}.get(iid, base_name)
        if (refdir / f'{alias}-reference.stl').is_file():
            base_name = alias
    if iid not in refs and (refdir / f'{base_name}-reference.stl').is_file():
        m = trimesh.load(refdir / f'{base_name}-reference.stl', force='mesh')
        refs[iid] = {'kind': 'openscad_reference', 'source': f'references/{base_name}-reference.stl',
                     'watertight': bool(m.is_watertight), 'components': 1,
                     'extents_mm': [round(v, 2) for v in m.extents],
                     'volume_mm3': round(float(m.volume), 1), 'genus': int((2 - m.euler_number) // 2)}
    if iid not in refs:
        refs[iid] = {'kind': 'no_ground_truth',
                     'note': 'feature contract drawing (#42/#43); shape checks n/a, build+gates still scored'}
(HERE / 'references' / 'reference-measurements.json').write_text(json.dumps(refs, indent=2) + '\n')
kinds = {}
for v in refs.values():
    kinds[v['kind']] = kinds.get(v['kind'], 0) + 1
print(len(refs), 'references |', kinds)
