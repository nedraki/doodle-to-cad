"""Bounded opening and thickness clarification. Waiting is cancellable; answers never execute code."""
import asyncio
import json
import math
import uuid
from fastapi import HTTPException


def accept_answer(job, payload):
    future=job.get('_answer_future')
    question=job.get('question')
    if job['status']!='waiting_for_answer' or not question or not future or future.done():
        raise HTTPException(409, 'This question is no longer waiting for an answer.')
    kind=question.get('kind','opening_extent')
    if kind=='body_dimension':
        value=payload.get('value_mm') if isinstance(payload,dict) else None
        if isinstance(payload,dict) and set(payload)-{'question_id','value_mm'}:
            raise HTTPException(422,'Invalid answer fields.')
        if not isinstance(payload,dict) or payload.get('question_id')!=question['id']:
            raise HTTPException(409,'This answer belongs to a different question.')
        if isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value) or not 0<value<=question['maximum_mm']:
            raise HTTPException(422,'Enter a positive size in millimetres within the allowed range. Geometry checks still apply.')
        answer={'question_id':question['id'],'feature_id':question.get('feature_id','size'),'kind':kind,'value_mm':value}
        future.set_result(answer)
        job.update(status='running',stage='generating CAD geometry',question=None)
        return {'job_id':job['job_id'],'status':'running'}
    thickness_question=kind in {'wall_thickness','floor_thickness','uniform_thickness'}
    allowed={'question_id','thickness_mm'} if thickness_question else {'question_id','choice','depth_mm'}
    if not isinstance(payload,dict) or set(payload)-allowed:
        raise HTTPException(422, 'Invalid answer fields.')
    if payload.get('question_id')!=question['id']:
        raise HTTPException(409, 'This answer belongs to a different question.')
    answer={'question_id':question['id'],'feature_id':question['feature_id'],'kind':kind}
    if thickness_question:
        thickness=payload.get('thickness_mm')
        if isinstance(thickness,bool) or not isinstance(thickness,(int,float)) or not math.isfinite(thickness) or not 0<thickness<=question['maximum_thickness_mm']:
            raise HTTPException(422, 'Enter a positive thickness within the part size. Geometry checks still apply.')
        answer['thickness_mm']=thickness
    else:
        choice=payload.get('choice')
        if not isinstance(choice,str) or choice not in {'through','recess'}:raise HTTPException(422, 'Choose through-hole or recess.')
        answer['choice']=choice
        if choice=='recess':
            depth=payload.get('depth_mm')
            if isinstance(depth,bool) or not isinstance(depth,(int,float)) or not math.isfinite(depth) or not 0<depth<=question['maximum_depth_mm']:
                raise HTTPException(422, 'Enter a positive recess depth within the part size. Geometry checks still apply.')
            answer['depth_mm']=depth
        elif payload.get('depth_mm') is not None:
            raise HTTPException(422, 'A through-hole does not use a recess depth.')
    future.set_result(answer)
    job.update(status='running',stage='planning BRep geometry',question=None)
    return {'job_id':job['job_id'],'status':'running'}


async def ask_clarification(job, out, request, maximum, history, timeout_s=None):
    thickness_labels={'wall_thickness':'Wall thickness','floor_thickness':'Floor thickness','uniform_thickness':'Wall and floor thickness'}
    if request['kind']=='body_dimension':
        question={**request,'id':uuid.uuid4().hex,'text':request.get('text') or 'Size (mm)?','maximum_mm':maximum}
    elif request['kind'] in thickness_labels:
        question={**request,'id':uuid.uuid4().hex,'text':thickness_labels[request['kind']]+' (mm)?','maximum_thickness_mm':maximum}
    else:
        question={**request,'id':uuid.uuid4().hex,'text':'Should this hole go all the way through the part?',
                  'maximum_depth_mm':maximum,'choices':[{'id':'through','label':'Yes — make a through-hole'},
                  {'id':'recess','label':'No — leave a bottom'}]}
    record={'question':question,'status':'waiting'};history.append(record)
    def save(): (out/'clarifications.json').write_text(json.dumps(history,indent=2))
    save()
    future=asyncio.get_running_loop().create_future()
    job.update(status='waiting_for_answer',stage='waiting for your answer',question=question,_answer_future=future)
    timer=job.get('_prepare_timeout')
    if timer:timer.reschedule(None)
    try:
        if timeout_s:
            answer=await asyncio.wait_for(future, timeout_s)
        else:
            answer=await future
        record.update(status='answered',answer=answer);save()
        return answer
    except asyncio.TimeoutError:
        record.update(status='timeout');save()
        job.update(status='queued',stage='',question=None)
        job.pop('_answer_future',None)
        return None
    except asyncio.CancelledError:
        record['status']='cancelled';save();raise
    finally:
        job.pop('_answer_future',None);job.pop('question',None)
        if timer and not timer.expired():timer.reschedule(asyncio.get_running_loop().time()+600)
