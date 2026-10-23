"""Audit the issue 42 input contract. Does not call a model or build geometry."""
import hashlib
import json
from pathlib import Path
from PIL import Image, __version__ as pillow_version
ROOT=Path(__file__).resolve().parents[1]
def main():
    source=ROOT/'benchmarks/brep-features/selection.json'
    data=json.loads(source.read_text())
    assert len({c['id'] for c in data['cases']})==len(data['cases'])
    checked=[]
    for c in data['cases']+data['regressions']:
        path=ROOT/c['drawing']
        assert hashlib.sha256(path.read_bytes()).hexdigest()==c['sha256'],c['id']
        with Image.open(path) as im:w,h=im.size
        for r in c.get('evidence_regions',[]):
            x0,y0,x1,y1=r['box_px'];assert 0<=x0<x1<=w and 0<=y0<y1<=h,(c['id'],r)
        if 'controls' in c:
            assert c['controls']['notes']==c['controls']['object_type_hint']==''
            assert c['checks'] and c['capability']['status']
            for key in ('source','report'):
                if key in c['openscad_evidence']:assert (ROOT/c['openscad_evidence'][key]).is_file()
        checked.append({'id':c['id'],'image_size':[w,h],'sha256':c['sha256'],'input_check':'pass'})
    random=data['random_selection']
    assert random['selected'] in random['eligible']
    assert random['selected'] in [c['id'] for c in data['regressions']]
    report=dict(contract_revision=data['contract_revision'],contract_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),pillow_version=pillow_version,checks=checked,model_calls=0,geometry_builds=0,user_review='pending',scope='Input integrity only; no drawing-generation or geometry acceptance claim')
    dest=ROOT/'docs/brep/task-42/input-audit.json';dest.parent.mkdir(parents=True,exist_ok=True)
    dest.write_text(json.dumps(report,indent=2)+'\n');print(f'{len(checked)} input records pass. No model calls or geometry builds.')
if __name__=='__main__':main()
