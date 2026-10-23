import asyncio
import copy
import json
import time
from dataclasses import replace
from pathlib import Path

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from doodle_to_cad import app, direct_brep
from doodle_to_cad.clarification import accept_answer, ask_clarification
from doodle_to_cad.construction_intent import validate_plan

PLAN={'view_frame':'Top XY','features':[{'id':'hole','shape':'opening','section':'circle','axis_or_plane':'Z','dimensions':['diameter 8'],'placement':'centre','evidence':'circle in top view'}], 'connections':[], 'edit_rules':[], 'unresolved':['opening depth unknown'], 'clarification':{'feature_id':'hole','feature_label':'Circle at the centre of the top face','reason':'No bottom or through label is shown','kind':'opening_extent'}}


def test_wait_answer_bounds_stale_and_saved_evidence(tmp_path):
    async def scenario():
        job={'job_id':'abc','status':'running'};history=[]
        async with asyncio.timeout(.05) as timer:
            job['_prepare_timeout']=timer
            waiting=asyncio.create_task(ask_clarification(job,tmp_path,PLAN['clarification'],40,history))
            await asyncio.sleep(.1) # Human thinking does not consume preparation timeout.
            q=job['question'];assert not timer.expired()
            for payload,status in [({'question_id':q['id'],'choice':[]},422),({'question_id':'stale','choice':'through'},409),({'question_id':q['id'],'choice':'recess','depth_mm':0},422),({'question_id':q['id'],'choice':'recess','depth_mm':float('nan')},422),({'question_id':q['id'],'choice':'recess','depth_mm':True},422),({'question_id':q['id'],'choice':'recess'},422)]:
                with pytest.raises(HTTPException) as error:accept_answer(job,payload)
                assert error.value.status_code==status and not waiting.done()
            payload={'question_id':q['id'],'choice':'recess','depth_mm':5}
            accept_answer(job,payload)
            with pytest.raises(HTTPException):accept_answer(job,payload)
            answer=await waiting
            assert answer['feature_id']=='hole' and answer['depth_mm']==5
            assert history[0]['status']=='answered'
            assert json.loads((tmp_path/'clarifications.json').read_text())[0]['answer']==answer
    asyncio.run(scenario())


def test_clarification_must_reference_existing_feature():
    plan=copy.deepcopy(PLAN);plan['clarification']['feature_id']='missing'
    with pytest.raises(ValueError):validate_plan(plan)


@pytest.mark.parametrize('choice',['through','recess','cancel','clear','unresolved'])
def test_job_question_resumes_same_measurements_or_cancels(tmp_path,monkeypatch,choice):
    monkeypatch.setattr(app,'settings',replace(app.settings,results_dir=tmp_path))
    calls=[]
    async def worker():pass
    async def discover():return type('Model',(),{'selected':'fixture-model'})()
    async def interpret(image,mime,controls,*,out):
        calls.append('measure');(out/'geometry.json').write_text('{"saved":true}')
        return {}
    async def model(messages,out,label,**kw):
        calls.append(label)
        if label=='construction-plan':
            p=copy.deepcopy(PLAN)
            if choice in {'clear','unresolved'}:p.pop('clarification')
            if choice=='clear':p['unresolved']=[]
            return p
        if label.startswith('construction-plan-answer'):
            payload=json.loads(messages[1]['content'][0]['text']);a=payload['clarification_answers'][0]
            assert a['choice']==choice and a['feature_id']=='hole'
            if choice=='recess':assert a['depth_mm']==5
            p=copy.deepcopy(PLAN);p.pop('clarification');p['unresolved']=[];return p
        if choice=='unresolved':
            assert json.loads(messages[1]['content'][0]['text'])['construction_plan']['unresolved']==PLAN['unresolved']
        # Stop before kernel execution: this test proves state and provenance, not geometry.
        assert json.loads((out/'geometry.json').read_text())=={'saved':True}
        return {'unsupported':'controlled test stop before build'}
    monkeypatch.setattr(direct_brep,'check_worker',worker)
    monkeypatch.setattr(app.pipeline,'interpret_features',interpret)
    monkeypatch.setattr(app.pipeline,'_json_call',model)
    monkeypatch.setattr(app.pipeline.client,'discover',discover)
    image=Path('benchmarks/feature-evidence/ambiguous-outline.png').read_bytes()
    with TestClient(app.app) as client:
        job=client.post('/api/generate',files={'image':('drawing.png',image,'image/png')},data={'backend':'usd-brep'}).json()['job_id']
        def wait():
            for _ in range(200):
                s=client.get('/api/generate/'+job).json()
                if s['status']!='running':return s
                time.sleep(.01)
            pytest.fail('job did not settle')
        state=wait()
        if choice in {'through','recess','cancel'}:
            assert state['status']=='waiting_for_answer'
            assert not (tmp_path/job/'result.json').exists()
            if choice=='cancel':
                assert client.post('/api/generate/'+job+'/cancel').json()['status']=='cancelled'
                assert client.post('/api/generate/'+job+'/answer',json={'question_id':state['question']['id'],'choice':'through'}).status_code==409
            else:
                answer={'question_id':state['question']['id'],'choice':choice}
                if choice=='recess':answer['depth_mm']=5
                assert client.post('/api/generate/'+job+'/answer',json=answer).status_code==200
                assert wait()['error']['code']=='unsupported_construction'
            saved=json.loads((tmp_path/job/'clarifications.json').read_text())
            assert saved[0]['status']==('cancelled' if choice=='cancel' else 'answered')
        else:
            assert state['status']=='error'
            assert state['error']['code']=='unsupported_construction'
            assert not (tmp_path/job/'clarifications.json').exists()
        assert calls.count('measure')==1
        assert not (tmp_path/job/'result.json').exists()
        if choice=='cancel':assert not any(c.startswith('direct-recipe') for c in calls)


