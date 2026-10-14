"""Replay failed model recipes through live, guarded construction correction.
These are not new drawing generations. Do not count them as drawing fidelity checks.
"""
import asyncio
import json
import os
from pathlib import Path
import shutil
import time
import uuid

from doodle_to_cad.app import pipeline, _save_brep_result
from doodle_to_cad.direct_brep import correct_construction, PROMPT_VERSION, PROMPT, CORRECTION_PROMPT_VERSION
from doodle_to_cad.recipe_jobs import run_recipe_job
from doodle_to_cad.build_contract import BuildError

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'docs/brep/task-06/correction-01/replayed-failures'
RESULTS=ROOT/'results/brep-direct-corrections'
SOURCES={'wheel':'b84fcad7db3f','knob':'4c52461e6c88'}

async def run(name,source_id):
    source=ROOT/'results/brep-direct-product'/source_id
    recipe=json.loads((source/'input.recipe.json').read_text())
    run_id=uuid.uuid4().hex[:12]
    job={'job_id':run_id,'status':'running','created':time.monotonic(),'result':None,'error':None}
    model=(await pipeline.client.discover()).selected
    metadata={'path':'saved-failure-correction','source_run':source_id,'model':model,'prompt_version':PROMPT_VERSION,
              'correction_prompt_version':CORRECTION_PROMPT_VERSION,'maximum_dimension_mm':120,'drawing_fidelity_verified':False}
    async def prepare(out):
        shutil.copyfile(source/'input.png',out/'input.png')
        (out/'generation.json').write_text(json.dumps(metadata,indent=2))
        (out/'recipe-prompt.txt').write_text(PROMPT)
        return recipe
    async def repair(out,current,failure,attempt):
        return await correct_construction(pipeline,out,current,failure,attempt,120)
    def publish(out,current,built):
        extents=built['build']['measurements']['extents_mm']
        if max(extents)>120.5:
            raise BuildError('dimension_exceeded',f'extents_mm={extents} exceed requested maximum 120 mm')
        result=_save_brep_result(out,current,built)
        metadata['construction_attempts']=json.loads((out/'build-history.json').read_text())
        result.update(generation=metadata,model=model)
        (out/'generation.json').write_text(json.dumps(metadata,indent=2))
        (out/'result.json').write_text(json.dumps(result,indent=2))
        return result
    print(name,run_id,'started',flush=True)
    await run_recipe_job(job,recipe,RESULTS,publish,prepare=prepare,repair=repair)
    dest=OUT/name;dest.mkdir(parents=True,exist_ok=True)
    shutil.copytree(RESULTS/run_id,dest/'artifacts'/run_id,dirs_exist_ok=True)
    (dest/'job.json').write_text(json.dumps(job,indent=2))
    print(name,job['status'],job['error'],flush=True)
    return {'id':run_id,'source_id':source_id,'status':job['status'],'error':job['error']}

async def main():
    OUT.mkdir(parents=True,exist_ok=True)
    summary={}
    for name,source in SOURCES.items():
        summary[name]=await run(name,source)
        (OUT/'summary.json').write_text(json.dumps(summary,indent=2))

if __name__=='__main__':asyncio.run(main())
