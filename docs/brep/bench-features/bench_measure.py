"""Independent mesh measurements for the special-features benchmark.

Self-contained: numpy + trimesh only, no rtree/shapely (this environment has
none). Every primitive works from exported STL vertices/faces alone, so the
checks never trust the kernel's word. Audit re-runs these functions over the
saved artifacts.
"""
from __future__ import annotations

import math

import numpy as np
import trimesh

RAY_DIRECTION = np.array([0.011, 0.017, 1.0])


def load(path):
    mesh = trimesh.load(path, force="mesh")
    if not mesh.is_watertight or not mesh.is_winding_consistent or mesh.volume <= 0:
        raise ValueError(f"Mesh failed independent validation before measuring: {path}")
    return mesh


def inside(mesh, points):
    """Point-in-solid by upward-ray crossing parity (vectorised Moller-Trumbore)."""
    tri = np.asarray(mesh.triangles, dtype=float)
    e1 = tri[:, 1] - tri[:, 0]
    e2 = tri[:, 2] - tri[:, 0]
    d = RAY_DIRECTION / np.linalg.norm(RAY_DIRECTION)
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
        ok = valid & (u >= -1e-9) & (v >= -1e-9) & (u + v <= 1 + 1e-9) & (t > 1e-9)
        hits[start:start + len(batch)] = ok.sum(1)
    return [int(count) % 2 == 1 for count in hits]


def march_transitions(mesh, start, direction, t_lo, t_hi, step=0.02, refine=0.002):
    """Boundary positions along a ray, refined to +-refine/2 by bisection probes.

    Returns sorted transition t values (inside<->outside). Probes must not graze
    geometry: benchmark fixtures are axis-aligned away from probe lines.
    """
    start = np.asarray(start, float)
    direction = np.asarray(direction, float)
    direction = direction / np.linalg.norm(direction)
    ts = np.arange(t_lo, t_hi + step / 2, step)
    states = np.asarray(inside(mesh, start + ts[:, None] * direction))
    flips = np.flatnonzero(states[1:] != states[:-1]) + 1
    boundaries = []
    for i in flips:
        lo, hi = float(ts[i - 1]), float(ts[i])
        probes = np.arange(lo, hi + refine / 2, refine)
        flags = np.asarray(inside(mesh, start + probes[:, None] * direction))
        change = np.flatnonzero(flags != flags[0])
        boundaries.append(float(probes[change[0]] - refine / 2) if len(change) else (lo + hi) / 2)
    return boundaries


def footprint_area(mesh, z, spacing=0.25):
    """Solid area of a horizontal slice by grid sampling with ray parity."""
    (x0, y0), (x1, y1) = mesh.bounds[0][:2], mesh.bounds[1][:2]
    xs = np.arange(x0 + spacing / 2, x1, spacing)
    ys = np.arange(y0 + spacing / 2, y1, spacing)
    grid = [(float(x), float(y), float(z)) for x in xs for y in ys]
    return sum(inside(mesh, grid)) * spacing * spacing


def radial_boundary(mesh, origin_xy, z, angle_rad, r_max, step=0.05, refine=0.002):
    """First solid->empty exit distance from a known-interior point at one angle."""
    ox, oy = origin_xy
    direction = np.array([math.cos(angle_rad), math.sin(angle_rad), 0.0])
    start = np.array([ox, oy, z])
    ts = np.arange(0.0, r_max + step / 2, step)
    states = np.asarray(inside(mesh, start + ts[:, None] * direction))
    if not states[0]:
        raise ValueError(f"probe origin not inside at angle {math.degrees(angle_rad):.1f}")
    flips = np.flatnonzero(~states[1:] & states[:-1]) + 1
    if len(flips) == 0:
        raise ValueError("no exit found within r_max")
    i = int(flips[0])
    lo, hi = float(ts[i - 1]), float(ts[i])
    probes = np.arange(lo, hi + refine / 2, refine)
    flags = np.asarray(inside(mesh, start + probes[:, None] * direction))
    change = np.flatnonzero(~flags)
    return float(probes[change[0]]) if len(change) else (lo + hi) / 2


