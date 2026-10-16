"""Render saved, real app results and index all clarification trials."""
import json,html,os
from pathlib import Path
import httpx
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'docs/brep/task-08';TRIAL=OUT/os.getenv('BREP_TRIAL','trial-01');BASE=os.getenv('DOODLE_TEST_URL','http://127.0.0.1:8095')
summary=json.loads((TRIAL/'summary.json').read_text())
with sync_playwright() as p:
 browser=p.chromium.launch(headless=True,executable_path='/home/sparkie/.cache/ms-playwright/chromium-1243/chrome-linux-arm64/chrome',args=['--no-sandbox','--allow-file-access-from-files','--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader'])
 for name,c in summary.items():
  c['flow_passed']=(c['status']=='cancelled' and c['questions']==1 and c.get('no_completed_result',False)) if name=='cancel' else (c['status']=='done' and c.get('feature_passed',False) and c['questions']==(0 if name=='clear' else 1))
  if c['status']!='done':continue
  page=browser.new_page(viewport={'width':1600,'height':1200});page.goto(BASE)
  result=httpx.get(BASE+'/api/results/'+c['job']).json();page.evaluate('(r)=>render(r,null)',result)
  page.wait_for_function('viewer?.mesh',timeout=30000);page.wait_for_timeout(1000)
  for view in ['top','isometric']:
   page.evaluate('(v)=>viewer.setView(v)',view);page.wait_for_timeout(500)
   page.locator('#viewerWrap').screenshot(path=str(TRIAL/name/(view+'.png')))
  page.close()
 (TRIAL/'summary.json').write_text(json.dumps(summary,indent=2))
 cards=[('trial-01/through/input.png','Same drawing, empty notes'),('trial-01/through/top.png','Through-hole: open through the block'),('trial-01/recess/top.png','Recess: bottom remains, depth 5 mm')]
 document='''<!doctype html><meta charset="utf-8"><style>body{background:#f8f4e9;color:#182d36;font:20px Arial;margin:30px}h1{font-size:30px}.cards{display:flex;gap:16px}figure{margin:0;flex:1;min-width:0;background:white;border:1px solid #bbb;border-radius:12px;overflow:hidden}img{width:100%;height:440px;object-fit:contain}figcaption{padding:18px;font-weight:bold}footer{margin-top:24px}</style><h1>One drawing → one question → two different parts</h1><p>Real model generation and app screenshots. Both outputs pass independent section and dimension checks.</p><div class="cards">'''
 document+=''.join(f'<figure><img src="{src}"><figcaption>{html.escape(label)}</figcaption></figure>' for src,label in cards)
 document=document.replace('trial-01/',TRIAL.name+'/')
 document+='</div><footer>Both bodies: 40 × 30 × 12 mm. Opening: Ø8 mm. Recess leaves a 7 mm floor. No reference recipe was supplied to the model.</footer>'
 (OUT/'comparison.html').write_text(document)
 page=browser.new_page(viewport={'width':1800,'height':720});page.goto((OUT/'comparison.html').as_uri());page.screenshot(path=str(OUT/'comparison.png'),full_page=True);browser.close()
lines=['# Task 08 — ask before guessing an opening','',
'Issue #25. Base branch: `brep-integration` at `da94850`. Task branch: `codex/brep-08-clarification`. `main` is unchanged.','',
'Implementation commit: `cd1f0ca`. PR [47](https://github.com/nedraki/doodle-to-cad/pull/47), targeting `brep-integration`. User review and merge remain pending.','','## What changed','',
'A top-view circle can mean a through-hole or a recess. The experimental BRep path now pauses before building when the construction plan identifies that missing choice. It names the opening and asks whether it goes through. A recess requires a depth in millimetres. The original image and measured evidence stay in the same job. The answer is saved and the construction plan is updated before recipe generation.','',
'The first version supports opening extent questions. It can ask about at most three different openings, one at a time. It does not provide arbitrary questions or upload of an extra view during a paused job. Other plan uncertainties continue through the existing recipe planner. That planner must disclose permitted assumptions or retain unresolved recipe evidence, which the existing validator rejects. No recipe or geometry validation is bypassed.','',
'## Visible evidence','',
'![Same drawing, two answered constructions](comparison.png)','',
'![Real question with a recess answer](trial-01/recess/answer.png)','',
'## Live acceptance trials','',
'All four use the real model through the browser. Notes are empty. The synthetic drawings are saved in `benchmarks/brep-clarification`; expected geometry enters only the later measurement code, never the model request.','',
'| Case | Job | Questions | Result | Expected flow and geometry |','|---|---|---|---|---|']
for name,c in summary.items():lines.append(f"| {name} | `{c['job']}` | {c['questions']} | {c['status']} | {'passed' if c['flow_passed'] else 'failed'} |")
lines+=['','The ambiguous drawing produced one question in each answered run. Selecting through-hole made a hole through the full 12 mm thickness. Selecting recess and entering 5 mm left a 7 mm floor. Both retained the 40 × 30 × 12 mm body and centred Ø8 opening. The explicit section drawing generated a through-hole with no question. Cancelling the question saved the cancelled question and no completed result.','',
'Measurements use exported STL sections at Z = 1, 6, 8 and 11 mm, boundary tolerance 0.25 mm, outer-dimension tolerance 0.25 mm and volume tolerance 10 mm³. The section tests distinguish an empty hole from a remaining floor. Mesh tessellation makes volume approximate. All three generated outputs are watertight and have one connected component. The app still reports detailed drawing acceptance separately; these specific offline checks do not silently override its warnings.','',
'[Full measurements](trial-01/summary.json). Each case directory contains inputs, questions, screenshots, raw model responses, answer history, recipe, STL, USDA and diagnostics. The `artifacts` subdirectory preserves the exact submitted image after browser processing.','',
'## Compatibility probes','',
'The agreed wheel, bookend and knob were included, with the saved cable holder and one random case selected before generation. [Selection and fixed random seed](regressions/selection.json). A question in this probe is saved and cancelled, rather than answered with an invented design choice. These are single trials, not reliability estimates.','',
'| Input | Result | Asked a question | Drawing status / error |','|---|---|---|---|']
for reg in sorted(OUT.glob('regressions*/summary.json')):
 for name,c in json.loads(reg.read_text()).items():
  detail=(c.get('error') or {}).get('message') or c.get('drawing_status') or 'not evaluated'
  lines.append(f"| {reg.parent.name}: {name} | {c['status']} | {c['question_requested']} | {detail.replace('|','/')} |")
