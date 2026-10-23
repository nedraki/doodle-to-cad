import asyncio
from dataclasses import replace
import json
from pathlib import Path
import time

from fastapi.testclient import TestClient
from doodle_to_cad.brep import worker_available
import pytest

from doodle_to_cad import app, direct_brep

IMAGE=Path('benchmarks/feature-evidence/ambiguous-outline.png').read_bytes()

PLAN={'view_frame':'Front XZ; depth along Y','features':[{'id':'body','shape':'box','section':'rectangular','axis_or_plane':'XYZ','dimensions':'test fixture','placement':'at origin','evidence':'controlled test fixture'}],'connections':[],'edit_rules':[],'unresolved':[]}



def test_default_generation_keeps_openscad(monkeypatch):
    seen=[]
    async def generate(*args,**kwargs):
        seen.append((args,kwargs))
        return {'backend':'openscad'}
    monkeypatch.setattr(app.pipeline,'generate',generate)
    with TestClient(app.app) as client:
        job=client.post('/api/generate',files={'image':('drawing.png',IMAGE,'image/png')}).json()['job_id']
        for _ in range(50):
            state=client.get('/api/generate/'+job).json()
            if state['status']=='done':break
            time.sleep(.01)
    assert state['result']['backend']=='openscad' and len(seen)==1


@pytest.mark.parametrize('data',[
    {'backend':'unknown'}, {'backend':'usd-brep','dimension':'nan'},
    {'backend':'usd-brep','dimension':'300'}, {'backend':'usd-brep','refine_mode':'as_drawn'},
])
def test_bad_options_do_not_start_jobs(data):
    before=set(app.JOBS)
    with TestClient(app.app) as client:
        response=client.post('/api/generate',files={'image':('drawing.png',IMAGE,'image/png')},data=data)
    assert response.status_code==422 and set(app.JOBS)==before


def test_direct_rejects_separate_views_and_missing_worker(monkeypatch):
    with TestClient(app.app) as client:
        files=[('image',('drawing.png',IMAGE,'image/png')),('additional_views',('other.png',IMAGE,'image/png'))]
        response=client.post('/api/generate',files=files,data={'backend':'usd-brep'})
        assert response.status_code==422 and response.json()['detail']['code']=='unsupported_input'
        monkeypatch.setenv('DOODLE_BREP_PYTHON','/missing/python')
        response=client.post('/api/generate',files=files[:1],data={'backend':'usd-brep'})
        assert response.status_code==422 and response.json()['detail']['code']=='backend_unavailable'


@pytest.mark.parametrize('mode',['unsupported','schema','cancel','plan'])
def test_failure_is_saved_without_result_or_fallback(tmp_path,monkeypatch,mode):
    monkeypatch.setattr(app,'settings',replace(app.settings,results_dir=tmp_path))
    async def worker():pass
    monkeypatch.setattr(direct_brep,'check_worker',worker)
    async def interpret(image,mime,controls,*,out):
        (out/'input.png').write_bytes(image)
        (out/'geometry.json').write_text('{}')
        if mode=='cancel':await asyncio.sleep(60)
        return {'interpretation':{'unresolved':['depth']}}
    async def model(*args,**kwargs):
        if args[2]=='construction-plan':return {'broken':True} if mode=='plan' else PLAN
        return {'unsupported':'Arbitrary loft is unsupported'} if mode=='unsupported' else {'version':1}
    async def discover():return type('Model',(),{'selected':'test-model'})()
    async def forbidden(*a,**kw):pytest.fail('Must not call OpenSCAD generation')
    monkeypatch.setattr(app.pipeline,'interpret_features',interpret)
    monkeypatch.setattr(app.pipeline,'_json_call',model)
    monkeypatch.setattr(app.pipeline.client,'discover',discover)
    monkeypatch.setattr(app.pipeline,'generate',forbidden)
    with TestClient(app.app) as client:
        job=client.post('/api/generate',files={'image':('drawing.png',IMAGE,'image/png')},data={'backend':'usd-brep'}).json()['job_id']
        for _ in range(200):
            state=client.get('/api/generate/'+job).json()
            if mode=='cancel' and state['stage']=='interpreting drawing':
                client.post('/api/generate/'+job+'/cancel')
            if state['status'] not in {'running','cancelling'}:break
            time.sleep(.01)
    assert state['status']==('cancelled' if mode=='cancel' else 'error')
    assert not (tmp_path/job/'result.json').exists()
    assert (tmp_path/job/'failure.json').exists()
    assert json.loads((tmp_path/job/'generation.json').read_text())['backend']=='usd-brep'
    assert not list((tmp_path/job).rglob('*.scad'))
    if mode=='unsupported':assert state['error']['code']=='unsupported_construction'
    if mode in {'schema','plan'}:assert state['error']['code']=='invalid_recipe'


