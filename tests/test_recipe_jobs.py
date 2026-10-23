import asyncio
import json
import os
from pathlib import Path
import sys
import time
from doodle_to_cad.brep import worker_available

import pytest

from doodle_to_cad import recipe_jobs
from doodle_to_cad.build_contract import BuildError


def test_cancellation_stops_process_group_and_never_publishes(tmp_path, monkeypatch):
    """Exercise real processes: the runner spawns a long-running child."""
    real_spawn = asyncio.create_subprocess_exec
    pid_file = tmp_path / 'child.pid'
    script = ('import subprocess,sys,time; from pathlib import Path; '
              'p=subprocess.Popen([sys.executable,"-c","import time; time.sleep(60)"]); '
              f'Path({str(pid_file)!r}).write_text(str(p.pid)); time.sleep(60)')
    async def spawn(*args, **kwargs):
        if 'doodle_to_cad.recipe_job_worker' in args:
            return await real_spawn(sys.executable, '-c', script, **kwargs)
        return await real_spawn(*args, **kwargs)
    monkeypatch.setattr(recipe_jobs.asyncio, 'create_subprocess_exec', spawn)
    async def no_docker(_): pass
    monkeypatch.setattr(recipe_jobs, '_docker_cleanup', no_docker)
    output=tmp_path/'results';output.mkdir()
    prior=output/'previous';prior.mkdir();(prior/'result.json').write_text('previous result')
    job={'job_id':'abc123abc123','status':'running','result':None}
    async def scenario():
        task=asyncio.create_task(recipe_jobs.run_recipe_job(job,{},output,lambda *a: pytest.fail('Cancelled build must not publish')))
        for _ in range(200):
            if pid_file.exists(): break
            await asyncio.sleep(.01)
        assert pid_file.exists()
        task.cancel()
        with pytest.raises(asyncio.CancelledError): await task
    asyncio.run(scenario())
    assert job['status']=='cancelled' and job['result'] is None
    assert not (output/job['job_id']).exists()
    assert not list(tmp_path.glob('.recipe-job-*'))
    assert (prior/'result.json').read_text()=='previous result'
    child=int(pid_file.read_text())
    # An orphan may briefly be a zombie until init reaps it; it cannot run.
    stat=Path(f'/proc/{child}/stat')
    # SIGKILL has been sent to the whole group. The child may need one
    # scheduler turn after the parent is reaped before /proc shows its exit.
    deadline=time.monotonic()+1
    while stat.exists() and stat.read_text().split()[2]!='Z' and time.monotonic()<deadline:
        time.sleep(.01)
    assert not stat.exists() or stat.read_text().split()[2]=='Z'
    with pytest.raises(ProcessLookupError):os.kill(job['worker_pid'],0)


def test_missing_worker_is_rejected_before_job_creation(monkeypatch):
    from fastapi.testclient import TestClient
    from doodle_to_cad import app
    monkeypatch.setenv('DOODLE_BREP_PYTHON','/missing/python')
    before=set(app.JOBS)
    recipe=json.loads(Path('benchmarks/brep-v2/bookend.json').read_text())
    with TestClient(app.app) as client:
        response=client.post('/api/brep/jobs',json=recipe)
    assert response.status_code==422
    assert response.json()['detail']['code']=='backend_unavailable'
    assert set(app.JOBS)==before


@pytest.mark.skipif(not worker_available(),reason='Isolated worker not configured')
def test_real_recipe_job_reload_and_download_contract(tmp_path,monkeypatch):
    from dataclasses import replace
    from fastapi.testclient import TestClient
    from doodle_to_cad import app
    monkeypatch.setattr(app,'settings',replace(app.settings,results_dir=tmp_path))
    recipe=json.loads(Path('benchmarks/brep-v2/bookend.json').read_text())
    with TestClient(app.app) as client:
        response=client.post('/api/brep/jobs',json=recipe)
        assert response.status_code==200,response.text
        job_id=response.json()['job_id']
        for _ in range(600):
            data=client.get('/api/generate/'+job_id).json()
            if data['status']!='running':break
            time.sleep(.1)
        assert data['status']=='done',data
        assert data['result']['backend']=='usd-brep'
        assert 'score' not in data['result']['evaluation']
        assert not data['result']['success']
        assert (tmp_path/job_id/'result.json').exists()
        for key in ('stl','source','usd'):
            relative=data['result']['files'][key].removeprefix('/results/')
            assert (tmp_path/relative).is_file()
        app.JOBS.pop(job_id)
        restored=client.get('/api/generate/'+job_id).json()
        assert restored['result']==data['result']


def test_incompatible_worker_probe_fails(monkeypatch):
    monkeypatch.setattr(recipe_jobs,'worker_python',lambda:sys.executable)
    with pytest.raises(BuildError,match='Python 3.12'):
        asyncio.run(recipe_jobs.check_worker())