def radial_polygon_area(mesh, origin_xy, z, r_max, n=720, step=0.05):
    """Cross-section area from a radial boundary polygon (shoelace)."""
    angles = np.linspace(0, 2 * math.pi, n, endpoint=False)
    radii = [radial_boundary(mesh, origin_xy, z, float(a), r_max, step=step) for a in angles]
    radii = np.asarray(radii)
    x = radii * np.cos(angles)
    y = radii * np.sin(angles)
    area = 0.5 * abs(np.dot(x, np.roll(y, -1)) - np.dot(y, np.roll(x, -1)))
    return float(area), radii


def circle_fit(points):
    """Kasa least-squares circle fit: returns (cx, cy, r, rms_residual)."""
    p = np.asarray(points, dtype=float)
    x, y = p[:, 0], p[:, 1]
    a = np.stack([x, y, np.ones(len(x))], axis=1)
    b = x * x + y * y
    (cx, cy, c), *_ = np.linalg.lstsq(a, b, rcond=None)
    cx, cy = cx / 2, cy / 2
    r = math.sqrt(c + cx * cx + cy * cy)
    residual = np.abs(np.linalg.norm(p - np.array([cx, cy]), axis=1) - r)
    return float(cx), float(cy), float(r), float(np.sqrt((residual ** 2).mean()))


# --------------------------------------------------------------------------
# Feature checkers. Each returns {"ok": bool, "checks": {name: {...}}}.


def _check(name, ok, **fields):
    entry = {"status": "passed" if ok else "failed"}
    entry.update(fields)
    return name, entry


def verify_fillet(stl, width, depth, height, radius, *, slice_z=None, tol=0.1):
    """Outer vertical corner arcs measured by per-corner circle fit on a slice."""
    mesh = load(stl)
    slice_z = height / 2 if slice_z is None else slice_z
    checks = {}
    lo, hi = mesh.bounds
    centre = np.array([(lo[0] + hi[0]) / 2, (lo[1] + hi[1]) / 2])
    for i, (cx, cy) in enumerate([(lo[0], lo[1]), (hi[0], lo[1]), (lo[0], hi[1]), (hi[0], hi[1])], start=1):
        sx = 1.0 if centre[0] > cx else -1.0
        sy = 1.0 if centre[1] > cy else -1.0
        expected_center = np.array([cx + sx * radius, cy + sy * radius])
        origin3 = np.array([expected_center[0], expected_center[1], slice_z])
        points = []
        # The filleted quarter arc spans +-45 degrees around the direction
        # from the arc centre to the original corner; probes stay strictly
        # inside that window so a ray never grazes the tangent point between
        # arc and wall (grazing flips the crossing parity spuriously).
        for deg in np.linspace(-44.0, 44.0, 25):
            base = math.atan2(-sy, -sx)  # direction from arc centre to the corner
            angle = base + math.radians(deg)
            direction = np.array([math.cos(angle), math.sin(angle), 0.0])
            ts = np.arange(radius - 1.0, radius + 1.0, 0.01)
            states = np.asarray(inside(mesh, origin3[None, :] + direction[None, :] * ts[:, None]))
            # A real boundary flip persists for the rest of the probe; a
            # one- or two-sample flip is a tessellation graze and is ignored.
            flips = [j for j in range(1, len(ts))
                     if states[j] != states[j - 1]
                     and bool(np.all(states[j:] == states[j]))]
            if flips:
                t = float(ts[flips[0]])
                points.append(expected_center + direction[:2] * t)
        if len(points) < 12:
            checks[f"corner {i}"] = {"status": "failed", "reason": f"only {len(points)} arc points found"}
            continue
        cx_f, cy_f, r_fit, rms = circle_fit(points)
        ok = abs(r_fit - radius) <= tol and math.dist((cx_f, cy_f), expected_center) <= tol
        name = f"corner {i} arc radius"
        checks[name] = {"status": "passed" if ok else "failed",
                        "measured_radius_mm": round(r_fit, 4), "expected_radius_mm": radius,
                        "tolerance_mm": tol, "centre_error_mm": round(math.dist((cx_f, cy_f), expected_center), 4),
                        "fit_rms_mm": round(rms, 4), "arc_points": len(points)}
    removed = inside(mesh, [(hi[0] - 0.02, hi[1] - 0.02, slice_z), (lo[0] + 0.02, lo[1] + 0.02, slice_z)])
    name, entry = _check("corner material removed", not any(removed), probed=removed)
    checks[name] = entry
    core = inside(mesh, [(*centre, slice_z)])
    name, entry = _check("body core intact", all(core))
    checks[name] = entry
    return {"ok": all(c["status"] == "passed" for c in checks.values()), "checks": checks}


