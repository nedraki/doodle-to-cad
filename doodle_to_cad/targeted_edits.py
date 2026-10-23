"""Targeted edits on a selected target: plan a bounded recipe change, then measure it.

The planner only edits recipe data (never generated code) and rejects anything
outside the supported subset with a useful message. The verifier measures the
exported meshes independently of the kernel and of the recipe, so a green report
means the requested change is visible and the preserved dimensions did not move.
"""
from copy import deepcopy
import math

import numpy as np
import trimesh

CHANGE_TOLERANCE = 0.05   # mm a requested change must be measured within
PRESERVE_TOLERANCE = 0.005  # mm a preserved dimension must not move
PROBE_STEP = 0.02


def _literal(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def plan(recipe, rule, value, bounds=None):
    """Return (edited_recipe, edit) or raise ValueError with a user-facing reason."""
    if not _literal(value) or value <= 0:
        raise ValueError("The requested change must be a positive number in millimetres.")
    kind = (rule or {}).get("kind")
    if kind == "box_cutout":
        return _plan_pocket(recipe, rule, float(value))
    if kind == "outer_vertical_edges":
        return _plan_fillet(recipe, rule, float(value), bounds)
    raise ValueError("This selection cannot be changed yet. Supported: deepen a selected "
                     "box pocket, or round the selected outer vertical edges.")


def _operations(recipe):
    return {op["id"]: op for op in recipe.get("operations", [])}


def _plan_pocket(recipe, rule, depth):
    from .brep_recipe import validate_recipe
    ops = _operations(recipe)
    difference = ops.get(rule.get("owner"))
    if not isinstance(difference, dict) or difference.get("kind") != "difference" \
            or difference.get("right") != rule.get("cutter"):
        raise ValueError("The selected pocket is no longer a box cut from a body. Select the target again.")
    cutter = ops.get(rule["cutter"])
    if not isinstance(cutter, dict) or cutter.get("kind") != "box":
        raise ValueError("The pocket cutter is no longer a supported box.")
    if not all(_literal(v) for v in (*cutter["origin"], *cutter["size"])):
        raise ValueError("This pocket cutter uses named parameters. Use the parameter controls for it.")
    left = ops.get(difference.get("left"))
    if not isinstance(left, dict) or left.get("kind") != "box":
        raise ValueError("Only pockets cut directly from a box body are supported for now.")
    if not all(_literal(v) for v in (*left["origin"], *left["size"])):
        raise ValueError("The pocket body uses named parameters. Use the parameter controls for it.")
    lo_b = [left["origin"][i] for i in range(3)]
    hi_b = [left["origin"][i] + left["size"][i] for i in range(3)]
    origin, size = cutter["origin"], cutter["size"]
    bottom, top = origin[2], origin[2] + size[2]

    def spans(axis):
        return origin[axis] <= lo_b[axis] + 0.001 and origin[axis] + size[axis] >= hi_b[axis] - 0.001

    if abs(top - hi_b[2]) > 0.001:
        if bottom <= lo_b[2] + 0.001 or top >= hi_b[2] - 0.001:
            raise ValueError("Through openings cannot be deepened; use the parameter controls.")
        raise ValueError("Only pockets that open at the top face are supported for now.")
    if bottom <= lo_b[2] + 0.001:
        raise ValueError("Through openings cannot be deepened; use the parameter controls.")
    for axis in (0, 1):
        if spans(axis):
            raise ValueError("Through openings cannot be deepened; use the parameter controls.")
        if not (origin[axis] > lo_b[axis] and origin[axis] + size[axis] < hi_b[axis]):
            raise ValueError("Only pockets fully inside the outer faces are supported for now.")
    max_depth = round(hi_b[2] - lo_b[2] - 0.01, 6)
    if not 0.01 <= depth <= max_depth:
        raise ValueError(f"Pocket depth must be between 0.01 and {max_depth:g} mm.")
    new_floor = hi_b[2] - depth
    if abs(new_floor - bottom) < 1e-9:
        raise ValueError("The selected pocket already has that depth.")
    edited = deepcopy(recipe)
    target = next(op for op in edited["operations"] if op["id"] == cutter["id"])
    target["origin"][2] = new_floor
    target["size"][2] = depth
    validate_recipe(edited)
    neighbours = []
    for op in recipe["operations"]:
        if op["kind"] != "difference" or op["id"] == difference["id"] or op.get("right") not in ops:
            continue
        other = ops[op["right"]]
        if other.get("kind") != "box" or not all(_literal(v) for v in (*other["origin"], *other["size"])):
            continue
        if abs(other["origin"][2] + other["size"][2] - hi_b[2]) <= 0.001 and other["origin"][2] > lo_b[2] + 0.001:
            neighbours.append({"center": [other["origin"][0] + other["size"][0] / 2,
                                          other["origin"][1] + other["size"][1] / 2],
                               "floor": float(other["origin"][2])})
    edit = {"operation": "pocket_depth", "rule": deepcopy(rule), "cutter": cutter["id"],
            "difference": difference["id"], "value": depth,
            "old_floor": float(bottom), "new_floor": float(new_floor),
            "cutter_center": [origin[0] + size[0] / 2, origin[1] + size[1] / 2],
            "body_top": float(hi_b[2]), "other_pockets": neighbours}
    return edited, edit


def _plan_fillet(recipe, rule, radius, bounds):
    from .brep_recipe import validate_recipe
    if rule.get("owner") != recipe.get("output"):
        raise ValueError("The selected edge group belongs to a different final body. Select the edges again.")
    if bounds is not None:
        extents = [float(hi) - float(lo) for lo, hi in zip(bounds[0], bounds[1])] if len(bounds) == 2 else list(bounds)
        limit = min(extents) / 2 - 0.01
        if radius > limit:
            raise ValueError(f"The fillet radius must stay below {limit:g} mm so opposite rounds do not meet.")
    ids = {op["id"] for op in recipe["operations"]}
    index = 1
    while f"targeted_fillet_{index}" in ids:
        index += 1
    fillet_id = f"targeted_fillet_{index}"
    edited = deepcopy(recipe)
    operation = {"id": fillet_id, "kind": "fillet", "body": rule["owner"],
                 "radius": radius, "selector": "outer_vertical"}
    if edited.get("version") == 2:
        operation.update(frame="world", depends_on=[rule["owner"]], evidence=[])
    edited["operations"].append(operation)
    edited["output"] = fillet_id
    if edited.get("version") == 2 and edited.get("bodies"):
        edited["bodies"][0]["output"] = fillet_id
    validate_recipe(edited)
    return edited, {"operation": "edge_fillet", "rule": deepcopy(rule), "radius": radius, "fillet_op": fillet_id}


def _mesh(path):
    mesh = trimesh.load(path, force="mesh")
    if not mesh.is_watertight or mesh.volume <= 0:
        raise ValueError("The exported mesh failed independent validation before checking.")
    return mesh


RAY_DIRECTION = [0.011, 0.017, 1.0]


def _ray_parity(mesh, points):
    """Point-in-solid by upward-ray crossing parity, vectorised Möller-Trumbore.

    Self-contained: no rtree/shapely. Probe points must avoid exact geometry
    edges (pocket centres and rounded corners do); grazing hits are not robust.
    """
    tri = mesh.triangles
    e1 = tri[:, 1] - tri[:, 0]
    e2 = tri[:, 2] - tri[:, 0]
    d = np.asarray(RAY_DIRECTION, dtype=float)
    d = d / np.linalg.norm(d)
    h = np.cross(d, e2)
    a = np.einsum("ij,ij->i", h, e1)
    valid = np.abs(a) > 1e-12
    inv_a = np.where(valid, 1.0 / np.where(valid, a, 1.0), 0.0)
    origins = np.asarray(points, dtype=float).reshape(-1, 3)
    hits = np.zeros(len(origins), dtype=int)
    for start in range(0, len(origins), 256):
        batch = origins[start:start + 256]
        s = batch[:, None, :] - tri[None, :, 0]
        u = (s * h).sum(2) * inv_a
        q = np.cross(s, e1[None, :, :])
        v = (q * d).sum(2) * inv_a
        t = (q * e2).sum(2) * inv_a
        inside = valid & (u >= -1e-9) & (v >= -1e-9) & (u + v <= 1 + 1e-9) & (t > 1e-9)
        hits[start:start + len(batch)] = inside.sum(1)
    return [int(count) % 2 == 1 for count in hits]


def _inside(mesh, points):
    return _ray_parity(mesh, points)


def _coverage_area(mesh, z, spacing=0.5):
    """Solid area of a horizontal slice by grid sampling; no shapely needed."""
    (x0, y0), (x1, y1) = mesh.bounds[0][:2], mesh.bounds[1][:2]
    xs = np.arange(x0 + spacing / 2, x1, spacing)
    ys = np.arange(y0 + spacing / 2, y1, spacing)
    grid = [(float(x), float(y), z) for x in xs for y in ys]
    solid = sum(_inside(mesh, grid))
    return solid * spacing * spacing


def _probe_floor(mesh, center, top):
    """Floor height under a pocket centre: first solid sample scanning down."""
    x, y = center
    heights = np.arange(top - PROBE_STEP, 0.0, -PROBE_STEP)
    hits = _inside(mesh, [(x, y, float(h)) for h in heights])
    index = int(np.argmax(hits)) if any(hits) else -1
    if index < 0 or not hits[index]:
        return None
    fine = np.arange(float(heights[index]) + PROBE_STEP, float(heights[index]) - PROBE_STEP, -0.002)
    fine_hits = _inside(mesh, [(x, y, float(h)) for h in fine])
    fine_index = int(np.argmax(fine_hits)) if any(fine_hits) else index
    return float(heights[index] + PROBE_STEP - (fine_index + 0.5) * 0.002)


def _surface_distance(mesh, points):
    """Max over points of the distance to the mesh surface (own triangles math; no rtree)."""
    tri = np.asarray(mesh.triangles, dtype=float)
    pts = np.asarray(points, dtype=float).reshape(-1, 3)
    a, b, c = tri[:, 0], tri[:, 1], tri[:, 2]
    n = np.cross(b - a, c - a)
    lengths = np.linalg.norm(n, axis=1, keepdims=True)
    n = np.divide(n, lengths, out=np.zeros_like(n), where=lengths > 0)
    ap = pts[:, None, :] - a
    signed = (ap * n).sum(2)
    same = np.stack([(np.cross(p1 - p0, pts[:, None, :] - p0) * n).sum(2)
                     for p0, p1 in ((a, b), (b, c), (c, a))])
    inside = ((same >= -1e-9).all(0)) | ((same <= 1e-9).all(0))
    edge_dists = []
    for p0, p1 in ((a, b), (b, c), (c, a)):
        e = p1 - p0
        denom = np.maximum((e * e).sum(1), 1e-12)[None, :, None]
        t = np.clip(((pts[:, None, :] - p0) * e).sum(2)[:, :, None] / denom, 0.0, 1.0)
        edge_dists.append(np.linalg.norm(pts[:, None, :] - (p0 + t * e), axis=2))
    per_point = np.where(inside, np.abs(signed), np.minimum.reduce(edge_dists))
    return float(np.max(per_point.min(axis=1)))


def _vertical_corner_edges(mesh):
    """Straight vertical edges at outer XY corners, from the mesh itself."""
    lo, hi = mesh.bounds
    corners = [(lo[0], lo[1]), (hi[0], lo[1]), (lo[0], hi[1]), (hi[0], hi[1])]
    vertices = mesh.vertices
    found = {}
    for a, b in mesh.edges_unique:
        pa, pb = vertices[a], vertices[b]
        if abs(pa[0] - pb[0]) > 1e-6 or abs(pa[1] - pb[1]) > 1e-6:
            continue
        if abs(pa[2] - pb[2]) <= 0.001:
            continue
        for cx, cy in corners:
            if abs(pa[0] - cx) < 1e-6 and abs(pa[1] - cy) < 1e-6:
                key = (cx, cy)
                span = min(pa[2], pb[2]), max(pa[2], pb[2])
                if key in found:
                    prev = found[key]
                    found[key] = (min(prev[0], span[0]), max(prev[1], span[1]))
                else:
                    found[key] = span
    return found


def verify_edit(old_stl, new_stl, edit, edges=None):
    """Measure the candidate against the displayed version. Never trusts the kernel's word."""
    old, new = _mesh(old_stl), _mesh(new_stl)
    checks = {}
    shift = max([abs(a - b) for a, b in zip(old.bounds[0], new.bounds[0])]
                + [abs(a - b) for a, b in zip(old.bounds[1], new.bounds[1])])
    checks["preserved outer dimensions"] = {
        "status": "passed" if shift <= PRESERVE_TOLERANCE else "failed",
        "max_corner_shift_mm": round(float(shift), 5), "tolerance_mm": PRESERVE_TOLERANCE}
    if edit["operation"] == "pocket_depth":
        floor = _probe_floor(new, edit["cutter_center"], edit["body_top"])
        moved = floor is not None and abs(floor - edit["new_floor"]) <= CHANGE_TOLERANCE
        checks["selected pocket floor depth"] = {
            "status": "passed" if moved else "failed",
            "measured_floor_mm": None if floor is None else round(floor, 3),
            "expected_floor_mm": round(edit["new_floor"], 3), "tolerance_mm": CHANGE_TOLERANCE}
        old_floor = _probe_floor(old, edit["cutter_center"], edit["body_top"])
        checks["selected pocket floor actually moved"] = {
            "status": "passed" if old_floor is not None and abs(old_floor - edit["old_floor"]) <= CHANGE_TOLERANCE
            and (floor is None or abs(floor - old_floor) > CHANGE_TOLERANCE) else "failed",
            "previous_floor_mm": None if old_floor is None else round(old_floor, 3)}
        for i, pocket in enumerate(edit["other_pockets"]):
            neighbour = _probe_floor(new, pocket["center"], edit["body_top"])
            stable = neighbour is not None and abs(neighbour - pocket["floor"]) <= CHANGE_TOLERANCE
            checks[f"neighbouring pocket {i + 1} floor"] = {
                "status": "passed" if stable else "failed",
                "measured_floor_mm": None if neighbour is None else round(neighbour, 3),
                "expected_floor_mm": round(pocket["floor"], 3)}
    elif edit["operation"] == "edge_fillet":
        radius = edit["radius"]
        corner_edges = _vertical_corner_edges(old) if edges is None else {
            (float(line[0][0]), float(line[0][1])): (min(float(line[0][2]), float(line[1][2])),
                                                      max(float(line[0][2]), float(line[1][2])))
            for line in edges}
        if not corner_edges:
            checks["corner 1 rounded"] = {"status": "failed", "reason": "No outer vertical corner edges were found to round."}
        list_ = corner_edges.items()
        centre_x = (old.bounds[0][0] + old.bounds[1][0]) / 2
        centre_y = (old.bounds[0][1] + old.bounds[1][1]) / 2
        for i, ((cx, cy), (z0, z1)) in enumerate(list_):
            z = (z0 + z1) / 2
            removed = not _inside(new, [(cx, cy, z)])[0]
            sx = 1.0 if centre_x >= cx else -1.0
            sy = 1.0 if centre_y >= cy else -1.0
            centre = np.array([cx + sx * radius, cy + sy * radius, z])
            angles = np.linspace(0.0, np.pi / 2, 5)
            arc = np.stack([centre[0] - sx * radius * np.cos(angles),
                            centre[1] - sy * radius * np.sin(angles),
                            np.full_like(angles, z)], axis=1)
            distance = _surface_distance(new, arc)
            rounded = removed and distance <= 0.1
            checks[f"corner {i + 1} rounded to {radius:g} mm"] = {
                "status": "passed" if rounded else "failed",
                "corner_material_removed": removed, "arc_surface_error_mm": round(distance, 4),
                "tolerance_mm": 0.1}
        try:
            areas = [_coverage_area(new, 0.2), _coverage_area(new, 1.0)]
            stable = abs(areas[0] - areas[1]) <= 0.5
        except Exception:
            areas, stable = [], False
        checks["preserved contact surfaces"] = {
            "status": "passed" if stable else "failed",
            "slice_area_mm2": [round(a, 3) for a in areas],
            "detail": "Bottom cross-section area stays constant with height: the flat contact faces were not consumed by the round."}
    else:
        raise ValueError("Unknown targeted edit operation")
    ok = bool(checks) and all(item["status"] == "passed" for item in checks.values())
    return {"ok": ok, "checks": checks}
