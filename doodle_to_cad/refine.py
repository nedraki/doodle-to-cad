"""Intent refinement: turn doodle wobble into the professional shape the user meant.

A hand-drawn circle is never round, a hand-placed hole row is never aligned,
five hand-sketched slots are never equal. The generator must still build the
IDEAL part (true circles, shared axes, uniform sizes) — unless the user asks
for exact fidelity to the strokes ("as_drawn").

Pure geometry over the measured evidence (view-local normalized polygons), so
refinements are deterministic, testable and explainable. Thresholds were
calibrated against known-answer probes: a true circle measures circularity
~0.906 here (approxPolyDP at 1.5% keeps it 8-gon-ish), a 5:4 rectangle ~0.77.

Each refinement carries what it snapped FROM, so the spec keeps an honest
trail from intent back to ink.
"""
from __future__ import annotations

import math
from statistics import median
from typing import Any

# Calibration constants (view-normalized units: 1.0 = full view extent).
ALIGN_TOL = 0.025      # centres this close share a row/column axis
EQUAL_SIZE_TOL = 0.12  # sizes within 12% are the same size
CIRCLE_MIN_CIRC = 0.78 # true circle measures ~0.906 on measured evidence
CIRCLE_ASPECT = (0.82, 1.22)
SLOT_ASPECT = (1.22, 3.4)
SLOT_MIN_CIRC = 0.68
# Slit/bar regime: drawn louvre slats measure paper aspect 8-10 and
# circularity ~0.2 — far outside the stadium window, so a dedicated regime
# with its own (still fit-checked) acceptance recognises them.
SLOT_BAR_ASPECT_MAX = 12.0
SLOT_BAR_MIN_CIRC = 0.15
SLOT_BAR_FIT_MIN = 0.75
RIGHT_ANGLE_TOL = 12.0 # corner of a "right" angle may drift +/- this many deg
PARALLEL_TOL = 0.14    # opposite side length disagreement for rectangles
# A primitive may only REPLACE a measured contour when it reproduces it:
# fitted-primitive/polygon IoU below this keeps the honest polygon instead.
PRIMITIVE_FIT_MIN_IOU = 0.85
RASTER_GRID = 96       # cells per side for the primitive-fit rasterisation


def _corrected(poly: list[list[float]], pixel_aspect: float) -> list[list[float]]:
    """Undo the per-axis view normalization: u scales by the view's pixel
    aspect so metrics measure the shape as drawn on paper, not squashed into
    a unit square (regression: an 11-vertex shoulder silhouette in a 1.59:1
    front view measured aspect 1.01/circularity 0.837 and became a 'circle').
    """
    if abs(pixel_aspect - 1.0) < 1e-6 or not poly:
        return poly
    return [[p[0] * pixel_aspect, p[1]] for p in poly]


def _point_in_polygon(px: float, py: float, poly: list[list[float]]) -> bool:
    inside = False
    n = len(poly)
    for i in range(n):
        x1, y1 = poly[i]
        x2, y2 = poly[(i + 1) % n]
        if (y1 > py) != (y2 > py):
            t = (py - y1) / (y2 - y1)
            if px < x1 + t * (x2 - x1):
                inside = not inside
    return inside


def _polygon_centroid_area(poly: list[list[float]]) -> tuple[tuple[float, float], float]:
    n = len(poly)
    twice_area = sum(poly[i][0] * poly[(i + 1) % n][1] - poly[(i + 1) % n][0] * poly[i][1]
                     for i in range(n))
    area = abs(twice_area) / 2
    if area < 1e-12:
        return (poly[0][0], poly[0][1]), 0.0
    cx = sum((poly[i][0] + poly[(i + 1) % n][0]) *
             (poly[i][0] * poly[(i + 1) % n][1] - poly[(i + 1) % n][0] * poly[i][1]) for i in range(n))
    cy = sum((poly[i][1] + poly[(i + 1) % n][1]) *
             (poly[i][0] * poly[(i + 1) % n][1] - poly[(i + 1) % n][0] * poly[i][1]) for i in range(n))
    return (cx / (3 * twice_area), cy / (3 * twice_area)), area