def verify_chamfer(stl, width, depth, height, radius, *, slope_tol=0.06, leg_tol=0.05, area_rel_tol=0.01):
    """Chamfer measurement for the usd_brep `chamfer` operation.

    Measured kernel semantics (calibrated on the exported mesh, not assumed):
    the operation bevels the horizontal (top and bottom) edges only, at 45
    degrees, and the `radius` argument is the hypotenuse of the chamfer
    triangle: the horizontal leg equals radius / sqrt(2). Vertical edges are
    left untouched. The checker fits width-vs-height inside the taper band and
    asserts the slope (45 degrees) and the fitted leg, so a build with a
    different radius fails on the fitted leg.
    """
    mesh = load(stl)
    lo, hi = mesh.bounds
    checks = {}
    leg = radius / math.sqrt(2.0)
    for side, z_at in (("top", lambda zb: hi[2] - zb), ("bottom", lambda zb: lo[2] + zb)):
        samples = []
        for frac in (0.05, 0.35, 0.70, 0.94):
            zb = leg * frac
            z = z_at(zb)
            xb = march_transitions(mesh, (lo[0] - 2, (lo[1] + hi[1]) / 2, z), (1, 0, 0), 0.0, width + 4)
            yb = march_transitions(mesh, ((lo[0] + hi[0]) / 2, lo[1] - 2, z), (0, 1, 0), 0.0, depth + 4)
            w = xb[-1] - xb[0] if len(xb) == 2 else None
            d = yb[-1] - yb[0] if len(yb) == 2 else None
            samples.append((zb, w, d))
        ok_samples = all(w is not None and d is not None for _, w, d in samples)
        if not ok_samples:
            checks[f"{side} taper sampled"] = {"status": "failed", "samples": samples}
            continue
        zs = np.array([s[0] for s in samples])
        ws = np.array([s[1] for s in samples])
        ds = np.array([s[2] for s in samples])
        bx, ax = np.polyfit(zs, ws, 1)
        by, ay = np.polyfit(zs, ds, 1)
        fit_leg_x = (width - ax) / bx
        fit_leg_y = (depth - ay) / by
        checks[f"{side} taper is 45 degrees"] = {
            "status": "passed" if abs(bx - 2.0) <= slope_tol and abs(by - 2.0) <= slope_tol else "failed",
            "measured_slope_x": round(float(bx), 4), "measured_slope_y": round(float(by), 4),
            "expected_slope": 2.0, "tolerance": slope_tol}
        checks[f"{side} fitted leg equals radius/sqrt(2)"] = {
            "status": "passed" if abs(fit_leg_x - leg) <= leg_tol and abs(fit_leg_y - leg) <= leg_tol else "failed",
            "measured_leg_x_mm": round(float(fit_leg_x), 4), "measured_leg_y_mm": round(float(fit_leg_y), 4),
            "expected_leg_mm": round(leg, 4), "tolerance_mm": leg_tol,
            "radius_argument_mm": radius, "samples": [(round(z, 3), round(w, 3), round(d, 3)) for z, w, d in samples]}
    # Vertical edges untouched: mid-height footprint is the full rectangle.
    area = footprint_area(mesh, (lo[2] + hi[2]) / 2, spacing=0.25)
    expected_area = width * depth
    ok = abs(area - expected_area) <= area_rel_tol * expected_area
    checks["mid footprint keeps vertical edges (full rectangle)"] = {
        "status": "passed" if ok else "failed", "measured_area_mm2": round(area, 3),
        "expected_area_mm2": expected_area, "tolerance_mm2": round(area_rel_tol * expected_area, 3)}
    return {"ok": all(c["status"] == "passed" for c in checks.values()), "checks": checks}