def test_rotation_is_bounded_and_does_not_mutate_source():
    from doodle_to_cad.brep_recipe import validate_recipe
    recipe={'version':1,'units':'mm','parameters':{},'operations':[
        {'id':'seed','kind':'box','origin':[0,0,0],'size':[20,2,3]},
        {'id':'turned','kind':'rotate','body':'seed','origin':[0,0,0],'axis':'z','angle':45}],
        'output':'turned'}
    validate_recipe(recipe)
    recipe['operations'][1]['angle']=361
    with pytest.raises(ValueError,match='360'):validate_recipe(recipe)
    recipe['operations'][1]['angle']=45
    recipe['operations'][1]['axis']='arbitrary'
    with pytest.raises(ValueError,match='Axis'):validate_recipe(recipe)


@pytest.mark.skipif(not worker_available(),reason='Isolated worker not configured')
def test_real_rotated_wheel(tmp_path):
    from doodle_to_cad.brep import build_brep
    from doodle_to_cad.build_contract import BuildInput
    from doodle_to_cad.construction_recipe import migrate_v1
    recipe={'version':1,'units':'mm','parameters':{},'operations':[
        {'id':'outer','kind':'cylinder','origin':[0,0,0],'radius':30,'height':4,'axis':'z'},
        {'id':'inner','kind':'cylinder','origin':[0,0,-1],'radius':26,'height':6,'axis':'z'},
        {'id':'rim','kind':'difference','left':'outer','right':'inner'},
        {'id':'hub','kind':'cylinder','origin':[0,0,0],'radius':8,'height':4,'axis':'z'},
        {'id':'seed','kind':'box','origin':[6,-2,0],'size':[22,4,4]},
        {'id':'first','kind':'union','left':'seed','right':'hub'}], 'output':'first'}
    previous='first'
    for i in range(1,8):
        recipe['operations'] += [
            {'id':f'spoke{i}','kind':'rotate','body':'seed','origin':[0,0,0],'axis':'z','angle':i*45},
            {'id':f'join{i}','kind':'union','left':previous,'right':f'spoke{i}'}]
        previous=f'join{i}'
    recipe['operations'].append({'id':'wheel','kind':'union','left':previous,'right':'rim'})
    recipe['output']='wheel'
    recipe=migrate_v1(recipe)
    recipe['constraints']=[{'id':f'joint{i}','kind':'connected','left':spoke,'right':'rim','min_volume_mm3':.01}
                           for i,spoke in enumerate(['seed']+[f'spoke{i}' for i in range(1,8)])]
    source=tmp_path/'recipe.json';source.write_text(json.dumps(recipe))
    result=build_brep(BuildInput('usd-brep',source,tmp_path,render=False))
    assert result.ok,result.log
    assert result.measurements['components']==1
    assert len(result.backend_details['connections'])==8
    assert result.backend_details['usd_roundtrip']


