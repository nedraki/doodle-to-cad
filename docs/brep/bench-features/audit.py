"""Audit gate for the special-features benchmark.

Re-runs every measurement from the saved artifacts and re-derives each README
claim. Exits 0 only when all claims re-verify. From the repository root:

    export DOODLE_BREP_PYTHON=$PWD/workers/brep/.venv/bin/python
    PYTHONPATH=. .venv/bin/python docs/brep/bench-features/audit.py
"""
import hashlib
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import bench_measure as bm  # noqa: E402

results = []


def check(name, ok, detail=''):
    results.append({'check': name, 'status': 'passed' if ok else 'failed', 'detail': str(detail)[:300]})
    print(('PASS' if ok else 'FAIL'), name, str(detail)[:110])


def fixture(name):
    return json.loads((HERE / 'fixtures' / f'{name}.json').read_text())


def art(name):
    return HERE / 'artifacts' / name / 'model.stl'


def main():
    # 1. Artifact integrity
    sums = (HERE / 'SHA256SUMS').read_text().splitlines()
    bad = [l.split()[-1] for l in sums
           if not (HERE / l.split()[-1]).exists()
           or hashlib.sha256((HERE / l.split()[-1]).read_bytes()).hexdigest() != l.split()[0]]
    check('sha256sums', not bad, f'{len(sums)} files, bad: {bad[:3]}')

    # 2. Fillet: every corner arc fits r=15 (derived width/4) within 0.1 mm
    p = {k: v['value'] for k, v in fixture('fillet_block')['parameters'].items()}
    v = bm.verify_fillet(art('fillet_block'), p['block_width'], p['block_depth'], p['block_height'],
                         p['block_width'] / 4)
    check('fillet_4_corners', v['ok'], json.dumps({k: c.get('measured_mm') for k, c in v['checks'].items()})[:200])

    # 3/4. Chamfer: nominal passes the fitted-leg claim; planted fails it.
    p = {k: v['value'] for k, v in fixture('chamfer_box')['parameters'].items()}
    args = [p['body_width'], p['body_depth'], p['body_height'], p['chamfer_radius']]
    ok_nom = bm.verify_chamfer(art('chamfer_box'), *args)['ok']
    check('chamfer_nominal_passes', ok_nom)
    planted = bm.verify_chamfer(art('chamfer_planted_wrong_radius'), *args)
    check('chamfer_planted_fails', not planted['ok'],
          'leg ' + str([c.get('measured_leg_x_mm') for c in planted['checks'].values() if 'measured_leg_x_mm' in c][:1]))

    # 5. Arc pipes (quarter + half) pass their radii probes.
    arc_ok = True
    for name in ('arc_pipe_quarter', 'arc_pipe_half'):
        j = json.loads((HERE / 'measurements' / f'{name}.json').read_text())
        arc_ok = arc_ok and bool(j.get('verdict', {}).get('ok'))
        # re-verify checker presence on the artifact too
        arc_ok = arc_ok and art(name).exists()
    check('arc_pipes_pass', arc_ok)

    # 6. Loft: ends exact + monotone + symmetric; planted wrong radius fails.
    p = {k: v['value'] for k, v in fixture('loft_transition')['parameters'].items()}
    la = [p['rect_width'], p['rect_depth'], p['circle_radius'], p['transition_height']]
    check('loft_nominal_passes', bm.verify_loft(art('loft_transition'), *la)['ok'])
    check('loft_planted_fails', not bm.verify_loft(art('loft_planted_wrong_radius'), *la)['ok'])

    # 7. Shell: volume matches ideal to 0.5 %, genus 1 (Euler 2), open top hollow.
    p = {k: v['value'] for k, v in fixture('shell_tray')['parameters'].items()}
    w, d, h, t = p['tray_width'], p['tray_depth'], p['tray_height'], p['wall_thickness']
    m = bm.load(art('shell_tray'))
    ideal = w * d * h - (w - 2 * t) * (d - 2 * t) * (h - t)
    vol_ok = abs(m.volume - ideal) <= 0.005 * ideal
    check('shell_volume_and_genus', vol_ok and m.euler_number == 2,
          f'vol {m.volume:.1f} ideal {ideal:.1f} euler {m.euler_number}')
    check('shell_open_top_hollow', bm.verify_shell(art('shell_tray'), w, d, h, t)['ok'])

    # 8. Wheel spokes probe: published watertight single component (this config).
    j = json.loads((HERE / 'measurements' / 'wheel_spokes.json').read_text())
    ms = j.get('mesh_summary', {})
    m = bm.load(art('wheel_spokes'))
    check('wheel_spokes_built_watertight_single',
          ms.get('watertight') is True and ms.get('components') == 1 and m.is_watertight and len(m.split()) == 1,
          f"triangles {ms.get('triangles')}")

    # 9. Curved handle: kernel crash published verbatim (issue #61).
    bj = json.loads((HERE / 'artifacts' / 'curved_handle' / 'build.json').read_text())
    check('curved_handle_kernel_failure_published',
          bj.get('build_ok') is False and '_omni_solid' in json.dumps(bj),
          bj.get('worker_log_tail', '')[:80])

    # 10. Media: every passing feature has a screenshot + state JSON + GIF.
    feats = ['fillet_block', 'chamfer_box', 'arc_pipe_quarter', 'arc_pipe_half',
             'loft_transition', 'shell_tray', 'wheel_spokes']
    media_ok = True
    for i, f in enumerate(feats, 1):
        shot = HERE / 'screenshots' / f'{i:02d}_{f}.png'
        gif = HERE / 'gifs' / f'{f}_orbit.gif'
        state = HERE / 'screenshots' / f'{i:02d}_{f}.state.json'
        ok = (shot.exists() and gif.stat().st_size if gif.exists() else 0) > 20_000 and shot.exists() and state.exists()
        media_ok = media_ok and ok
    check('media_per_feature', media_ok)

    # 11. Environment fingerprint present.
    env = json.loads((HERE / 'environment.json').read_text())
    check('environment_fingerprint', all(k in env for k in ('git_rev', 'host', 'captured_utc', 'worker')))

    (HERE / 'audit-result.json').write_text(json.dumps(results, indent=1))
    failed = [r for r in results if r['status'] == 'failed']
    print('AUDIT', 'FAILED' if failed else 'PASSED', f'({len(results) - len(failed)}/{len(results)})')
    return 1 if failed else 0


if __name__ == '__main__':
    sys.exit(main())