def verify_arc_pipe(stl, bend_radius, tube_radius, angle_deg, theta_mid_deg, *,
                    centreline_tol=0.1, tube_tol=0.1, volume_rel_tol=0.02):
    """Centreline radius and tube radius by radial slice probes."""
    mesh = load(stl)
    checks = {}
    theta = math.radians(theta_mid_deg)
    for dz in (0.0, 0.5 * tube_radius, -0.5 * tube_radius, 0.8 * tube_radius):
        z = tube_radius + dz
        half = tube_radius * math.sqrt(max(0.0, 1 - (dz / tube_radius) ** 2))
        expected_inner, expected_outer = bend_radius - half, bend_radius + half
        xb = march_transitions(mesh, (0.0, 0.0, z), (math.cos(theta), math.sin(theta), 0.0),
                               bend_radius - tube_radius - 2.0, bend_radius + tube_radius + 2.0)
        ok = len(xb) == 2
        inner, outer = (round(xb[0], 4), round(xb[1], 4)) if ok else (None, None)
        centre_meas = round((xb[0] + xb[1]) / 2, 4) if ok else None
        half_meas = round((xb[1] - xb[0]) / 2, 4) if ok else None
        ok_c = ok and abs(centre_meas - bend_radius) <= centreline_tol
        ok_w = ok and abs(half_meas - half) <= tube_tol
        checks[f"radial slice at dz {round(dz, 3)} mm"] = {
            "status": "passed" if (ok_c and ok_w) else "failed",
            "measured_centreline_mm": centre_meas, "expected_centreline_mm": bend_radius,
            "measured_half_width_mm": half_meas, "expected_half_width_mm": round(half, 4),
            "measured_inner_mm": inner, "expected_inner_mm": round(expected_inner, 4),
            "measured_outer_mm": outer, "expected_outer_mm": round(expected_outer, 4),
            "tolerance_mm": max(centreline_tol, tube_tol)}
    # Circular profile: w^2 + dz^2 == r^2 across the probed offsets.
    offsets = []
    for dz in np.linspace(-0.9 * tube_radius, 0.9 * tube_radius, 7):
        z = tube_radius + float(dz)
        xb = march_transitions(mesh, (0.0, 0.0, z), (math.cos(theta), math.sin(theta), 0.0),
                               bend_radius - tube_radius - 2.0, bend_radius + tube_radius + 2.0)
        if len(xb) == 2:
            offsets.append(((xb[1] - xb[0]) / 2, float(dz)))
    r_fits = [math.sqrt(w * w + dz * dz) for w, dz in offsets]
    r_fit = float(np.mean(r_fits)) if r_fits else None
    spread = float(np.max(r_fits) - np.min(r_fits)) if r_fits else 9e9
    ok = r_fit is not None and abs(r_fit - tube_radius) <= tube_tol and spread <= 0.08
    checks["tube radius from slice circles"] = {
        "status": "passed" if ok else "failed", "measured_tube_radius_mm": None if r_fit is None else round(r_fit, 4),
        "expected_tube_radius_mm": tube_radius, "spread_mm": round(spread, 4), "probes": len(offsets),
        "tolerance_mm": tube_tol}
    expected_volume = math.radians(angle_deg) * bend_radius * math.pi * tube_radius ** 2
    rel = abs(mesh.volume - expected_volume) / expected_volume
    ok = rel <= volume_rel_tol
    checks["volume (Pappus)"] = {
        "status": "passed" if ok else "failed", "measured_volume_mm3": round(mesh.volume, 2),
        "expected_volume_mm3": round(expected_volume, 2), "relative_tolerance": volume_rel_tol,
        "relative_error": round(rel, 5)}
    return {"ok": all(c["status"] == "passed" for c in checks.values()), "checks": checks}