@pytest.mark.skipif(not worker_available(),reason='Isolated worker not configured')
def test_direct_job_publishes_native_recipe_and_provenance(tmp_path,monkeypatch):
    monkeypatch.setattr(app,'settings',replace(app.settings,results_dir=tmp_path))
    recipe=json.loads(Path('benchmarks/brep-v2/bookend.json').read_text())
    async def interpret(image,mime,controls,*,out):
        evidence={'interpretation':{'object_hypothesis':'test bookend'}}
        (out/'feature-evidence.json').write_text(json.dumps(evidence))
        (out/'geometry.json').write_text(json.dumps({'view_geometry':[]}))
        return evidence
    async def model(messages,out,label,**kwargs):
        if label=='construction-plan':return PLAN
        assert 'scad' not in json.loads(messages[1]['content'][0]['text'])
        (out/(label+'.raw.txt')).write_text(json.dumps(recipe))
        return recipe
    async def discover():return type('Model',(),{'selected':'fixture-model'})()
    async def forbidden(*a,**kw):pytest.fail('Direct BRep must never generate SCAD')
    monkeypatch.setattr(app.pipeline,'interpret_features',interpret)
    monkeypatch.setattr(app.pipeline,'_json_call',model)
    monkeypatch.setattr(app.pipeline.client,'discover',discover)
    monkeypatch.setattr(app.pipeline,'generate',forbidden)
    with TestClient(app.app) as client:
        response=client.post('/api/generate',files={'image':('drawing.png',IMAGE,'image/png')},data={'backend':'usd-brep'})
        assert response.status_code==200,response.text
        job=response.json()['job_id']
        for _ in range(600):
            state=client.get('/api/generate/'+job).json()
            if state['status']!='running':break
            time.sleep(.1)
        assert state['status']=='done',state
        result=state['result']
        assert result['generation']['path']=='drawing-to-brep'
        assert result['model']=='fixture-model'
        assert not result['success'] and not result['generation']['generated_scad']
        assert result['build']['source_format']=='brep-recipe-v2'
        app.JOBS.pop(job)
        assert client.get('/api/generate/'+job).json()['result']==result
        for key in ('source','stl','usd','evidence','generation'):
            assert (tmp_path/result['files'][key].removeprefix('/results/')).is_file()
    for scad in (tmp_path/job).rglob('*.scad'):
        assert scad.name=='preview.scad'
        assert scad.read_text()=='import("model.stl");\n'


def test_correction_cannot_weaken_joints_or_drop_features():
    import copy
    recipe=json.loads(Path('benchmarks/brep-v2/wheel.json').read_text())
    weakened=copy.deepcopy(recipe)
    weakened['constraints'][0]['min_volume_mm3']=.001
    with pytest.raises(ValueError,match='weaken'):
        direct_brep.validate_correction(recipe,weakened)
    added=copy.deepcopy(recipe)
    added['operations'].insert(0,{'id':'extra','kind':'box','size':[1,1,1],'origin':[0,0,0],
                                  'frame':'world','depends_on':[],'evidence':[]})
    with pytest.raises(ValueError,match='feature IDs'):
        direct_brep.validate_correction(recipe,added)
    with pytest.raises(ValueError,match='no change'):
        direct_brep.validate_correction(recipe,recipe)


