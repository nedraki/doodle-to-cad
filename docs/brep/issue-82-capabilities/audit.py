"""Read-only evidence integrity gate. Does NOT certify CAD correctness (#81).

The committed seal is the trust anchor. This gate never regenerates it and
never overwrites reports on failure. It independently recomputes final-run
mesh observations and checks every generated summary against its source rows.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
sys.path.insert(0,str(ROOT))
import measure
from doodle_to_cad.brep_recipe import validate_recipe
from doodle_to_cad import targeted_edits
import cases


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def load(path):return json.loads(path.read_text())

def seal(root=HERE):
    return {p.relative_to(root).as_posix():sha(p) for p in sorted(root.rglob('*'))
            if p.is_file() and '__pycache__' not in p.parts and p.name!='MANIFEST.json'}

def check(root=HERE,recompute=True):
    manifest=load(root/'MANIFEST.json')
    actual=seal(root);assert manifest==actual,'Evidence/source seal mismatch: '+str(sorted(k for k in set(actual)|set(manifest) if actual.get(k)!=manifest.get(k))[:5])
    runs=load(root/'RUNS.json');final=root/'evidence'/runs['selected_run']
    for run_name,meta in runs['runs'].items():
        run=root/'evidence'/run_name
        plan=load(run/'plan.json');summary=load(run/'summary.json')
        assert set(summary)==set(plan['cases']),f'{run_name}: missing/unexpected case'
        assert plan['model_calls']==0
        assert set(load(run/'review.json')['decisions'])==set(plan['cases'])
        for name,c in summary.items():
            assert c==load(run/name/'case.json'),f'{run_name}/{name}: summary disagrees with case'
            attempts=c['attempts']
            disk={p.name for p in (run/name).iterdir() if p.is_dir() and p.name[:2].isdigit()}
            assert {r['attempt'] for r in attempts}==disk,f'{name}: missing/extra attempt'
            for r in attempts:
                a=run/name/r['attempt']
                assert load(a/'attempt.json')==r,f'{name}: attempt record drift'
                if r.get('stl_sha256'):assert sha(a/'model.stl')==r['stl_sha256'],f'{name}: mesh binding'
        if run!=final:
            assert meta['reason'] and meta['replaced_by'] in runs['runs']
            continue
        assert meta['status']=='selected'
        for name,c in summary.items():
            contract=plan['cases'][name]
            assert c['user_review']=='pending' and c['measurement_validation'].startswith('provisional')
            if c['outcome']!='constructed_and_edited':continue  # failures remain visible, never called success
            roles={r['role']:r for r in c['attempts']}
            assert set(roles)=={'initial','edited','rejected','continued'},f'{name}: incomplete edit lifecycle'
            assert c['preview_keeps_original_selected'] and c['continued_edit_recorded']
            assert c['rejection']['rejected'] and all(c['failure_recovery'][k] for k in
                ('selected_revision_unchanged','store_unchanged','downloads_unchanged'))
            observations={}
            for role,r in roles.items():
                if role=='rejected':continue
                a=run/name/r['attempt'];doc=load(a/'model.recipe.json')
                expected_recipe=contract['recipe']
                if role!='initial':
                    value=contract['value' if role=='edited' else 'continued']
                    if name=='pocket':expected_recipe,_=targeted_edits.plan(expected_recipe,cases.POCKET_RULE,value)
                    else:expected_recipe,_=validate_recipe(expected_recipe,{contract['edit']:value})
                expected_recipe,_=validate_recipe(expected_recipe)
                assert doc==expected_recipe,f'{name}/{role}: source differs from frozen edit request'
                obs=load(a/'mesh-observations.json');observations[role]=obs
                assert obs['expectations']==measure.compare(obs,measure.expected(name,doc)),f'{name}: expectation drift'
                assert r['observations_within_provisional_tolerances']==all(x['within_tolerance'] for x in obs['expectations'].values())
                if recompute:
                    fresh=measure.observe(name,a/'model.stl')
                    assert fresh['mesh']==obs['mesh'],f'{name}: mesh summary drift'
                    for k,v in fresh['values'].items():
                        if isinstance(v,list):assert v==obs['values'][k]
                        else:assert abs(v-obs['values'][k])<1e-8,f'{name}: scalar measurement drift {k}'
                native=load(a/'native-observations.json')
                assert r['native_measurement_available']==('volume_mm3' in native)
            before=observations['initial']['values'];after=observations['edited']['values']
            expected_preservation={k:{'before':before.get(k),'after':after.get(k),'tolerance_mm':.05,
                'within_tolerance':k in before and k in after and abs(before[k]-after[k])<=.05} for k in contract['protected']}
            assert expected_preservation==c['preservation'],f'{name}: preservation report drift'
    return {'integrity':'verified','selected_run':runs['selected_run'],
            'cases':len(load(final/'summary.json')),'geometry_validation':'pending #81','user_acceptance':'pending'}

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--seal',action='store_true',help='Explicit author action after reviewing every changed artifact')
    args=ap.parse_args()
    if args.seal:
        (HERE/'MANIFEST.json').write_text(json.dumps(seal(),indent=2)+'\n')
        print('Sealed evidence and source; this action is not validation.')
    else:
        try:print(json.dumps(check(),indent=2))
        except Exception as e:print(f'AUDIT FAILED: {e}',file=sys.stderr);sys.exit(1)