def _expected_loft_polygon(w, d, r, t, samples_per_segment=180):
    """Boundary points of the degree-1 skin section at t (rect corners -> circle diagonals)."""
    # Build order in workers/brep/build.py: rect NE->NW->SW->SE->NE matched with
    # arcs 45->135, 135->225, 225->315, 315->45 (CCW), segmentwise linear skin.
    hw, hd = w / 2, d / 2
    corners = [(hw, hd), (-hw, hd), (-hw, -hd), (hw, -hd)]
    pts = []
    for i in range(4):
        a, b = corners[i], corners[(i + 1) % 4]
        ang0, ang1 = [45, 135, 225, 315][i], [135, 225, 315, 405][i]
        for k in range(samples_per_segment):
            s = k / samples_per_segment
            rp = (a[0] + (b[0] - a[0]) * s, a[1] + (b[1] - a[1]) * s)
            ang = math.radians(ang0 + (ang1 - ang0) * s)
            cp = (r * math.cos(ang), r * math.sin(ang))
            pts.append(((1 - t) * rp[0] + t * cp[0], (1 - t) * rp[1] + t * cp[1]))
    pts = np.asarray(pts)
    area = 0.5 * abs(np.dot(pts[:, 0], np.roll(pts[:, 1], -1)) - np.dot(pts[:, 1], np.roll(pts[:, 0], -1)))
    return pts, float(area)


def verify_loft(stl, rect_width, rect_depth, circle_radius, height, *,
                end_tol=0.15, section_tol=0.03, section_abs=4.0):
    """End profiles exactly, intermediate sections against the skin interpolation model."""
    mesh = load(stl)
    checks = {}
    # Bottom rectangle: boundary distance along face normals and diagonals.
    zb = 0.05
    for deg, expected in ((0.0, rect_width / 2), (90.0, rect_depth / 2), (180.0, rect_width / 2),
                          (270.0, rect_depth / 2),
                          (45.0, math.hypot(rect_width / 2, rect_depth / 2))):
        # diagonal direction hits the corner only for matching aspect; compare along that
        # direction to the interpolated rectangle corner distance.
        got = radial_boundary(mesh, (0.0, 0.0), zb, math.radians(deg), rect_width)
        ok = abs(got - expected) <= end_tol
        checks[f"bottom profile at {deg:g} deg"] = {
            "status": "passed" if ok else "failed", "measured_mm": round(got, 4),
            "expected_mm": round(expected, 4), "tolerance_mm": end_tol}
    zt = height - 0.05
    radii = [radial_boundary(mesh, (0.0, 0.0), zt, math.radians(a), circle_radius + 5)
             for a in range(0, 360, 15)]
    worst = max(abs(x - circle_radius) for x in radii)
    checks["top circle profile"] = {
        "status": "passed" if worst <= end_tol else "failed",
        "measured_radius_mm": round(float(np.mean(radii)), 4), "expected_radius_mm": circle_radius,
        "max_deviation_mm": round(worst, 4), "tolerance_mm": end_tol}
    # Intermediate sections at three heights vs the interpolation model.
    for t in (0.25, 0.5, 0.75):
        z = t * height
        expected_pts, expected_area = _expected_loft_polygon(rect_width, rect_depth, circle_radius, t)
        r_max = max(rect_width, rect_depth, 2 * circle_radius)
        area, radii_mid = radial_polygon_area(mesh, (0.0, 0.0), z, r_max, n=360)
        rel = abs(area - expected_area) / expected_area
        ok = rel <= section_tol or abs(area - expected_area) <= section_abs
        checks[f"section area at t={t}"] = {
            "status": "passed" if ok else "failed", "measured_area_mm2": round(area, 3),
            "expected_area_mm2": round(expected_area, 3), "relative_error": round(rel, 5),
            "tolerance_relative": section_tol, "tolerance_absolute_mm2": section_abs}
        # Corner correspondence: NE diagonal boundary must follow corner -> diagonal.
        got = radial_boundary(mesh, (0.0, 0.0), z, math.pi / 4, r_max)
        corner = np.array([rect_width / 2, rect_depth / 2])
        diag = np.array([circle_radius / math.sqrt(2)] * 2)
        p = (1 - t) * corner + t * diag
        expected_dist = math.hypot(*p)
        ok_c = abs(got - expected_dist) <= 0.25
        checks[f"NE corner interpolation at t={t}"] = {
            "status": "passed" if ok_c else "failed", "measured_boundary_mm": round(got, 4),
            "expected_boundary_mm": round(expected_dist, 4), "tolerance_mm": 0.25}
    return {"ok": all(c["status"] == "passed" for c in checks.values()), "checks": checks}