def _primitive_fit_iou(poly: list[list[float]], shape: str) -> float:
    """Rasterised IoU between the polygon and the fitted primitive of `shape`.

    The fitted primitive is derived from the polygon itself (equal-area circle
    at its centroid, its bounding box, a stadium over its bounding box), so a
    low IoU means the primitive CANNOT describe the measured contour and the
    polygon must be preserved instead of being replaced.
    """
    if shape == "polygon" or len(poly) < 3:
        return 0.0
    xs = [p[0] for p in poly]; ys = [p[1] for p in poly]
    x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
    if x1 - x0 <= 0 or y1 - y0 <= 0:
        return 0.0
    (cx, cy), area = _polygon_centroid_area(poly)
    radius = math.sqrt(area / math.pi)
    if (x1 - x0) >= (y1 - y0):
        half_short, sa, sb = (y1 - y0) / 2, (x0 + (y1 - y0) / 2, (y0 + y1) / 2), (x1 - (y1 - y0) / 2, (y0 + y1) / 2)
    else:
        half_short, sa, sb = (x1 - x0) / 2, ((x0 + x1) / 2, y0 + (x1 - x0) / 2), ((x0 + x1) / 2, y1 - (x1 - x0) / 2)
    seg_vx, seg_vy = sb[0] - sa[0], sb[1] - sa[1]
    seg_len_sq = seg_vx * seg_vx + seg_vy * seg_vy
    inter = union = 0
    step_u, step_v = (x1 - x0) / RASTER_GRID, (y1 - y0) / RASTER_GRID
    for iy in range(RASTER_GRID):
        py = y0 + (iy + 0.5) * step_v
        for ix in range(RASTER_GRID):
            px = x0 + (ix + 0.5) * step_u
            inside_poly = _point_in_polygon(px, py, poly)
            if shape == "circle":
                inside_prim = math.hypot(px - cx, py - cy) <= radius
            elif shape == "rectangle":
                inside_prim = True  # the polygon's own bounding box
            elif shape == "slot":
                if seg_len_sq <= 1e-12:
                    t = 0.0
                else:
                    t = min(max(((px - sa[0]) * seg_vx + (py - sa[1]) * seg_vy) / seg_len_sq, 0.0), 1.0)
                inside_prim = math.hypot(px - (sa[0] + seg_vx * t), py - (sa[1] + seg_vy * t)) <= half_short
            else:
                inside_prim = inside_poly
            if inside_poly or inside_prim:
                union += 1
            if inside_poly and inside_prim:
                inter += 1
    return inter / union if union else 0.0


def _poly_metrics(poly: list[list[float]]) -> tuple[float, float]:
    """Shoelace area and perimeter of the normalized polygon."""
    n = len(poly)
    if n < 3:
        return 0.0, 0.0
    area = abs(sum(poly[i][0] * poly[(i + 1) % n][1] - poly[(i + 1) % n][0] * poly[i][1]
                   for i in range(n))) / 2
    perim = sum(math.dist(poly[i], poly[(i + 1) % n]) for i in range(n))
    return area, perim


def _circularity(poly: list[list[float]]) -> float:
    area, perim = _poly_metrics(poly)
    if perim <= 0:
        return 0.0
    return 4 * math.pi * area / (perim * perim)


def _corners(poly: list[list[float]]) -> list[float]:
    """Interior angles (deg) at each vertex."""
    n = len(poly)
    angles: list[float] = []
    for i in range(n):
        ax, ay = poly[(i - 1) % n]
        bx, by = poly[i]
        cx, cy = poly[(i + 1) % n]
        a = math.atan2(ay - by, ax - bx)
        b = math.atan2(cy - by, cx - bx)
        diff = abs(math.degrees(a - b)) % 360
        angles.append(360 - diff if diff > 180 else diff)
    return angles


def _is_rectangle(poly: list[list[float]]) -> bool:
    if not (4 <= len(poly) <= 8):
        return False
    angles = _corners(poly)
    if not all(90 - RIGHT_ANGLE_TOL <= a <= 90 + RIGHT_ANGLE_TOL for a in angles[:4]):
        return False
    n = len(poly) if len(poly) == 4 else 4
    sides = [math.dist(poly[i], poly[(i + 1) % n]) for i in range(n)]
    if n == 4 and (abs(sides[0] - sides[2]) > PARALLEL_TOL * max(sides[0], sides[2], 1e-9)
                   or abs(sides[1] - sides[3]) > PARALLEL_TOL * max(sides[1], sides[3], 1e-9)):
        return False
    return True