@pytest.mark.skipif(not worker_available(),reason='Isolated worker not configured')
@pytest.mark.parametrize('mode',['placement','size','exhausted','cancel'])
def test_bounded_construction_correction_with_real_worker(tmp_path,monkeypatch,mode):
    from doodle_to_cad.construction_recipe import migrate_v1
    monkeypatch.setattr(app,'settings',replace(app.settings,results_dir=tmp_path))
    def recipe(z,width=20):
        return migrate_v1({'version':1,'units':'mm','parameters':{},'operations':[
            {'id':'body','kind':'box','origin':[0,0,z],'size':[width,10,10]}],'output':'body'})
    calls=[]
    async def interpret(image,mime,controls,*,out):
        (out/'feature-evidence.json').write_text('{}')
        (out/'geometry.json').write_text('{}')
        return {}
    async def model(messages,out,label,**kwargs):
        if label=='construction-plan':return PLAN
        calls.append(label)
        if label.startswith('direct-recipe'):
            return recipe(0,200) if mode=='size' else recipe(-2)
        payload=json.loads(messages[1]['content'])
        assert payload['diagnostic']['code'] in {'placement_failed','dimension_exceeded'}
        if mode=='cancel':await asyncio.sleep(60)
        if mode=='exhausted':return recipe(-2/len(calls))
        return recipe(0)
    async def discover():return type('Model',(),{'selected':'fixture-model'})()
    monkeypatch.setattr(app.pipeline,'interpret_features',interpret)
    monkeypatch.setattr(app.pipeline,'_json_call',model)
    monkeypatch.setattr(app.pipeline.client,'discover',discover)
    with TestClient(app.app) as client:
        response=client.post('/api/generate',files={'image':('drawing.png',IMAGE,'image/png')},data={'backend':'usd-brep'})
        job=response.json()['job_id']
        for _ in range(900):
            state=client.get('/api/generate/'+job).json()
            if mode=='cancel' and len(calls)>1:
                client.post('/api/generate/'+job+'/cancel')
            if state['status'] not in {'running','cancelling'}:break
            time.sleep(.05)
        out=tmp_path/job
        history=json.loads((out/'build-history.json').read_text())
        assert history[0]['status']=='failed'
        assert (out/'construction-attempts/1/recipe.json').exists()
        if mode in {'placement','size'}:
            assert state['status']=='done',state
            assert len(calls)==2 and history[-1]['status']=='built'
            assert state['result']['generation']['construction_attempts']==history
            assert state['result']['success'] is False
        else:
            assert state['status']==('cancelled' if mode=='cancel' else 'error'),state
            assert not (out/'result.json').exists()
            assert len(calls)==(2 if mode=='cancel' else 3)
            assert len(history)==(1 if mode=='cancel' else 3)


@pytest.mark.skipif(not worker_available(),reason='Isolated worker not configured')
def test_usd_comparison_requests_sufficient_volume_accuracy(tmp_path):
    from doodle_to_cad.brep import build_brep
    from doodle_to_cad.build_contract import BuildInput
    # This unchanged live-generated recipe fails the 1e-5 export gate when
    # volume() uses its default 1e-3 integration accuracy.
    source=Path('benchmarks/brep-v2/volume-precision-wheel.json')
    result=build_brep(BuildInput('usd-brep',source,tmp_path,render=False))
    assert result.ok,result.log
    d=result.backend_details
    assert d['volume_relative_accuracy']==1e-8
    assert abs(d['solid_volume_mm3']-d['usd_volume_mm3'])/d['solid_volume_mm3']<1e-5


def test_numeric_correction_cannot_change_axes_or_parameter_ranges():
    import copy
    recipe=json.loads(Path('benchmarks/brep-v2/wheel.json').read_text())
    changed=copy.deepcopy(recipe)
    next(op for op in changed['operations'] if op['kind']=='cylinder')['axis']='y'
    with pytest.raises(ValueError,match='numeric geometry'):
        direct_brep.validate_correction(recipe,changed)
    changed=copy.deepcopy(recipe)
    next(iter(changed['parameters'].values()))['max']+=1
    with pytest.raises(ValueError,match='ranges'):
        direct_brep.validate_correction(recipe,changed)


