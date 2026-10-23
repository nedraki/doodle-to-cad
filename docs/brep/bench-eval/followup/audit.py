"""Seal or verify the follow-up package; audit does not regenerate evidence."""
import argparse
import hashlib
import json
import sys
from pathlib import Path
HERE=Path(__file__).resolve().parent; ROOT=HERE.parents[3]
sys.path.insert(0,str(ROOT))
from scripts.evaluate_brep import _measure_stl, reference_checks, overall_checks


def hashes():
    return {p.relative_to(HERE).as_posix():hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(HERE.rglob('*')) if p.is_file() and '__pycache__' not in p.parts
            and p.name not in ('MANIFEST.json','audit-result.json')}


def verify():
    plan=json.loads((HERE/'TRIAL-PLAN.json').read_text())
    expected={(i['id'],b,t) for i in plan['corpus'] for b in ('openscad','usd-brep') for t in (1,2)}
    seen=set(); items={i['id']:i for i in plan['corpus']}
    from datetime import datetime
    revision=datetime.fromisoformat(plan['plan_revisions'][-1]['at'])
    for path in sorted((HERE/'runs').glob('*/*/trial-*/row.json')):
        row=json.loads(path.read_text()); cell=path.parent
        key=(row['drawing'],row['backend'],row['trial'])
        assert key not in seen, f'Duplicate {key}'
        seen.add(key)
        assert cell == HERE/'runs'/key[0]/key[1]/f'trial-{key[2]:02d}', f'Wrong path: {key}'
        request=json.loads((cell/'request.json').read_text()); item=items[key[0]]
        assert request['form']['dimension']==item['dimension']
        assert request['form']['notes']==item['notes']
        assert request['reference_geometry_sent'] is False
        assert hashlib.sha256((cell/'input.png').read_bytes()).hexdigest()==request['image_sha256']==plan['input_hashes'][item['drawing']]
        env=json.loads((cell/'environment.json').read_text())
        assert env['server_model']==plan['model_settings']['selected_model']
        assert env['model_settings']['structured_enable_thinking'] is False
        assert env['model_settings']['code_enable_thinking'] is False
        assert datetime.fromisoformat(row['submitted_at']) >= revision
        measurement=None
        if (row.get('build') or {}).get('sha256'):
            mesh=cell/'stl/model.stl'
            assert hashlib.sha256(mesh.read_bytes()).hexdigest()==row['build']['sha256']
            measurement=_measure_stl(mesh)
        calculated=reference_checks(measurement,{},item['dimension'])[0]['supplied_dimension_pass']
        assert row['checks']['supplied_dimension_pass']==calculated, f'Dimension drift {key}'
        assert row['checks']['overall_pass']==overall_checks(row['checks']), f'Overall drift {key}'
    assert seen==expected, f'Cell mismatch: missing {expected-seen}, unexpected {seen-expected}'
    print(f'PASS: {len(seen)} exact cells, input hashes, request provenance, model, timestamps, independent mesh dimensions and unchanged overall definition')


def main():
    parser=argparse.ArgumentParser(); parser.add_argument('--seal',action='store_true'); args=parser.parse_args()
    verify()
    path=HERE/'MANIFEST.json'
    if args.seal:
        if path.exists(): raise ValueError('Refusing to replace a seal; publish a documented revision')
        path.write_text(json.dumps(hashes(),indent=2)+'\n')
    else:
        expected=json.loads(path.read_text()); actual=hashes()
        bad=[k for k in set(expected)|set(actual) if expected.get(k)!=actual.get(k)]
        if bad: raise ValueError(f'Evidence hash mismatch: {bad}')
    print('PASS: follow-up evidence seal')
if __name__=='__main__': main()
