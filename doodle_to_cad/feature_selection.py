"""Resolve saved geometric rules against the current native build catalog."""
from copy import deepcopy
from fastapi import HTTPException


def resolve(result, saved):
    if not saved:return {'status':'none'}
    catalog=result.get('diagnostics',{}).get('selection_catalog',{})
    if catalog.get('status')=='unavailable':
        return {**saved,'status':'unavailable','reason':'Geometry selection is unavailable for this build.'}
    rule=saved['rule']
    matches=[t for t in catalog.get('targets',[]) if t['rule']==rule]
    if len(matches)==1:return {**saved,'status':'matched','target':matches[0]}
    rejected=next((x for x in catalog.get('unresolved',[]) if x['rule']==rule),None)
    if rejected:return {**saved,**rejected}
    same_owner=[t for t in catalog.get('targets',[]) if t['rule'].get('kind')==rule.get('kind') and t['rule'].get('owner')==rule.get('owner')]
    return {**saved,'status':'ambiguous' if same_owner else 'lost',
            'reason':'The selected geometry changed or is no longer present. Select again.'}


def choose(out, payload):
    from . import revisions
    if set(payload)!={'revision_id','target_id','target_version','selection_version'}:
        raise HTTPException(422,'Selection requires the displayed revision and current selection versions.')
    with revisions.locked(out):
        store=revisions.read_store(out)
        revisions.selection_matches(store,payload['selection_version'])
        if type(payload['target_version']) is not int or payload['target_version']!=store.get('target_version',0):
            raise HTTPException(409,'The geometry selection changed. Reload before selecting again.')
        item=revisions.record(store,payload['revision_id'])
        if payload['target_id'] is None:store['target_selection']=None
        else:
            targets=item['result'].get('diagnostics',{}).get('selection_catalog',{}).get('targets',[])
            target=next((t for t in targets if t['id']==payload['target_id']),None)
            if target is None:raise HTTPException(422,'This target is not selectable in the displayed revision.')
            store['target_selection']={'rule':deepcopy(target['rule']),'label':target['label'],
                                       'selected_in_revision':item['id']}
        store['target_version']=store.get('target_version',0)+1
        revisions.write_store(out,store)
        return revisions.result_for(store,item['id'])
