"""Audit gate for the issue #32 (targeted recipe edits) evidence folder.

Run from the repository root with the worker available:
    PYTHONPATH=. .venv/bin/python docs/brep/task-15-targeted/audit.py
Exits 0 only when every recorded claim re-verifies. Failures are kept.
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
    results.append({'check': name, 'status': 'passed' if ok else 'failed', 'detail': detail})
    print(('PASS' if ok else 'FAIL'), name, detail)


def main():
    # 1. Artifact integrity
    sums = (HERE / 'SHA256SUMS').read_text().splitlines()
    bad = []
    for line in sums:
        digest, name = line.split()
        path = HERE / name
        if not path.exists() or hashlib.sha256(path.read_bytes()).hexdigest() != digest:
            bad.append(name)
    check('sha256sums', not bad, f'{len(sums)} files, bad: {bad}')

    # 2. Recorded session captured zero unrecorded failures
    failures = json.loads((HERE / 'checks' / 'session_failures.json').read_text())
    check('capture_session_failures_recorded', isinstance(failures, list) and not failures,
          f'{len(failures)} recorded')

    # 3. UI statuses contain the measured check reports
    pocket = (HERE / 'checks' / 'pocket_depth_status.txt').read_text()
    check('pocket_preview_reported_checks', 'checks passed' in pocket and '✗' not in pocket, pocket[:80])
    fillet = (HERE / 'checks' / 'fillet_status.txt').read_text()
    check('fillet_preview_reported_checks', 'checks passed' in fillet and '✗' not in fillet, fillet[:80])
    noop = (HERE / 'checks' / 'pocket_noop_saved_unchanged.json').read_text()
    check('noop_saved_result_unchanged', '"unchanged": true' in noop)

    # 4. API guards recorded the right rejections
    guards = json.loads((HERE / 'checks' / 'api_guards.json').read_text())
    check('guard_stale_selection_409', guards['stale_selection']['status'] == 409)
    check('guard_unsupported_operation_422', guards['unsupported_operation']['status'] == 422)
    check('guard_wrong_target_422', guards['wrong_target_operation']['status'] == 422)

    # 5. Construction tests (includes planted-error fixtures) re-run green
    proc = subprocess.run([sys.executable, '-m', 'pytest', 'tests/test_targeted_edits.py', '-q', '--tb=line'],
                          cwd=ROOT, capture_output=True, text=True)
    tail = proc.stdout.strip().splitlines()[-1] if proc.stdout.strip() else proc.stderr[-200:]
    check('pytest_targeted_edits', proc.returncode == 0 and 'failed' not in tail, tail)

    (HERE / 'audit-result.json').write_text(json.dumps(results, indent=1))
    failed = [r for r in results if r['status'] == 'failed']
    print('AUDIT', 'FAILED' if failed else 'PASSED', f'({len(results) - len(failed)}/{len(results)})')
    return 1 if failed else 0


if __name__ == '__main__':
    sys.exit(main())