def verify_shell(stl, width, depth, height, thickness, *, tol=0.1, area_tol=2.0):
    """Wall thickness from slice areas plus direct wall/floor probes."""
    mesh = load(stl)
    checks = {}
    z = height / 2
    area = footprint_area(mesh, z, spacing=0.25)
    # A = 2t(W+D) - 4t^2  ->  t = ((W+D) - sqrt((W+D)^2 - 4A)) / 4
    s = width + depth
    disc = s * s - 4 * area
    t_measured = (s - math.sqrt(disc)) / 4 if disc >= 0 else None
    expected_area = 2 * thickness * s - 4 * thickness ** 2
    checks["slice wall area"] = {
        "status": "passed" if t_measured is not None and abs(area - expected_area) <= area_tol else "failed",
        "measured_area_mm2": round(area, 3), "expected_area_mm2": round(expected_area, 3),
        "tolerance_mm2": area_tol, "thickness_from_area_mm": None if t_measured is None else round(t_measured, 4),
        "expected_thickness_mm": thickness}
    probes_spec = {
        "x walls": ((-2.0, depth / 2, z), (1, 0, 0), width + 4, [thickness, thickness]),
        "y walls": ((width / 2, -2.0, z), (0, 1, 0), depth + 4, [thickness, thickness]),
        "floor": ((width / 2, depth / 2, -2.0), (0, 0, 1), height + 4, [thickness]),
    }
    for name, (start, direction, span, expected) in probes_spec.items():
        bounds = march_transitions(mesh, start, direction, 0.0, span)
        need = 2 * len(expected)
        got = [round(bounds[2 * k + 1] - bounds[2 * k], 4) for k in range(len(expected))] \
            if len(bounds) == need else None
        ok = got is not None and all(abs(g - e) <= tol for g, e in zip(got, expected))
        checks[name + " thickness by probes"] = {
            "status": "passed" if ok else "failed", "measured_mm": got,
            "expected_mm": expected, "tolerance_mm": tol}
    cavity_top = inside(mesh, [(width / 2, depth / 2, height - 1.0)])[0]
    wall_top = inside(mesh, [(thickness / 2, depth / 2, height - 1.0)])[0]
    cavity_mid = inside(mesh, [(width / 2, depth / 2, z)])[0]
    ok = (not cavity_top) and wall_top and cavity_mid
    checks["open top, hollow interior, walls reach top"] = {
        "status": "passed" if ok else "failed",
        "cavity_open_at_top": not cavity_top, "wall_solid_at_top": wall_top, "cavity_hollow_at_mid": cavity_mid}
    return {"ok": all(c["status"] == "passed" for c in checks.values()), "checks": checks}
