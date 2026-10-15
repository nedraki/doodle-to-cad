"""Bounded opening clarification. Waiting is cancellable; answers never execute code."""
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
    if not isinstance(payload,dict) or set(payload)-{'question_id','choice','depth_mm'}:
        raise HTTPException(422, 'Invalid answer fields.')
    if payload.get('question_id')!=question['id']:
        raise HTTPException(409, 'This answer belongs to a different question.')
    choice=payload.get('choice')
    if choice not in {'through','recess'}:raise HTTPException(422, 'Choose through-hole or recess.')
    answer={'question_id':question['id'],'feature_id':question['feature_id'],'choice':choice}
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


async def ask_opening(job, out, request, maximum, history):
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
        answer=await future
        record.update(status='answered',answer=answer);save()
        return answer
    except asyncio.CancelledError:
        record['status']='cancelled';save();raise
    finally:
        job.pop('_answer_future',None);job.pop('question',None)
        if timer and not timer.expired():timer.reschedule(asyncio.get_running_loop().time()+600)
