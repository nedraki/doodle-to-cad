"""Contract failures must not expose stale output or lose a usable revision."""
import json
import subprocess

import pytest
import trimesh

from doodle_to_cad.build_contract import BuildInput, CAMERAS, build
from doodle_to_cad import openscad, brep


def test_failed_scad_removes_stale_mesh(tmp_path, monkeypatch):
    source = tmp_path / 'model.scad'
    source.write_text('invalid')
    (tmp_path / 'model.stl').write_bytes(b'stale mesh')
    monkeypatch.setattr(openscad, 'run', lambda *a, **k: (False, 'syntax error'))
    result = build(BuildInput('openscad', source, tmp_path))
    assert not result.ok and result.stl is None
    assert result.diagnostics[0].code == 'build_failed'
    assert not (tmp_path / 'model.stl').exists()


def test_render_failure_keeps_geometry_but_not_stale_views(tmp_path, monkeypatch):
    source = tmp_path / 'model.scad'
    source.write_text('cube([10,20,30]);')
    for view in CAMERAS:
        (tmp_path / f'view-{view}.png').write_bytes(b'stale')
    def run(args, **kwargs):
        if args[1] == '-o':
            trimesh.creation.box([10,20,30]).export(tmp_path / 'model.stl')
            return True, ''
        return False, 'renderer unavailable'
    monkeypatch.setattr(openscad, 'run', run)
    result = build(BuildInput('openscad', source, tmp_path))
    assert result.ok and not result.views
    assert result.measurements['extents_mm'] == [10,20,30]
    assert result.diagnostics[0].code == 'render_failed'
    assert result.diagnostics[0].severity == 'warning'
    assert not list(tmp_path.glob('view-*.png'))
    assert result.metadata()['drawing_evaluated'] is False


def test_scad_timeout_code(tmp_path, monkeypatch):
    source = tmp_path / 'model.scad'
    source.write_text('cube(1);')
    monkeypatch.setattr(openscad.shutil, 'which', lambda _: '/openscad')
    def timeout(*args, **kwargs):
        raise subprocess.TimeoutExpired(args[0], 180)
    monkeypatch.setattr(openscad.subprocess, 'run', timeout)
    result = build(BuildInput('openscad', source, tmp_path, render=False))
    assert not result.ok
    assert result.diagnostics[0].code == 'timeout'


def test_brep_bad_source_is_structured(tmp_path):
    source = tmp_path / 'bad.json'
    source.write_text('{')
    result = build(BuildInput('usd-brep', source, tmp_path))
    assert not result.ok
    assert result.diagnostics[0].code == 'invalid_input'
    assert not list(tmp_path.glob('brep-*'))


def test_brep_missing_worker_output_is_not_published(tmp_path, monkeypatch):
    from pathlib import Path
    source = Path('benchmarks/brep/bracket.json')
    monkeypatch.setattr(brep, 'worker_python', lambda: '/python')
    class OkEmptyPopen:
        returncode = 0
        def __init__(self, *args, **kwargs): pass
        def communicate(self, timeout=None): return ('', '')
        def kill(self): pass
    monkeypatch.setattr(brep.subprocess, 'Popen', OkEmptyPopen)
    result = build(BuildInput('usd-brep', source, tmp_path))
    assert not result.ok
    assert result.diagnostics[0].code == 'invalid_output'
    assert not list(tmp_path.iterdir())
