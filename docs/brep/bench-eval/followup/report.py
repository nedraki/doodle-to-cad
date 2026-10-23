"""Build a review page from every frozen cell, including failed trials."""
import hashlib
import html
import json
import shutil
from pathlib import Path

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]


def digest(path): return hashlib.sha256(path.read_bytes()).hexdigest()


def retain_stage_evidence(rows, plan):
    """Append copies of original intermediates; never overwrite trial records."""
    results=ROOT/plan['infrastructure']['results_dir']
    for cell,row in rows:
        run_id=row.get('run_id')
        if not run_id: continue
        run=results/run_id
        if not run.exists(): continue  # fresh clones already have retained evidence
        dest=cell/'stages'
        candidates=list(run.glob('*.raw.*'))+list(run.glob('*.failure*.json'))
        candidates += [run/name for name in ('derived-sizes.json','interpretation.json','spec.json','construction-plan-request.json','generation.json','model.recipe.json','model.scad','stage.txt') if (run/name).exists()]
        for pattern in ('attempt-*/*','construction-attempts/*/*'):
            candidates += list(run.glob(pattern))
        for src in candidates:
            if not src.is_file(): continue
            target=dest/src.relative_to(run); target.parent.mkdir(parents=True,exist_ok=True)
            if target.exists():
                if digest(target)!=digest(src): raise ValueError(f'Retained evidence changed: {target}')
            else: shutil.copyfile(src,target)
        # The stock harness omits large STLs. Retain every selected mesh here.
        if row.get('build') and row['build'].get('sha256'):
            target=cell/'stl/model.stl'
            if not target.exists():
                matches=[p for p in run.rglob('*.stl') if digest(p)==row['build']['sha256']]
                if not matches: raise ValueError(f'Missing selected STL: {cell}')
                target.parent.mkdir(exist_ok=True); shutil.copyfile(matches[0],target)


def load_rows(plan):
    expected={(i['id'],b,t) for i in plan['corpus'] for b in ('openscad','usd-brep') for t in (1,2)}
    rows=[]
    for file in sorted((HERE/'runs').glob('*/*/trial-*/row.json')):
        row=json.loads(file.read_text()); rows.append((file.parent,row))
    actual={(r['drawing'],r['backend'],r['trial']) for _,r in rows}
    if actual!=expected or len(rows)!=len(expected):
        raise ValueError(f'Incomplete/duplicate matrix: {len(rows)}/{len(expected)}; missing {expected-actual}')
    return rows


def display(value):
    return 'not measured' if value is None else ('pass' if value is True else 'fail' if value is False else str(value))


