"""Benchmark-only rigid registration. Never changes product acceptance.

A single proper cube rotation must explain every registered view. The score
is silhouette IoU, NOT the historical edge/profile metric; no historical
threshold is transferred to it. Rendering ignores lighting and tessellation
edges. Perspective, occluded edges and ambiguous ink remain limitations.
"""
from itertools import permutations, product
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw
import trimesh

from doodle_to_cad.evaluation import _decode, _normalized_profile, assign_view_groups

# Screen right/up in the canonical world frame (matching the camera views).
AXES = {'front': (0, 2, 1, 1), 'top': (0, 1, 1, 1),
        'right': (1, 2, 1, 1), 'left': (1, 2, -1, 1),
        'rear': (0, 2, -1, 1), 'bottom': (0, 1, 1, -1)}


def cube_rotations():
    identity = np.eye(3, dtype=int)
    rotations = []
    for perm in permutations(range(3)):
        for signs in product((-1, 1), repeat=3):
            rotation = identity[list(perm)] * np.array(signs)[:, None]
            if round(np.linalg.det(rotation)) == 1:
                rotations.append(rotation)
    return sorted(rotations, key=lambda r: (not np.array_equal(r, identity), tuple(r.ravel())))


def render_mask(mesh, rotation, direction, size=384):
    ua, va, us, vs = AXES[direction]
    verts = np.asarray(mesh.vertices) @ rotation.T
    points = verts[:, [ua, va]] * [us, vs]
    extent = np.ptp(points, axis=0)
    span = float(max(extent))
    if not np.isfinite(span) or span <= 0:
        raise ValueError('Mesh has no finite projected area')
    center = (points.max(axis=0) + points.min(axis=0)) / 2
    points = (points - center) * ((size - 24) / span)
    points[:, 0] += size / 2
    points[:, 1] = size / 2 - points[:, 1]
    canvas = Image.new('L', (size, size), 0)
    draw = ImageDraw.Draw(canvas)
    for triangle in points[np.asarray(mesh.faces)]:
        draw.polygon([tuple(p) for p in triangle], fill=255)
    return np.array(canvas)


def normalize_mask(mask):
    points = cv2.findNonZero(mask)
    if points is None:
        return np.zeros((96, 96), np.uint8)
    x, y, w, h = cv2.boundingRect(points)
    scale = 88 / max(w, h)
    resized = cv2.resize(mask[y:y+h, x:x+w], (max(1, round(w*scale)), max(1, round(h*scale))), interpolation=cv2.INTER_NEAREST)
    out = np.zeros((96, 96), np.uint8)
    oy, ox = (96-resized.shape[0])//2, (96-resized.shape[1])//2
    out[oy:oy+resized.shape[0], ox:ox+resized.shape[1]] = resized
    return out


def mask_iou(a, b):
    union = np.count_nonzero((a > 0) | (b > 0))
    return float(np.count_nonzero((a > 0) & (b > 0)) / union) if union else 0.0


def source_masks(source, evidence, primary='front', standard='third-angle'):
    image = _decode(source)
    if image is None:
        raise ValueError('Cannot decode drawing')
    h, w = image.shape[:2]
    masks = {}
    for direction, group in assign_view_groups(evidence, primary, standard).items():
        if direction not in AXES:
            raise ValueError(f'Unsupported view: {direction}')
        x, y, gw, gh = group['bbox_normalized']
        crop = image[max(0,int(y*h)):min(h,int((y+gh)*h)), max(0,int(x*w)):min(w,int((x+gw)*w))]
        if not crop.size:
            raise ValueError(f'Empty view crop: {direction}')
        masks[direction] = _normalized_profile(crop, render=False)[0]
    if not masks:
        raise ValueError('No registered views')
    return masks


def register_mesh(mesh, targets):
    """Maximize the worst view, then mean; stable identity-first tie break."""
    trials, best, best_rank = [], None, None
    # Cubic rotations only permute/sign projected axes; cache identical views.
    cache = {}
    for rotation in cube_rotations():
        scores = {}
        for direction, target in targets.items():
            ua, va, us, vs = AXES[direction]
            key = tuple(np.r_[rotation[ua]*us, rotation[va]*vs])
            if key not in cache:
                cache[key] = normalize_mask(render_mask(mesh, rotation, direction))
            scores[direction] = mask_iou(target, cache[key])
        rank = (min(scores.values()), sum(scores.values()) / len(scores))
        trial = {'rotation': rotation.tolist(), 'scores': scores, 'minimum_iou': rank[0], 'mean_iou': rank[1]}
        trials.append(trial)
        if best_rank is None or rank > best_rank:
            best, best_rank = trial, rank
    return {'metric': 'silhouette_iou_joint_cube_rotation_v1', 'status': 'diagnostic_only',
            'identity': trials[0], 'registered': best, 'candidates': trials}


def evaluate_orientation(stl, source, evidence, output, primary='front'):
    mesh = trimesh.load_mesh(stl, process=True)
    if not isinstance(mesh, trimesh.Trimesh) or not len(mesh.faces):
        raise ValueError('Expected nonempty triangle mesh')
    targets = source_masks(source, evidence, primary)
    report = register_mesh(mesh, targets)
    output = Path(output); output.mkdir(parents=True, exist_ok=True)
    for direction, target in targets.items():
        Image.fromarray(255-target).resize((384,384)).save(output/f'{direction}-drawing.png')
        for name in ('identity', 'registered'):
            mask = normalize_mask(render_mask(mesh, np.array(report[name]['rotation']), direction))
            Image.fromarray(255-mask).resize((384,384)).save(output/f'{direction}-{name}.png')
    return report


def opening_positions(mask):
    """Visible background islands; not proof of through-holes (use mesh genus)."""
    contours, hierarchy = cv2.findContours(mask, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
    if hierarchy is None:
        return []
    centers = []
    for contour, link in zip(contours, hierarchy[0]):
        if link[3] < 0:
            continue
        moments = cv2.moments(contour)
        if moments['m00'] >= 2:
            centers.append([moments['m10']/moments['m00']/mask.shape[1], moments['m01']/moments['m00']/mask.shape[0]])
    return centers


def opening_displacement(reference_mask, candidate_mask):
    """Symmetric nearest-centre displacement; counts are reported separately.

    Diagnostic only: nearest-centre matching is not a bijection and image
    extraction is not a certified feature annotation.
    """
    a, b = opening_positions(reference_mask), opening_positions(candidate_mask)
    if not a or not b:
        distance = 0.0 if not a and not b else None
    else:
        distances = np.linalg.norm(np.array(a)[:,None,:] - np.array(b)[None,:,:], axis=2)
        distance = float(max(distances.min(axis=0).max(), distances.min(axis=1).max()))
    return {'expected_count':len(a), 'actual_count':len(b), 'max_nearest_center_shift':distance}
