"""Collect append-only manual construction/edit evidence. Never calls a model.

Run from repository root with product Python; set DOODLE_BREP_PYTHON to the
isolated worker. --out must not exist. All failed attempts remain archived.
The production revision/selection state machine is exercised directly;
only its build adapter omits product screenshots (offline views are separate).
"""
import argparse
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import time

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
sys.path.insert(0,str(ROOT))
import cases
import measure
from doodle_to_cad.brep import build_brep, worker_python
from doodle_to_cad.brep_recipe import validate_recipe, recipe_params
from doodle_to_cad.build_contract import BuildInput
from doodle_to_cad import revisions, feature_selection, targeted_edits, openscad


def write(path,data):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(data,indent=2,allow_nan=False)+'\n')

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()

def collect(name,case,directory):
    directory.mkdir()
    session=directory/'session';session.mkdir()
    records=[];role='initial'
    def local(url):return session/Path(url).relative_to('/results/'+session.name)
    def adapter(out,recipe,updates=None):
        attempt=directory/f'{len(records)+1:02d}-{role}';attempt.mkdir()
        record={'role':role,'backend':'usd-brep','updates':updates or {},'attempt':attempt.name}
        records.append(record)
        write(attempt/'requested.recipe.json',recipe)
        start=time.monotonic()
        try:
            doc,_=validate_recipe(recipe,updates)
            write(attempt/'resolved.recipe.json',doc)
            result=build_brep(BuildInput('usd-brep',attempt/'resolved.recipe.json',out,render=False))
            record.update(build_ok=result.ok,seconds=round(time.monotonic()-start,4),
                          diagnostics=[vars(d) for d in result.diagnostics])
            (attempt/'worker.log').write_text(result.log)
            if not result.ok:return {'ok':False}
            for file,key in [(result.stl,'model.stl'),(result.source,'model.recipe.json'),(result.exports['usd'],'model.usda')]:
                shutil.copyfile(file,attempt/key)
            write(attempt/'diagnostics.json',result.backend_details)
            record['stl_sha256']=sha(attempt/'model.stl')
            obs=measure.observe(name,attempt/'model.stl')
            obs['expectations']=measure.compare(obs,measure.expected(name,doc))
            write(attempt/'mesh-observations.json',obs)
            native=subprocess.run([worker_python(),str(HERE/'native_probe.py'),str(attempt/'model.usda')],
                                  capture_output=True,text=True,timeout=90,
                                  env={k:v for k,v in os.environ.items() if k not in {"PYTHONPATH","PYTHONHOME"}})
            (attempt/'native-probe.log').write_text(native.stderr)
            try:
                native_data=json.loads(native.stdout) if native.returncode==0 else {'unavailable':native.stderr[-1500:]}
            except json.JSONDecodeError:
                native_data={'unavailable':'Probe returned invalid JSON','stdout':native.stdout[-1500:]}
            if 'volume_mm3' in native_data:
                native_data['mesh_volume_relative_error']=abs(native_data['volume_mm3']-obs['mesh']['volume_mm3'])/native_data['volume_mm3']
                if name in ('fillet','shell','combined'):
                    loops=list(native_data['xy_sections'].values())[2]
                    try:
                        native_data['sampled_outer_radius_mm']=measure.corner_radius([__import__('numpy').asarray(p) for p in loops])
                    except ValueError as exc:
                        native_data['sampled_outer_radius_unavailable']=str(exc)
            write(attempt/'native-observations.json',native_data)
            record['observations_within_provisional_tolerances']=all(v['within_tolerance'] for v in obs['expectations'].values())
            record['native_measurement_available']='volume_mm3' in native_data
            def url(p):return '/results/'+out.name+'/'+p.relative_to(out).as_posix()
            return {'ok':True,'backend':'usd-brep','stl':url(result.stl),'usd':url(result.exports['usd']),
                'source':url(result.source),'views':{},'diagnostics':result.backend_details,
                'build':result.metadata(),'params':recipe_params(doc)}
        except Exception as e:
            record.setdefault('build_ok',False)
            record.update(seconds=round(time.monotonic()-start,4),exception=f'{type(e).__name__}: {e}')
            raise
        finally:write(attempt/'attempt.json',record)
    summary={'case':name,'track':'manually_authored','user_review':'pending',
             'measurement_validation':'provisional; awaiting #81','attempts':records}
    try:
        built=adapter(session,case['recipe'])
        if not built['ok']:
            summary['outcome']='construction_failed';return summary
        original={'backend':'usd-brep','success':False,'files':{k:built[k] for k in ('source','stl','usd','views')},
            'diagnostics':built['diagnostics'],'evaluation':{'status':'unverified','accepted':False}}
        write(session/'result.json',original)
        (session/'model.recipe.json').write_text(local(built['source']).read_text())
        selected=revisions.selected_result(session)
        targets=built['diagnostics']['selection_catalog'].get('targets',[])
        target=next((t for t in targets if t['rule']==cases.POCKET_RULE),None) if name=='pocket' else next(
            (t for t in targets if t['rule'].get('kind')=='extreme_face' and t['rule'].get('axis')==2 and t['rule'].get('side')=='min'),None)
        if target:
            feature_selection.choose(session,{'revision_id':'original','target_id':target['id'],'target_version':0,'selection_version':0})
        summary['selection_rule']=target['rule'] if target else None
        summary['selection_limitation']='Geometric rule for pocket or bottom face; arbitrary face/edge targeting is not implemented.'
        def preview(value):
            state=revisions.selected_result(session)
            base={'parent_id':state['revision']['id'],'selection_version':state['revision']['selection_version']}
            if name=='pocket':
                return revisions.targeted_preview(session,{**base,'operation':'pocket_depth','value':value},adapter,targeted_edits.verify_edit)
            return revisions.preview(session,{**base,'updates':{case['edit']:value}},adapter)
        role='edited'
        candidate=preview(case['value'])
        summary['preview_keeps_original_selected']=revisions.selected_result(session)['revision']['id']=='original'
        summary['selection_after_edit']=candidate.get('target_selection',{})
        revisions.keep(session,{'revision_id':candidate['revision']['id'],'selection_version':candidate['revision']['selection_version']})
        before=revisions.selected_result(session)
        protected_hashes={k:sha(local(before['files'][k])) for k in ('source','stl','usd')}
        store_before=sha(session/'revisions.json')
        role='rejected'
        try:
            preview(case.get('rejection_value',-1))
            summary['rejection']={'rejected':False,'error':'Invalid negative edit unexpectedly published'}
        except Exception as e:
            summary['rejection']={'rejected':True,'error':str(e),'type':type(e).__name__}
            # Planning rejects pocket depth before builder invocation; preserve that attempt too.
            if name=='pocket':
                p=directory/f'{len(records)+1:02d}-rejected';p.mkdir()
                record={'role':role,'backend':'usd-brep','attempt':p.name,'build_ok':False,
                        'stage':'production_targeted_planner','requested_depth':-1,'exception':str(e)}
                records.append(record);write(p/'attempt.json',record)
        after=revisions.selected_result(session)
        summary['failure_recovery']={'selected_revision_unchanged':before['revision']['id']==after['revision']['id'],
            'store_unchanged':store_before==sha(session/'revisions.json'),
            'downloads_unchanged':all(sha(local(after['files'][k]))==v for k,v in protected_hashes.items()),
            'download_sha256':protected_hashes}
        role='continued'
        more=preview(case['continued'])
        revisions.keep(session,{'revision_id':more['revision']['id'],'selection_version':more['revision']['selection_version']})
        summary['continued_edit_recorded']=True
        summary['outcome']='constructed_and_edited'
    except Exception as e:
        summary.update(outcome='failed',error=f'{type(e).__name__}: {e}')
    finally:
        # Preservation compares observed geometry, never merely unchanged recipe fields.
        good={r['role']:r for r in records if r.get('build_ok')}
        if 'initial' in good and 'edited' in good:
            a=json.loads((directory/good['initial']['attempt']/'mesh-observations.json').read_text())['values']
            b=json.loads((directory/good['edited']['attempt']/'mesh-observations.json').read_text())['values']
            summary['preservation']={k:{'before':a.get(k),'after':b.get(k),'tolerance_mm':.05,
                'within_tolerance':k in a and k in b and abs(a[k]-b[k])<=.05} for k in case['protected']}
        write(directory/'case.json',summary)
    return summary


