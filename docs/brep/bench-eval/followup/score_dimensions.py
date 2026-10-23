"""Additional dimension track on historical rows; never alters those rows."""
import hashlib
import json
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[4]; sys.path.insert(0,str(ROOT))
from scripts.evaluate_brep import reference_checks
HERE=Path(__file__).resolve().parent
ARCHIVE=HERE.parents[1]/'bench-final'


def main():
    plan=json.loads((ARCHIVE/'TRIAL-PLAN.json').read_text())
    items={i['id']:i for i in plan['corpus']}
    rows=[]
    for path in sorted((ARCHIVE/'runs').glob('*/*/trial-*/row.json')):
        row=json.loads(path.read_text()); item=items[row['drawing']]
        checks, _=reference_checks(row.get('build'),{},item['dimension'],1.0)
        rows.append({'drawing':row['drawing'],'backend':row['backend'],'trial':row['trial'],
                     'source':str(path.relative_to(ROOT)),'row_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
                     'supplied_dimension_mm':float(item['dimension']),
                     'measured_max_mm':max(row['build']['extents_mm']) if (row.get('build') or {}).get('extents_mm') else None,
                     'supplied_dimension_pass':checks.get('supplied_dimension_pass'),
                     'historical_overall_pass':(row.get('checks') or {}).get('overall_pass')})
    summary={}
    for backend in ('openscad','usd-brep'):
        rs=[r for r in rows if r['backend']==backend]; measured=[r for r in rs if r['measured_max_mm'] is not None]
        summary[backend]={'all_submitted':len(rs),'measured':len(measured),'dimension_pass':sum(r['supplied_dimension_pass'] is True for r in rs),
                          'dimension_fail_with_measurement':sum(r['supplied_dimension_pass'] is False for r in measured),
                          'no_measurement':len(rs)-len(measured)}
    report={'method':'shared reference_checks; archived measurements; no re-generation or historical row edits',
            'tolerance_mm':1.0,'summary':summary,'rows':rows}
    (HERE/'supplied-dimensions.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(summary,indent=2))
if __name__=='__main__': main()