def main():
    plan=json.loads((HERE/'TRIAL-PLAN.json').read_text()); rows=load_rows(plan)
    retain_stage_evidence(rows,plan)
    items={i['id']:i for i in plan['corpus']}
    summary={}
    for backend in ('openscad','usd-brep'):
        rs=[r for _,r in rows if r['backend']==backend]
        summary[backend]={'submitted':len(rs),'completed':sum(r.get('job_status')=='done' for r in rs),
                          'valid_solid':sum((r.get('checks') or {}).get('build_success') is True for r in rs),
                          'supplied_dimension_pass':sum((r.get('checks') or {}).get('supplied_dimension_pass') is True for r in rs),
                          'measured':sum(bool((r.get('build') or {}).get('extents_mm')) for r in rs)}
    interrupted=json.loads((HERE/'aborted-environment-run/OUTCOME.json').read_text())
    results={'summary':summary,'retained_interrupted_submissions':len(interrupted['submitted_run_ids']),
             'submitted_including_interrupted':len(rows)+len(interrupted['submitted_run_ids']),
             'user_acceptance':'pending','rows':[r for _,r in rows]}
    (HERE/'results.json').write_text(json.dumps(results,indent=2)+'\n')
    lines=['# Current-model baseline (#81 / #102)','',
           'All 24 cells from the revised plan are retained. Two earlier interrupted submissions are retained separately: 26 total submissions, 24 in the verified-environment matrix. The interruption is infrastructure evidence, not a model-quality verdict.','',
           'No model prompts or production geometry algorithms changed. Orientation scores are diagnostic only. These small repeated trials establish a descriptive baseline, not overall recognition improvement. User acceptance is pending.','',
           '| Backend | Submitted | Completed jobs | Valid solids | Supplied dimension passes | Measurable meshes |',
           '|---|---:|---:|---:|---:|---:|']
    for b,s in summary.items(): lines.append(f"| {b} | {s['submitted']} | {s['completed']} | {s['valid_solid']} | {s['supplied_dimension_pass']} | {s['measured']} |")
    lines += ['', 'Pass counts use all submitted cells as denominator. Failed builds are retained. See each row for measured-only comparisons; a valid solid is not drawing acceptance.', '',
              '| Case / backend / trial | Job | Solid | Supplied maximum | Measured extents | Genus (reference check) |',
              '|---|---|---|---:|---|---|']
    cards=[]
    for cell,row in rows:
        key=f"{row['drawing']} / {row['backend']} / {row['trial']}"; rel=cell.relative_to(HERE).as_posix()
        checks=row.get('checks') or {}; build=row.get('build') or {}; item=items[row['drawing']]
        lines.append(f"| [{key}]({rel}/row.json) | {row.get('job_status')} | {display(checks.get('build_success'))} | {item['dimension']} mm: {display(checks.get('supplied_dimension_pass'))} | {build.get('extents_mm','—')} | {build.get('genus','—')} ({display(checks.get('genus_pass'))}) |")
        imgs=[]
        for file,label in [('input.png','Submitted drawing'),('views/isometric.png','Generated CAD'),('views/front.png','Front view'),('views/top.png','Top view')]:
            if (cell/file).exists(): imgs.append(f'<figure><img loading="lazy" src="{rel}/{file}" alt="{label}"><figcaption>{label}</figcaption></figure>')
        evidence=[f'<a href="{rel}/row.json">Measurements</a>',f'<a href="{rel}/request.json">Exact request</a>',f'<a href="{rel}/environment.json">Environment</a>']
        for file,label in [('stl/model.stl','STL'),('model.scad','OpenSCAD'),('model.recipe.json','Recipe'),('construction-plan.json','Construction plan'),('sketch-spec.json','Interpretation'),('error.json','Failure'),('construction-plan.raw.txt','Raw plan')]:
            if (cell/file).exists(): evidence.append(f'<a href="{rel}/{file}">{label}</a>')
        error=row.get('error') or row.get('harness_error')
        cards.append(f'<article><h2>{html.escape(key)}</h2><p>Job: {html.escape(str(row.get("job_status")))} · Solid: {display(checks.get("build_success"))} · Supplied maximum {item["dimension"]} mm: {display(checks.get("supplied_dimension_pass"))}</p><p>Extents: {html.escape(str(build.get("extents_mm")))} · Genus: {build.get("genus", "not measured")} · User review: pending</p><div class="images">{"".join(imgs)}</div><p>{" · ".join(evidence)}</p><pre>{html.escape(json.dumps(error,indent=2)) if error else ""}</pre><details><summary>Registration diagnostic (not acceptance)</summary><pre>{html.escape(json.dumps(row.get("orientation_diagnostic"),indent=2))}</pre></details></article>')
    lines += ['', '## Reading the results', '',
              '- Reference-only thicknesses, depths and volumes are not model requirements. Historical `overall_pass` remains in raw rows but is not used as a reliability headline.',
              '- Wheel feature extraction and noisy view registration remain uncertain. A failed silhouette score does not by itself establish a model failure.',
              '- A passed genus check establishes tunnel count, not opening location or complete shape.',
              '- `ATTRIBUTION.md` records supported failure locations and unresolved causes. The interactive review page shows every cell, including errors.',
              '', '[Open the visual review](review.html) · [Before/after registration](before-after.png) · [All measurements](results.json)']
    (HERE/'RESULTS.md').write_text('\n'.join(lines)+'\n')
    page='''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>Drawing-to-CAD baseline: issues 81 and 102</title><style>body{font:16px system-ui;margin:30px auto;max-width:1500px;padding:0 20px;background:#eef2f5;color:#17212b}article{background:white;padding:24px;margin:24px 0;border-radius:12px}.images{display:flex;flex-wrap:wrap}figure{margin:8px;width:310px}img{width:100%;height:250px;object-fit:contain}pre{white-space:pre-wrap;overflow-wrap:anywhere}a{color:#075d9d}header img{height:auto;max-width:1480px}</style><header><h1>Current-model drawing-to-CAD baseline</h1><p>Every trial, including failures. Automatic checks are evidence; user acceptance remains pending. No claim of improved generated geometry. Two interrupted infrastructure submissions are retained separately.</p><p><a href="RESULTS.md">Summary and limits</a> · <a href="ATTRIBUTION.md">Failure attribution</a> · <a href="TRIAL-PLAN.json">Frozen plan</a> · <a href="aborted-environment-run/OUTCOME.json">Interrupted attempt</a></p><img src="before-after.png" alt="Same CAD before and after view registration"></header>'''
    (HERE/'review.html').write_text(page+'\n'.join(cards)+'</html>')
    print(json.dumps(summary,indent=2))
if __name__=='__main__': main()
