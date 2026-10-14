"""Cancellable process boundary for the existing generation job registry."""
import asyncio
import json
import os
from pathlib import Path
import shutil
import signal
import sys
import tempfile

from .brep import worker_python
from .build_contract import BuildError
from .config import ROOT


async def check_worker():
    """Reject missing, non-executable, or incompatible workers before job creation."""
    python = worker_python()
    if not os.access(python, os.X_OK):
        raise BuildError('backend_unavailable', 'The configured BRep worker is not executable')
    process = await asyncio.create_subprocess_exec(python, '-I', '-c',
        'import sys; from importlib.metadata import version; assert sys.version_info[:2] == (3,12); assert version("usd-brep") == "1.0.0"',
        stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.DEVNULL)
    try:
        await asyncio.wait_for(process.wait(), 10)
        if process.returncode:
            raise BuildError('backend_unavailable', 'Worker requires Python 3.12 and usd-brep==1.0.0')
    finally:
        if process.returncode is None:
            process.kill()
            await process.wait()


async def _docker_cleanup(job_id):
    if not shutil.which('docker'):
        return
    # Only containers started by this job carry this unique label.
    process = await asyncio.create_subprocess_exec('docker', 'ps', '-aq', '--filter',
        f'label=doodle-to-cad.job={job_id}', stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.DEVNULL)
    try:
        output, _ = await asyncio.wait_for(process.communicate(), 10)
    except asyncio.TimeoutError:
        process.kill()
        await process.wait()
        return
    ids = output.decode().split()
    if ids:
        process = await asyncio.create_subprocess_exec('docker', 'rm', '-f', *ids,
            stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.DEVNULL)
        try:
            await asyncio.wait_for(process.wait(), 10)
        except asyncio.TimeoutError:
            process.kill()
            await process.wait()


async def _stop(process, job_id):
    # The job runner, kernel, and local renderers share a new process group.
    try:
        os.killpg(process.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass
    await process.wait()
    await _docker_cleanup(job_id)


async def run_recipe_job(job, recipe, results_dir: Path, save_result, *, prepare=None, repair=None):
    job_id = job['job_id']
    process = None
    temporary = None
    try:
        # Stage outside the served results tree. Nothing partial is downloadable.
        temporary = tempfile.TemporaryDirectory(prefix='.recipe-job-', dir=results_dir.parent)
        out = Path(temporary.name) / job_id
        out.mkdir()
        if prepare is not None:
            job['stage'] = 'interpreting drawing'
            async with asyncio.timeout(600):
                recipe = await prepare(out)
        history = []
        for attempt in range(1, 4 if repair is not None else 2):
            attempt_dir = out / 'construction-attempts' / str(attempt)
            attempt_dir.mkdir(parents=True)
            (attempt_dir / 'recipe.json').write_text(json.dumps(recipe, indent=2))
            for stale in ('error.json', 'built.json', 'stage.txt'):
                (out / stale).unlink(missing_ok=True)
            record = {'attempt': attempt, 'status': 'building'}
            history.append(record)
            try:
                (out / 'input.recipe.json').write_text(json.dumps(recipe))
                with (out / 'runner.log').open('wb') as log:
                    launch = asyncio.create_task(asyncio.create_subprocess_exec(
                        sys.executable, '-m', 'doodle_to_cad.recipe_job_worker', str(out), cwd=ROOT,
                        env={**os.environ, 'DOODLE_JOB_ID': job_id}, start_new_session=True,
                        stdout=log, stderr=log))
                    try:
                        process = await asyncio.shield(launch)
                    except asyncio.CancelledError:
                        process = await launch
                        raise
                    job['worker_pid'] = process.pid
                    job['stage'] = 'building recipe'
                    async with asyncio.timeout(900):
                        while process.returncode is None:
                            stage = out / 'stage.txt'
                            if stage.exists():
                                job['stage'] = stage.read_text()
                            try:
                                await asyncio.wait_for(process.wait(), .1)
                            except asyncio.TimeoutError:
                                pass
                    if process.returncode:
                        error_file = out / 'error.json'
                        error = json.loads(error_file.read_text()) if error_file.exists() else {'message': 'Recipe worker stopped unexpectedly', 'code': 'build_failed'}
                        raise BuildError(error['code'], error['message'])
                    job['stage'] = 'publishing recipe'
                    built = json.loads((out / 'built.json').read_text())
                    # Complete subprocess cleanup before advertising a terminal result.
                    await _stop(process, job_id)
                    process = None
                    record['status'] = 'built'
                    (out / 'build-history.json').write_text(json.dumps(history, indent=2))
                    result = save_result(out, recipe, built)
                out.rename(results_dir / job_id)
                job.update(status='done', stage='done', result=result)
                break
            except BuildError as exc:
                record.update(status='failed', error={'code': exc.code, 'message': str(exc)})
                (out / 'build-history.json').write_text(json.dumps(history, indent=2))
                (attempt_dir / 'failure.json').write_text(json.dumps(record['error'], indent=2))
                if (out / 'runner.log').exists():
                    shutil.copyfile(out / 'runner.log', attempt_dir / 'runner.log')
                if process is not None:
                    await _stop(process, job_id)
                    process = None
                if repair is None or attempt == 3:
                    raise
                job['stage'] = 'correcting BRep construction'
                async with asyncio.timeout(600):
                    recipe = await repair(out, recipe, record['error'], attempt)
    except asyncio.CancelledError:
        job.update(status='cancelling', stage='cancelling', error={'message': 'Recipe job cancelled', 'code': 'cancelled'})
        raise
    except asyncio.TimeoutError:
        job.update(status="error", stage="failed", error={"message": "BRep job exceeded its stage time limit", "code": "timeout"})
    except Exception as exc:
        job.update(status='error', stage='failed', error={'message': str(exc), 'code': getattr(exc, 'code', 'build_failed')})
    finally:
        try:
            if process is not None:
                await _stop(process, job_id)
        finally:
            if temporary is not None:
                # Direct generation retains inputs, model outputs and failures for review.
                # A failed run has no result.json and cannot replace a completed result.
                if prepare is not None and out.exists():
                    (out / 'result.json').unlink(missing_ok=True)
                    (out / 'failure.json').write_text(json.dumps(job.get('error'), indent=2))
                    out.rename(results_dir / job_id)
                temporary.cleanup()
            if job['status'] == 'cancelling':
                job.update(status='cancelled', stage='cancelled')
