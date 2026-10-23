"""Saved design versions. Builds create candidates; only explicit keep changes selection.

The record is backend-neutral so targeted repairs can use the same history.
Immutable records and a compare-and-swap selection prevent delayed work from
silently replacing the version chosen by another request or browser.
"""
from contextlib import contextmanager
from copy import deepcopy
import fcntl
import json
from pathlib import Path
import uuid

from fastapi import HTTPException


@contextmanager
def locked(out):
    with (out / '.revisions.lock').open('a') as handle:
        fcntl.flock(handle, fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(handle, fcntl.LOCK_UN)


def read_store(out):
    path = out / 'revisions.json'
    if path.exists():
        return json.loads(path.read_text())
    if not (out / 'result.json').exists():
        raise HTTPException(404, 'Run has no completed result')
    result = json.loads((out / 'result.json').read_text())
    source = out / ('model.recipe.json' if result.get('backend') == 'usd-brep' else 'model.scad')
    source_text = source.read_text() if source.exists() else None
    if source_text and result.get('backend') == 'usd-brep':
        from .brep_recipe import recipe_params
        parameters = recipe_params(json.loads(source_text))
    elif source_text:
        from .params import extract_params
        parameters = [p.to_dict() for p in extract_params(source_text)]
    else:
        parameters = []
    return {'version': 1, 'selected': 'original', 'selection_version': 0,
            'revisions': {'original': {'id': 'original', 'parent_id': None,
                'result': result, 'source_text': source_text, 'parameters': parameters, 'kind': 'generation'}}}


def write_store(out, store):
    pending = out / ('revisions-' + uuid.uuid4().hex + '.pending')
    try:
        pending.write_text(json.dumps(store, indent=2))
        pending.replace(out / 'revisions.json')
    finally:
        pending.unlink(missing_ok=True)


def record(store, revision_id):
    if not isinstance(revision_id, str) or revision_id not in store['revisions']:
        raise HTTPException(404, 'Unknown design revision')
    return store['revisions'][revision_id]


def result_for(store, revision_id):
    item = record(store, revision_id)
    result = deepcopy(item['result'])
    result['revision'] = {'id': item['id'], 'parent_id': item['parent_id'],
                          'selected_id': store['selected'],
                          'selection_version': store['selection_version'],
                          'candidate': revision_id != store['selected'],
                          'kind': item.get('kind', 'generation')}
    if 'parameters' in item:
        result['params'] = deepcopy(item['parameters'])
    from .feature_selection import resolve
    result['target_selection'] = resolve(result, store.get('target_selection'))
    result['target_version'] = store.get('target_version',0)
    result['original_files'] = deepcopy(store['revisions']['original']['result']['files'])
    return result


def selected_result(out):
    with locked(out):
        store = read_store(out)
        return result_for(store, store['selected'])


def selection_matches(store, expected):
    if type(expected) is not int or expected != store['selection_version']:
        raise HTTPException(409, 'The saved version changed. Reload it before keeping another edit.')


def preview(out, payload, builder):
    if set(payload) != {'parent_id', 'selection_version', 'updates'} or not isinstance(payload['updates'], dict):
        raise HTTPException(422, 'Preview requires parent_id, selection_version and parameter updates.')
    with locked(out):
        store = read_store(out)
        selection_matches(store, payload['selection_version'])
        parent = deepcopy(record(store, payload['parent_id']))
    if parent['result'].get('backend') != 'usd-brep':
        raise HTTPException(422, 'Saved parameter previews currently require a BRep result.')
    # Native builds can be slow. Never hold the selection lock during a build.
    built = builder(out, json.loads(parent['source_text']), payload['updates'])
    if not built.get('ok'):
        raise HTTPException(422, 'The edit failed. The saved version is unchanged.')
    source_path = out / Path(built['source']).relative_to('/results/' + out.name)
    result = deepcopy(parent['result'])
    result.update(success=False, files={key: built[key] for key in ('source', 'stl', 'usd', 'views')},
                  diagnostics=built['diagnostics'], build=built['build'],
                  evaluation={'status': 'unverified', 'accepted': False,
                              'failures': ['Drawing checks have not been rerun for this edit.']})
    revision_id = uuid.uuid4().hex
    item = {'id': revision_id, 'parent_id': parent['id'], 'kind': 'parameter_edit',
            'result': result, 'source_text': source_path.read_text(), 'parameters': built['params']}
    with locked(out):
        store = read_store(out)
        selection_matches(store, payload['selection_version'])
        store['revisions'][revision_id] = item
        write_store(out, store)
        return result_for(store, revision_id)


def targeted_preview(out, payload, builder, verify):
    """Preview one supported targeted change on the selected target.

    Selection must be matched; the recipe is planned from the parent's saved
    source, built through the same isolated worker, then measured on the
    exported meshes. Only a candidate whose checks all pass is recorded.
    """
    if set(payload) != {'parent_id', 'selection_version', 'operation', 'value'} \
            or isinstance(payload['value'], bool) or not isinstance(payload['value'], (int, float)) \
            or not isinstance(payload['operation'], str):
        raise HTTPException(422, 'Targeted edit requires parent_id, selection_version, operation and a numeric value.')
    with locked(out):
        store = read_store(out)
        selection_matches(store, payload['selection_version'])
        parent = deepcopy(record(store, payload['parent_id']))
        saved = deepcopy(store.get('target_selection'))
    if parent['result'].get('backend') != 'usd-brep':
        raise HTTPException(422, 'Targeted edits currently require a BRep result.')
    from .feature_selection import resolve
    resolved = resolve(parent['result'], saved)
    if not saved or resolved.get('status') != 'matched':
        raise HTTPException(422, 'Select a supported target first. The saved selection is no longer matched to this version.')
    from . import targeted_edits
    rule = resolved['target']['rule']
    extents = parent['result'].get('diagnostics', {}).get('extents_mm')
    try:
        recipe = json.loads(parent['source_text'])
        edited, edit = targeted_edits.plan(recipe, rule, payload['value'], bounds=extents)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    if payload['operation'] != edit['operation']:
        raise HTTPException(422, f'The selected target does not support the requested change. Requested '
                                 f'"{payload["operation"]}"; this target supports "{edit["operation"]}".')
    # Native builds can be slow. Never hold the selection lock during a build.
    built = builder(out, edited)
    if not built.get('ok'):
        raise HTTPException(422, 'The edit failed to build. The saved version is unchanged.')
    def local(url):
        return out / Path(url).relative_to('/results/' + out.name)
    edges = next((t['geometry'].get('lines') for t in parent['result'].get('diagnostics', {})
                  .get('selection_catalog', {}).get('targets', []) if t['rule'] == rule), None)
    try:
        report = verify(local(parent['result']['files']['stl']), local(built['stl']), edit, edges=edges)
    except Exception as exc:  # measurement failures must never publish a candidate
        raise HTTPException(422, f'The change could not be verified: {exc}. The saved version is unchanged.') from exc
    if not report['ok']:
        raise HTTPException(422, {'message': 'The change did not meet its checks. Nothing was published.',
                                  'checks': report['checks']})
    source_path = local(built['source'])
    result = deepcopy(parent['result'])
    result.update(success=False, files={key: built[key] for key in ('source', 'stl', 'usd', 'views')},
                  diagnostics=built['diagnostics'], build=built['build'],
                  evaluation={'status': 'unverified', 'accepted': False,
                              'failures': ['Drawing checks have not been rerun for this edit.']})
    revision_id = uuid.uuid4().hex
    item = {'id': revision_id, 'parent_id': parent['id'], 'kind': 'targeted_edit',
            'result': result, 'source_text': source_path.read_text(), 'parameters': built['params'],
            'targeted': {'operation': edit['operation'], 'value': payload['value'],
                         'ok': report['ok'], 'rule': rule, 'checks': report['checks']}}
    with locked(out):
        store = read_store(out)
        selection_matches(store, payload['selection_version'])
        store['revisions'][revision_id] = item
        write_store(out, store)
        result = result_for(store, revision_id)
    result['targeted'] = item['targeted']
    return result


def keep(out, payload):
    if set(payload) != {'revision_id', 'selection_version'}:
        raise HTTPException(422, 'Keep requires revision_id and selection_version.')
    with locked(out):
        store = read_store(out)
        selection_matches(store, payload['selection_version'])
        record(store, payload['revision_id'])
        store['selected'] = payload['revision_id']
        store['selection_version'] += 1
        write_store(out, store)
        return result_for(store, store['selected'])