def classify_profile(profile: dict[str, Any], pixel_aspect: float = 1.0,
                     *, min_fit: float | None = None) -> tuple[str, float]:
    """(ideal_shape, confidence) for one closed profile polygon.

    `pixel_aspect` is the enclosing view's width/height pixel ratio: metrics
    are measured after un-squashing the polygon so a shape only becomes a
    primitive when it looks like that primitive ON PAPER. Every primitive
    candidate must additionally pass a fitted-primitive IoU check — a complex
    perimeter is never replaced by a primitive that does not reproduce it.
    `min_fit` raises that floor for every shape (the outer silhouette keeps
    the strict PRIMITIVE_FIT_MIN_IOU so e.g. a shouldered grille outline can
    never smuggle in as a slot at the looser slit/bar threshold).
    """
    poly = profile.get("polygon_view_normalized") or []
    bbox = profile.get("bbox_view_normalized") or [0, 0, 0, 0]
    w, h = bbox[2], bbox[3]
    if w <= 0 or h <= 0 or len(poly) < 3:
        return "polygon", 0.0
    aspect = w * pixel_aspect / h
    cand = _corrected(poly, pixel_aspect)
    circ = _circularity(cand)
    # `min_fit` may only RAISE thresholds (outer silhouettes pass 0.85 to keep
    # the bar regime strict); each regime's own default is the lower bound.
    norm_floor = max(min_fit, PRIMITIVE_FIT_MIN_IOU) if min_fit is not None else PRIMITIVE_FIT_MIN_IOU
    bar_floor = max(min_fit, SLOT_BAR_FIT_MIN) if min_fit is not None else SLOT_BAR_FIT_MIN
    # Rectangle first: a true-circle polygon never passes _is_rectangle
    # (octagon corners measure ~135 deg), while a square's circularity
    # (0.785) sits just inside the circle window and must not snap to one.
    if _is_rectangle(_corrected(poly, pixel_aspect)) and _primitive_fit_iou(cand, "rectangle") >= norm_floor:
        return "rectangle", 0.9
    if CIRCLE_MIN_CIRC <= circ and CIRCLE_ASPECT[0] <= aspect <= CIRCLE_ASPECT[1]:
        fit = _primitive_fit_iou(cand, "circle")
        if fit >= norm_floor:
            return "circle", min(1.0, (circ - CIRCLE_MIN_CIRC) / 0.15 + 0.5)
    long_ratio = max(aspect, 1 / aspect)
    if SLOT_MIN_CIRC <= circ and SLOT_ASPECT[0] <= long_ratio <= SLOT_ASPECT[1]:
        if _primitive_fit_iou(cand, "slot") >= norm_floor:
            return "slot", 0.7
    if SLOT_BAR_MIN_CIRC <= circ < SLOT_MIN_CIRC and SLOT_ASPECT[1] < long_ratio <= SLOT_BAR_ASPECT_MAX:
        # Thin drawn slit/bar: the stadium fit check alone decides.
        if _primitive_fit_iou(cand, "slot") >= bar_floor:
            return "slot", 0.65
    return "polygon", 0.3


def _cluster(values: list[float], tol: float) -> list[list[int]]:
    """Indices of `values` grouped when they agree within tol."""
    order = sorted(range(len(values)), key=lambda i: values[i])
    groups: list[list[int]] = []
    for i in order:
        if groups and abs(values[i] - values[groups[-1][-1]]) <= tol:
            groups[-1].append(i)
        else:
            groups.append([i])
    return groups


def _axis_groups(items: list[dict[str, Any]], axis: int) -> list[list[int]]:
    # Hand wobble scales with feature size, but the tolerance must be
    # PAIRWISE: a grille with 0.61-tall slots over 0.13 headlights makes the
    # global 0.35*median tol (0.213) swallow the real 0.188 gap between the
    # slot row and the headlight row, snapping headlights onto the wrong axis.
    # Two items share a row only when their gap is small compared to BOTH of
    # their sizes; distinct rows stay separated.
    vals = [e["center_view_normalized"][axis] for e in items]
    sizes = [e["size_view_normalized"][axis] for e in items]
    order = sorted(range(len(vals)), key=lambda i: vals[i])
    groups: list[list[int]] = []
    for i in order:
        if groups:
            last = groups[-1][-1]
            tol = max(ALIGN_TOL, 0.35 * min(sizes[i], sizes[last]))
            if vals[i] - vals[last] <= tol:
                groups[-1].append(i)
                continue
        groups.append([i])
    return groups


