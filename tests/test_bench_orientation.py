"""Known geometric answers independent of the frozen noisy drawings."""
import numpy as np
import trimesh
from scripts.bench_orientation import cube_rotations, render_mask, normalize_mask, register_mesh


def asymmetric_mesh():
    # Two non-overlapping boxes retain different dimensions in all views.
    a = trimesh.creation.box(extents=[60, 10, 35])
    b = trimesh.creation.box(extents=[15, 30, 10]); b.apply_translation([32, 17, 21])
    return trimesh.util.concatenate([a, b])


def targets(mesh):
    return {d: normalize_mask(render_mask(mesh, np.eye(3), d)) for d in ('front','right','top')}


def test_rotations_are_proper_unique_and_identity_first():
    rs = cube_rotations()
    assert len({tuple(r.ravel()) for r in rs}) == 24
    assert np.array_equal(rs[0], np.eye(3))
    assert all(round(np.linalg.det(r)) == 1 and np.array_equal(r @ r.T, np.eye(3)) for r in rs)


def test_one_rigid_pose_recovers_all_views():
    mesh = asymmetric_mesh(); ts = targets(mesh)
    rotated = mesh.copy(); rotated.vertices = rotated.vertices @ cube_rotations()[9].T
    report = register_mesh(rotated, ts)
    assert report['identity']['minimum_iou'] < .9
    assert report['registered']['minimum_iou'] == 1
    assert report['status'] == 'diagnostic_only'


def test_independent_view_cheating_is_not_allowed():
    mesh = asymmetric_mesh(); ts = targets(mesh)
    # Each target can be explained by some pose, but not one common pose.
    ts['top'] = normalize_mask(render_mask(mesh, cube_rotations()[9], 'top'))
    report = register_mesh(mesh, ts)
    assert all(max(t['scores'][d] for t in report['candidates']) == 1 for d in ts)
    assert report['registered']['minimum_iou'] < .95


def test_wrong_geometry_is_not_repaired_by_registration():
    mesh = asymmetric_mesh(); wrong = trimesh.creation.box(extents=[60, 10, 35])
    report = register_mesh(wrong, targets(mesh))
    assert report['registered']['minimum_iou'] < .8