def test_waiting_job_is_not_pruned(monkeypatch):
    monkeypatch.setattr(app,'MAX_TRACKED_JOBS',1)
    jobs={'waiting':{'created':1,'status':'waiting_for_answer'},'finished':{'created':2,'status':'done'},'new':{'created':3,'status':'running'}}
    monkeypatch.setattr(app,'JOBS',jobs)
    app._prune_jobs()
    assert set(jobs)=={'waiting','new'}

@pytest.mark.parametrize('kind',['wall_thickness','floor_thickness','uniform_thickness'])
def test_thickness_answer_is_bounded_saved_and_not_an_opening_choice(tmp_path,kind):
    async def scenario():
        job={'job_id':'abc','status':'running'};history=[]
        request={**PLAN['clarification'],'kind':kind}
        waiting=asyncio.create_task(ask_clarification(job,tmp_path,request,60,history));await asyncio.sleep(0)
        q=job['question'];assert 'maximum_thickness_mm' in q and 'choices' not in q
        for value in [None,0,-1,True,float('nan'),float('inf'),61,[], '2']:
            with pytest.raises(HTTPException):accept_answer(job,{'question_id':q['id'],'thickness_mm':value})
            assert not waiting.done()
        with pytest.raises(HTTPException):accept_answer(job,{'question_id':q['id'],'choice':'through'})
        accept_answer(job,{'question_id':q['id'],'thickness_mm':2})
        answer=await waiting
        assert answer['thickness_mm']==2 and answer['kind']==kind and 'choice' not in answer
        assert history[0]['answer']==answer
    asyncio.run(scenario())


def test_same_feature_can_answer_wall_and_floor_separately(tmp_path,monkeypatch):
    monkeypatch.setattr(app,'settings',replace(app.settings,results_dir=tmp_path))
    async def worker():pass
    async def discover():return type('Model',(),{'selected':'fixture-model'})()
    async def interpret(image,mime,controls,*,out):
        (out/'input.png').write_bytes(image)
        (out/'feature-evidence.json').write_text('{}')
        (out/'geometry.json').write_text('{"view_geometry":[]}')
        return {}
    async def model(messages,out,label,**kw):
        if label.startswith('construction-plan'):
            payload=json.loads(messages[1]['content'][0]['text']);answers=payload.get('clarification_answers',[])
            p=copy.deepcopy(PLAN)
            if len(answers)<2:p['clarification']['kind']=['wall_thickness','floor_thickness'][len(answers)]
            else:
                assert [(a['kind'],a['thickness_mm']) for a in answers]==[('wall_thickness',2),('floor_thickness',3)]
                p.pop('clarification');p['unresolved']=[]
            return p
        return {'unsupported':'controlled stop after both answers'}
    monkeypatch.setattr(direct_brep,'check_worker',worker);monkeypatch.setattr(app.pipeline,'interpret_features',interpret);monkeypatch.setattr(app.pipeline,'_json_call',model);monkeypatch.setattr(app.pipeline.client,'discover',discover)
    image=Path('benchmarks/feature-evidence/ambiguous-outline.png').read_bytes()
    with TestClient(app.app) as client:
        job=client.post('/api/generate',files={'image':('drawing.png',image,'image/png')},data={'backend':'usd-brep'}).json()['job_id']
        for kind,value in [('wall_thickness',2),('floor_thickness',3)]:
            for _ in range(200):
                state=client.get('/api/generate/'+job).json()
                if state['status']!='running':break
                time.sleep(.01)
            assert state['status']=='waiting_for_answer' and state['question']['kind']==kind
            assert client.post('/api/generate/'+job+'/answer',json={'question_id':state['question']['id'],'thickness_mm':value}).status_code==200
        for _ in range(200):
            state=client.get('/api/generate/'+job).json()
            if state['status']!='running':break
            time.sleep(.01)
        assert state['status']=='error' and state['error']['code']=='unsupported_construction'
        assert [x['answer']['thickness_mm'] for x in json.loads((tmp_path/job/'clarifications.json').read_text())]==[2,3]