def refine_view(view: dict[str, Any]) -> dict[str, Any]:
    """Idealized shape/center/size per profile for one view's measured geometry."""
    pixel_aspect = float(view.get("pixel_aspect_ratio_width_over_height") or 1.0)
    profiles = view.get("internal_profiles") or []
    refined: list[dict[str, Any]] = []
    for profile in profiles:
        shape, confidence = classify_profile(profile, pixel_aspect)
        bbox = profile.get("bbox_view_normalized") or [0, 0, 0, 0]
        center = list(profile.get("center_view_normalized") or [0.5, 0.5])
        size = [bbox[2], bbox[3]]
        entry: dict[str, Any] = {
            "profile_id": profile.get("profile_id"),
            "ideal_shape": shape,
            "confidence": round(confidence, 2),
            "center_view_normalized": [round(c, 4) for c in center],
            "size_view_normalized": [round(s, 4) for s in size],
            "snapped": {},
        }
        refined.append(entry)

    # Equal-size snap: same ideal shape and near size -> one canonical size.
    for shape in {e["ideal_shape"] for e in refined}:
        same = [e for e in refined if e["ideal_shape"] == shape]
        if len(same) < 2:
            continue
        for axis in (0, 1):
            vals = [e["size_view_normalized"][axis] for e in same]
            # Near-equal cluster -> unify to the median ("they meant one size").
            for group in _cluster(vals, EQUAL_SIZE_TOL * max(max(vals), 1e-9)):
                if len(group) < 2:
                    continue
                canon = round(median(vals[i] for i in group), 4)
                if canon <= 0:
                    continue
                for idx in group:
                    current = refined[idx]["size_view_normalized"][axis]
                    if current != canon:
                        refined[idx]["snapped"][f"size_{'u' if axis == 0 else 'v'}"] = {
                            "from": current, "to": canon}
                        refined[idx]["size_view_normalized"][axis] = canon

    # Row/column alignment snap on centres. Tolerance is pairwise size-relative
    # (see _axis_groups) so genuine hand-wobble inside one row collapses onto the
    # shared axis while distinct feature rows stay separated.
    us = [e["center_view_normalized"][0] for e in refined]
    vs = [e["center_view_normalized"][1] for e in refined]
    for group in _axis_groups(refined, 1):    # rows share one v
        if len(group) >= 2:
            canon = round(median(vs[i] for i in group), 4)
            for idx in group:
                if refined[idx]["center_view_normalized"][1] != canon:
                    refined[idx]["snapped"]["center_v"] = {"from": refined[idx]["center_view_normalized"][1], "to": canon}
                    refined[idx]["center_view_normalized"][1] = canon
    for group in _axis_groups(refined, 0):    # columns share one u
        if len(group) >= 2:
            canon = round(median(us[i] for i in group), 4)
            for idx in group:
                if refined[idx]["center_view_normalized"][0] != canon:
                    refined[idx]["snapped"]["center_u"] = {"from": refined[idx]["center_view_normalized"][0], "to": canon}
                    refined[idx]["center_view_normalized"][0] = canon

    # Regular-grid report: rows x cols of matching pitch -> tell the generator.
    grid = _grid_report(refined)
    outer_shape, outer_fit = None, None
    outer = view.get("outer_profile")
    if outer and (outer.get("polygon_dense_view_normalized") or outer.get("polygon_view_normalized") or []):
        # The outer silhouette is the body's extrusion profile. Classify it in
        # paper aspect, on the high-fidelity polygon, and record the primitive
        # fit so the generator may only replace it when the fit is honest.
        dense = outer.get("polygon_dense_view_normalized") or outer["polygon_view_normalized"]
        outer_profile = dict(outer)
        outer_profile["polygon_view_normalized"] = dense
        cand_shape, conf = classify_profile(outer_profile, pixel_aspect,
                                            min_fit=PRIMITIVE_FIT_MIN_IOU)
        cand = _corrected(dense, pixel_aspect)
        fit_iou = _primitive_fit_iou(cand, cand_shape) if cand_shape != "polygon" else None
        outer_fit = {"candidate": cand_shape, "iou": (round(fit_iou, 3) if fit_iou is not None else None),
                     "accepted": cand_shape != "polygon" and conf >= 0.5}
        outer_shape = cand_shape if outer_fit["accepted"] else "polygon"
    result: dict[str, Any] = {"view_id": view.get("view_id"), "profiles": refined}
    if outer_shape:
        result["outer_profile_ideal"] = outer_shape
        result["outer_profile_preservation"] = (
            "The outer silhouette is an extrusion profile the model must keep. "
            "Model it from outer_profile (polygon_dense_view_normalized / "
            "curve_segments); only build the ideal shape when "
            "outer_profile_fit.accepted is true."
            if outer_shape == "polygon" else
            "The outer silhouette matches its ideal shape within the fit check; build that primitive.")
        if outer_fit:
            result["outer_profile_fit"] = outer_fit
    if grid:
        result["grid"] = grid
    return result