lines+=['','The initial full probe uses construction-intent-3. Targeted repeats in regressions-02 use construction-intent-4. Both stopped too early on plan uncertainties. Final regressions-03 and trial-03 use construction-intent-5 and drawing-brep-11: opening questions pause the job, while other uncertainties go through the existing recipe validation. Every prior attempt is retained.','', '## Development trial history','']
for prior in sorted(OUT.glob('trial-*/summary.json')):
 lines.append(f'- [{prior.parent.name}]({prior.parent.name}/summary.json): '+', '.join(f"{name}: {c.get('status')}" for name,c in json.loads(prior.read_text()).items()))
lines+=['','## Tests and limits','',
'- The full suite passes 141 tests with the isolated BRep worker enabled. See [tests.txt](tests.txt). One existing Starlette/httpx deprecation warning remains.','- New tests cover invalid and stale answers, depth validation, answer persistence, cancellation, clear plans, unresolved plans, retaining waiting jobs, and reusing measurements. Human response time does not consume the preparation timeout.','- The worker still checks the built solid and mesh. A saved answer is design intent, not proof that every model-generated recipe follows it.','- The model decides whether the opening is ambiguous. These synthetic examples pass; arbitrary doodles and multiple ambiguous openings are not proven by this trial.','- The initial wheel, knob and cable-holder probes stopped on unresolved dimensions. The prompt-only revision did not reliably solve this. The final change removes the overly broad new plan-level stop, preserving the existing recipe-level unresolved-value validation. Follow-up outcomes are shown above; this does not establish reliable interpretation for arbitrary drawings.','- Pending questions are held in the in-memory job registry. A server restart interrupts a pending job; this task does not add persistent job recovery.','- The existing OpenSCAD generation path is unchanged and remains the default. No fresh live OpenSCAD generation is claimed here; regression coverage is from the test suite.','- The first evidence runner stopped after the through-hole build because it was invoked as a script and imported the old editable package. It was rerun as a module and measured the same saved job; no replacement generation was selected. A separate probe runner exited with status 143 and resumed its saved wheel job. Both interruptions are recorded in the runner logs.','',
'## Reproduce','',
'Use the task checkout and its app environment. Configure the isolated worker through `DOODLE_BREP_PYTHON`. Start the app with `DOODLE_RESULTS_DIR=results/brep25` on port 8095.','',
'```sh','python -m pytest -q','python -m scripts.draw_clarification_cases','python -m scripts.check_clarification_product','python -m scripts.check_clarification_regressions','python -m scripts.report_clarification','```','',
'The product runner resumes saved jobs in the selected trial directory. Use a new `BREP_TRIAL` value for new generations. Set `BREP_TRIAL` for the report to select the displayed acceptance trial. Keep previous attempts.','']
text='\n'.join(lines).replace('trial-01/',TRIAL.name+'/')
for prior in sorted(OUT.glob('trial-*/summary.json')):
 text=text.replace(f'[{prior.parent.name}]({TRIAL.name}/summary.json)',f'[{prior.parent.name}]({prior.parent.name}/summary.json)')
(OUT/'README.md').write_text(text)
print('Saved report and comparison image')