@pytest.mark.parametrize('change',['evidence','body_identity','name'])
def test_numeric_correction_preserves_recipe_context(change):
    import copy
    recipe=json.loads(Path('benchmarks/brep-v2/wheel.json').read_text())
    changed=copy.deepcopy(recipe)
    # A real numeric correction does not authorize rewriting its supporting evidence.
    next(op for op in changed['operations'] if op['kind']=='cylinder')['height']=9
    if change=='evidence':
        changed['evidence']['assumptions'].append({'id':'new_claim','text':'New unsupported claim'})
    elif change=='body_identity':
        changed['bodies'][0]['id']='replacement_part'
    else:
        changed['name']='replacement name'
    with pytest.raises(ValueError,match='metadata, body identity and evidence'):
        direct_brep.validate_correction(recipe,changed)


def test_direct_payload_carries_placements_refinements_and_new_kinds(tmp_path,monkeypatch):
    monkeypatch.setattr(app,'settings',replace(app.settings,results_dir=tmp_path))
    recipe=json.loads(Path('benchmarks/brep-v2/bookend.json').read_text())
    async def interpret(image,mime,controls,*,out):
        evidence={'interpretation':{'object_hypothesis':'test bookend'},'view_geometry':[]}
        (out/'feature-evidence.json').write_text(json.dumps(evidence))
        (out/'geometry.json').write_text(json.dumps({'view_geometry':[]}))
        return evidence
    async def model(messages,out,label,**kwargs):
        if label=='construction-plan':return PLAN
        (out/(label+'.raw.txt')).write_text(json.dumps(recipe))
        return recipe
    async def discover():return type('Model',(),{'selected':'fixture-model'})()
    async def forbidden(*a,**kw):pytest.fail('Direct BRep must never generate SCAD')
    monkeypatch.setattr(app.pipeline,'interpret_features',interpret)
    monkeypatch.setattr(app.pipeline,'_json_call',model)
    monkeypatch.setattr(app.pipeline.client,'discover',discover)
    monkeypatch.setattr(app.pipeline,'generate',forbidden)
    with TestClient(app.app) as client:
        response=client.post('/api/generate',files={'image':('drawing.png',IMAGE,'image/png')},data={'backend':'usd-brep'})
        assert response.status_code==200,response.text
        job=response.json()['job_id']
        for _ in range(600):
            state=client.get('/api/generate/'+job).json()
            if state['status']!='running':break
            time.sleep(.1)
        assert state['status']=='done',state
        app.JOBS.pop(job)
    payload=json.loads((tmp_path/job/'recipe-request.json').read_text())
    assert 'feature_placements_mm' in payload and 'intent_refinements' in payload
    prompt=(tmp_path/job/'recipe-prompt.txt').read_text()
    for token in ('sphere:','cone:','torus:','wedge:','pyramid:','arc_block:','helix:','drafted_extrude:',
                  'OUTER SILHOUETTE IS A HARD CONSTRAINT','polygon_mm'):
        assert token in prompt, token


def test_brep_checker_records_silhouette_gate(monkeypatch):
    from doodle_to_cad import brep_checks
    state={'silhouette':0.99}
    def fake_scores(source,evidence,views,primary,standard):
        return {'front':.99},{'front':{'crop_internal_profiles':2,'rendered_internal_profiles':2,
                                        'feature_position_fidelity':1.0,
                                        'silhouette_fidelity':state['silhouette']}}
    monkeypatch.setattr(brep_checks,'projection_scores',fake_scores)
    monkeypatch.setattr(brep_checks,'SILHOUETTE_MIN_FIDELITY',0.93)
    health={'watertight':True,'components':1,'extents_mm':[60,40,10]}
    result=brep_checks.evaluate_drawing(b'',{},{},health,{'primary_view':'front'},120)
    record={c['name']:c for c in result['checks']}
    assert record['front outer silhouette']['status']=='passed'
    assert result['projection_status']=='passed'
    state['silhouette']=0.876  # the saved rounded-rectangle substitution score
    result=brep_checks.evaluate_drawing(b'',{},{},health,{'primary_view':'front'},120)
    assert 'front outer silhouette' in result['failures']
    assert result['projection_status']=='failed'