def _grid_report(refined: list[dict[str, Any]]) -> dict[str, Any] | None:
    circles = [e for e in refined if e["ideal_shape"] == "circle"]
    # Slots/rectangles form rows too (vent slits, nameplate slots): include them.
    rowables = [e for e in refined if e["ideal_shape"] in ("circle", "rectangle", "slot")]
    pool = circles if len(circles) >= 3 else rowables
    if len(pool) < 3:
        return None
    rows = _axis_groups(pool, 1)
    cols = _axis_groups(pool, 0)
    # Single dominant row (or column) of >=3 equal items: the most common
    # doodle pattern of all — report it so the generator loops over the pitch
    # instead of hand-placing each item (hand-placed rows lose end items).
    # ANY aligned line of >=3 evenly spaced items earns the loop hint —
    # not just views that contain a single row (a grille has a 7-slot row
    # PLUS a 2-item headlight row; requiring rows==1 silenced the hint there
    # and the generator built 7 slots but lost both headlights).
    best_hint = None
    for line, axis, pitch_idx in ((rows, "v", 0), (cols, "u", 1)):
        for group in sorted(line, key=len, reverse=True):
            if len(group) < 3 or best_hint:
                continue
            coords = sorted(pool[c]["center_view_normalized"][pitch_idx] for c in group)
            pitches = [b - a for a, b in zip(coords, coords[1:])]
            med = median(pitches)
            if med > 0 and all(abs(p - med) < 0.18 * med for p in pitches):
                sizes = [pool[c]["size_view_normalized"][pitch_idx] for c in group]
                best_hint = {"type": f"linear_{axis}-row", "count": len(group),
                             "profile_ids": [pool[c]["profile_id"] for c in group],
                             "pitch_mm_of_view": round(med, 4),
                             "item_size_mm_of_view": round(median(sizes), 4),
                             "note": (f"Exactly {len(group)} equal items share one aligned {axis}-row "
                                      f"(listed profile_ids) — build ONE item in a for-loop over the "
                                      f"pitch and render {len(group)} copies; never drop edge items or "
                                      f"substitute a smaller count.")}
    if best_hint:
        return best_hint
    counts = {len(r) for r in rows}
    if len(rows) >= 2 and counts == {len(cols)} and len(cols) >= 2:
        row_vs = sorted(median([pool[c]["center_view_normalized"][1] for c in r]) for r in rows)
        col_us = sorted(median([pool[c]["center_view_normalized"][0] for c in col]) for col in cols)
        pitches_v = [b - a for a, b in zip(row_vs, row_vs[1:])]
        pitches_u = [b - a for a, b in zip(col_us, col_us[1:])]
        regular = (all(abs(p - median(pitches_u)) < 0.15 * median(pitches_u) for p in pitches_u)
                   and all(abs(p - median(pitches_v)) < 0.15 * median(pitches_v) for p in pitches_v))
        if regular:
            return {"type": "rectangular_grid", "rows": len(rows), "cols": len(cols),
                    "pitch_u_mm_of_view": round(median(pitches_u), 4),
                    "pitch_v_mm_of_view": round(median(pitches_v), 4),
                    "note": "Evenly spaced aligned grid — build with loops over pitch, not per-hole coordinates."}
    return None


def refine_evidence(evidence: dict[str, Any], mode: str = "regularize") -> dict[str, Any] | None:
    """Build the intent_refinements block for generation input (None when off)."""
    if mode != "regularize":
        return None
    views = evidence.get("view_geometry") or []
    if not views:
        return None
    return {
        "refine_mode": "regularize",
        "contract": ("The source strokes are hand-drawn and imperfect. ideal_shape, "
                     "snapped centres and sizes are the USER'S DESIGN INTENT: model these "
                     "ideal forms (true circle(), square/rectangle, aligned rows, uniform "
                     "sizes, grid loops) — never trace the raw wobbly polygon. "
                     "This applies to internal profiles only: the outer silhouette of a "
                     "view is an extrusion profile and must be kept unless its "
                     "outer_profile_fit.accepted is true."),
        "views": [refine_view(view) for view in views],
    }