def compare_scad(name,case,directory):
    if case['scad'] is None:return {'status':'not_attempted','reason':case['note']}
    records=[]
    initial=3 if name=='pocket' else case['recipe']['parameters'][case['edit']]['value']
    for role,value in [('initial',initial),('edited',case['value'])]:
        out=directory/f'openscad-{role}';out.mkdir()
        source=f'$fn=96;\n{case["edit"]}={value};\n'+case['scad']+'\n'
        (out/'model.scad').write_text(source)
        start=time.monotonic()
        ok,log=openscad.run(['openscad','-o','model.stl','model.scad'],cwd=out,timeout=180)
        (out/'worker.log').write_text(log)
        record={'role':role,'build_ok':bool(ok and (out/'model.stl').exists()),'seconds':round(time.monotonic()-start,4),
                'construction':'manually_authored OpenSCAD, $fn=96','note':case['note']}
        if record['build_ok']:
            try:
                obs=measure.observe(name,out/'model.stl')
                doc=deepcopy(case['recipe'])
                if name=='pocket':doc,_=targeted_edits.plan(doc,cases.POCKET_RULE,value) if value!=3 else (doc,None)
                else:doc['parameters'][case['edit']]['value']=value
                obs['expectations']=measure.compare(obs,measure.expected(name,doc))
                write(out/'mesh-observations.json',obs)
            except Exception as e:record['measurement_error']=str(e)
        records.append(record);write(out/'attempt.json',record)
    return {'status':'attempted','attempts':records}


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--out',type=Path,required=True)
    ap.add_argument('--cases',nargs='*');args=ap.parse_args()
    out=args.out.resolve();out.mkdir(parents=True,exist_ok=False)
    registry=cases.cases()
    if args.cases:registry={k:registry[k] for k in args.cases}
    now=datetime.now(timezone.utc).isoformat()
    write(out/'plan.json',{'frozen_before_build_utc':now,'cases':registry,'model_calls':0,
        'scope':'Independent trusted construction track of #82; #80/#81 gates remain pending',
        'steps_measure':'Count explicit manual modeling actions below, not code lines or elapsed human time',
        'edit_effort':'One named numeric update; pocket uses one selected-target depth update. No source rewriting after an edit.',
        'tessellation':{'brep_chord_height_mm':.05,'brep_loft_max_edge_mm':2,'openscad_fn':96}})
    write(out/'environment.json',{'base_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        'python':sys.version,'platform':platform.platform(),'worker_python':worker_python(),
        'worker_version':'usd-brep==1.0.0','started_utc':now,'openscad_image':os.getenv('DOODLE_OPENSCAD_DOCKER')})
    summaries={}
    for name,case in registry.items():
        print(name,flush=True)
        summary=collect(name,case,out/name)
        summary['openscad']=compare_scad(name,case,out/name)
        write(out/name/'case.json',summary);summaries[name]=summary
        print(name,summary['outcome'],flush=True)
    write(out/'summary.json',summaries)
    # Every run has its own review record; never infer a user decision from observations.
    write(out/'review.json',{'status':'awaiting_user_review','decisions':{k:{'decision':None,'comment':None} for k in registry}})
    print(out)

if __name__=='__main__':main()
