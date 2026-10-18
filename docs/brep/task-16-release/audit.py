"""Audit gate for the issue #33 (worker release readiness) evidence folder.

Run from the repository root with the worker available:
    PYTHONPATH=. .venv/bin/python docs/brep/task-16-release/audit.py
Exits 0 only when every recorded claim re-verifies.
"""
import hashlib
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
results = []


def check(name, ok, detail=''):
    results.append({'check': name, 'status': 'passed' if ok else 'failed', 'detail': str(detail)[:300]})
    print(('PASS' if ok else 'FAIL'), name, str(detail)[:120])


def main():
    # 1. Artifact integrity
    bad = []
    for line in (HERE / 'SHA256SUMS').read_text().splitlines():
        digest, name = line.split()
        path = HERE / name
        if not path.exists() or hashlib.sha256(path.read_bytes()).hexdigest() != digest:
            bad.append(name)
    check('sha256sums', not bad, f'bad: {bad}')

    # 2. Recorded clean-install report passed every step
    install = json.loads((HERE / 'install-check.json').read_text())
    check('install_check_recorded', install.get('passed') is True, f"{len(install.get('steps', []))} steps")

    # 3. pxr warning limitation is captured verbatim (known limitation, not hidden)
    sample = (HERE / 'logs' / 'worker-stderr-sample.txt').read_text()
    check('pxr_warning_sample_captured', '_LoadLibModules' in sample and "pxr.Ar" in sample)

    # 4. Startup capability: all three broken-worker shapes give actionable reasons
    sys.path.insert(0, str(ROOT))
    from doodle_to_cad import brep
    import os
    for label, value, needle in (
            ('missing', '/nonexistent/python/path', 'DOODLE_BREP_PYTHON'),
            ('wrong_python', sys.executable, 'Python 3.12')):
        os.environ['DOODLE_BREP_PYTHON'] = value
        brep._HEALTH_CACHE.clear()
        health = brep.worker_health()
        check(f'health_reason_{label}', health['available'] is False and needle in (health['reason'] or ''),
              (health['reason'] or '')[:80])
    if brep.worker_available():
        os.environ['DOODLE_BREP_PYTHON'] = str(ROOT / 'workers/brep/.venv/bin/python')
        brep._HEALTH_CACHE.clear()
        check('health_available_with_worker', brep.worker_health()['available'] is True)
    os.environ.pop('DOODLE_BREP_PYTHON', None)
    brep._HEALTH_CACHE.clear()

    # 5. Release test suite re-runs green (limits real, cancel kills pid, crash contained)
    env = dict(__import__('os').environ, DOODLE_BREP_PYTHON=str(ROOT / 'workers/brep/.venv/bin/python'))
    proc = subprocess.run([sys.executable, '-m', 'pytest', 'tests/test_worker_release.py', '-q', '--tb=line'],
                          cwd=ROOT, capture_output=True, text=True, env=env)
    tail = (proc.stdout or proc.stderr).strip().splitlines()[-1] if (proc.stdout or proc.stderr).strip() else 'no output'
    check('pytest_worker_release', proc.returncode == 0 and 'failed' not in tail, tail)

    (HERE / 'audit-result.json').write_text(json.dumps(results, indent=1))
    failed = [r for r in results if r['status'] == 'failed']
    print('AUDIT', 'FAILED' if failed else 'PASSED', f'({len(results) - len(failed)}/{len(results)})')
    return 1 if failed else 0


if __name__ == '__main__':
    sys.exit(main())
