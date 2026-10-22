"""Closed radius-height loops for bounded solids of revolution.

A revolve profile is a list of [r, z] pairs forming one closed loop in the
radius-height half-plane (r >= 0). The worker revolves it 360 degrees about
the +Z axis through r=0. Validation here rejects anything the kernel cannot
turn into one valid solid: open loops, negative radius, self-crossing or
touching edges, zero-area loops and axis-only loops.
"""
from __future__ import annotations

EPS = 1e-9


def _cross(ox, oy, ax, ay, bx, by):
    return (ax - ox) * (by - oy) - (ay - oy) * (bx - ox)


def _on_segment(ax, ay, bx, by, px, py):
    return (min(ax, bx) - EPS <= px <= max(ax, bx) + EPS
            and min(ay, by) - EPS <= py <= max(ay, by) + EPS)


def _point_on(ax, ay, bx, by, px, py):
    return abs(_cross(ax, ay, bx, by, px, py)) <= EPS and _on_segment(ax, ay, bx, by, px, py)


def _segments_touch(p1, p2, p3, p4):
    """True when closed segments p1p2 and p3p4 share any point."""
    x1, y1 = p1; x2, y2 = p2; x3, y3 = p3; x4, y4 = p4
    d1 = _cross(x3, y3, x4, y4, x1, y1)
    d2 = _cross(x3, y3, x4, y4, x2, y2)
    d3 = _cross(x1, y1, x2, y2, x3, y3)
    d4 = _cross(x1, y1, x2, y2, x4, y4)
    if ((d1 > 0) != (d2 > 0)) and ((d3 > 0) != (d4 > 0)):
        return True
    if abs(d1) <= EPS and _on_segment(x3, y3, x4, y4, x1, y1):
        return True
    if abs(d2) <= EPS and _on_segment(x3, y3, x4, y4, x2, y2):
        return True
    if abs(d3) <= EPS and _on_segment(x1, y1, x2, y2, x3, y3):
        return True
    if abs(d4) <= EPS and _on_segment(x1, y1, x2, y2, x4, y4):
        return True
    return False


def resolve_revolve_profile(profile, values, scalar):
    """Resolve and validate one closed [r, z] loop. Returns resolved float pairs.

    The final pair may repeat the first pair; that closing duplicate is
    removed. All radii are >= 0. A touching axis (r = 0) is allowed, a
    crossing (r < 0) is not.
    """
    if not isinstance(profile, list) or not 3 <= len(profile) <= 129:
        raise ValueError("Profile needs 3-128 ordered [radius, height] pairs")
    points = []
    for pair in profile:
        if (not isinstance(pair, (list, tuple)) or len(pair) != 2
                or not all(isinstance(v, (int, float, str)) and not isinstance(v, bool) for v in pair)):
            raise ValueError("Each profile pair needs exactly two numeric fields")
        r, z = scalar(pair[0], values), scalar(pair[1], values)
        if r < 0:
            raise ValueError("Radius must be 0 or positive; profiles never cross the axis")
        points.append((r, z))
    if abs(points[0][0] - points[-1][0]) <= EPS and abs(points[0][1] - points[-1][1]) <= EPS:
        points.pop()  # implicit closure; the loop is closed by contract
    if len(points) < 3:
        raise ValueError("Profile needs 3 distinct vertices after closing")
    for i, p in enumerate(points):
        q = points[(i + 1) % len(points)]
        if abs(p[0] - q[0]) <= EPS and abs(p[1] - q[1]) <= EPS:
            raise ValueError(f"Vertex {i + 1}: repeated vertices are invalid")
    if max(r for r, _ in points) <= EPS:
        raise ValueError("Profile lies on the axis and has no material")
    n = len(points)
    for i in range(n):
        a1, a2 = points[i], points[(i + 1) % n]
        for j in range(i + 1, n):
            b1, b2 = points[j], points[(j + 1) % n]
            adjacent = j in (i, (i + 1) % n) or (j + 1) % n == i
            if adjacent:
                # Adjacent edges share exactly one vertex; any other shared
                # point is a spike or a collinear fold-back. Endpoints of the
                # other edge matching the shared vertex are expected and are
                # excluded here.
                shared = sum(1 for p in (a1, a2) for q in (b1, b2)
                             if abs(p[0] - q[0]) <= EPS and abs(p[1] - q[1]) <= EPS)
                if shared != 1:
                    raise ValueError(f"Vertex {i + 1}: edges touch or overlap at {j + 1}")

                def _distinct(p, q, r):  # p lies on qr strictly inside qr
                    return (_point_on(q[0], q[1], r[0], r[1], p[0], p[1])
                            and not (abs(p[0] - q[0]) <= EPS and abs(p[1] - q[1]) <= EPS)
                            and not (abs(p[0] - r[0]) <= EPS and abs(p[1] - r[1]) <= EPS))
                if _distinct(a1, b1, b2) or _distinct(b2, a1, a2):
                    raise ValueError(f"Vertex {i + 1}: edge folds back on itself at {j + 1}")
                continue
            if _segments_touch(a1, a2, b1, b2):
                raise ValueError(f"Edge {i + 1} crosses or touches edge {j + 1}")
    area = 0.0
    for i in range(n):
        x1, y1 = points[i]; x2, y2 = points[(i + 1) % n]
        area += x1 * y2 - x2 * y1
    if abs(area) <= EPS:
        raise ValueError("Profile has zero area")
    return [[r, z] for r, z in points]
