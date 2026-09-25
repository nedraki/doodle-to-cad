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
RIGHT_ANGLE_TOL = 12.0 # corner of a "right" angle may drift +/- this many deg
PARALLEL_TOL = 0.14    # opposite side length disagreement for rectangles


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


def classify_profile(profile: dict[str, Any]) -> tuple[str, float]:
    """(ideal_shape, confidence) for one closed internal profile."""
    poly = profile.get("polygon_view_normalized") or []
    bbox = profile.get("bbox_view_normalized") or [0, 0, 0, 0]
    w, h = bbox[2], bbox[3]
    if w <= 0 or h <= 0 or len(poly) < 3:
        return "polygon", 0.0
    aspect = w / h
    circ = _circularity(poly)
    if CIRCLE_MIN_CIRC <= circ and CIRCLE_ASPECT[0] <= aspect <= CIRCLE_ASPECT[1]:
        return "circle", min(1.0, (circ - CIRCLE_MIN_CIRC) / 0.15 + 0.5)
    if _is_rectangle(poly):
        return "rectangle", 0.9
    long_ratio = max(aspect, 1 / aspect)
    if SLOT_MIN_CIRC <= circ and SLOT_ASPECT[0] <= long_ratio <= SLOT_ASPECT[1]:
        return "slot", 0.7
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


def _axis_tol(items: list[dict[str, Any]], axis: int) -> float:
    # Hand wobble scales with feature size: a 0.28-tall slot row drifts ~0.06
    # in v (real GT centroids), which a fixed 0.025 tol shreds into fragments.
    # Size-relative tolerance keeps distinct feature rows apart (headlight row
    # vs slot row stay >tol separated) while absorbing wobble within one row.
    sizes = sorted(e["size_view_normalized"][axis] for e in items)
    if not sizes:
        return ALIGN_TOL
    return max(ALIGN_TOL, 0.35 * median(sizes))


def refine_view(view: dict[str, Any]) -> dict[str, Any]:
    """Idealized shape/center/size per profile for one view's measured geometry."""
    profiles = view.get("internal_profiles") or []
    refined: list[dict[str, Any]] = []
    for profile in profiles:
        shape, confidence = classify_profile(profile)
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

    # Row/column alignment snap on centres. Tolerance is feature-size relative
    # (see _axis_tol) so genuine hand-wobble inside one row collapses onto the
    # shared axis while distinct feature rows stay separated.
    us = [e["center_view_normalized"][0] for e in refined]
    vs = [e["center_view_normalized"][1] for e in refined]
    tol_v = _axis_tol(refined, 1)
    tol_u = _axis_tol(refined, 0)
    for group in _cluster(vs, tol_v):        # rows share one v
        if len(group) >= 2:
            canon = round(median(vs[i] for i in group), 4)
            for idx in group:
                if refined[idx]["center_view_normalized"][1] != canon:
                    refined[idx]["snapped"]["center_v"] = {"from": refined[idx]["center_view_normalized"][1], "to": canon}
                    refined[idx]["center_view_normalized"][1] = canon
    for group in _cluster(us, tol_u):        # columns share one u
        if len(group) >= 2:
            canon = round(median(us[i] for i in group), 4)
            for idx in group:
                if refined[idx]["center_view_normalized"][0] != canon:
                    refined[idx]["snapped"]["center_u"] = {"from": refined[idx]["center_view_normalized"][0], "to": canon}
                    refined[idx]["center_view_normalized"][0] = canon

    # Regular-grid report: rows x cols of matching pitch -> tell the generator.
    grid = _grid_report(refined)
    outer_shape, outer_snap = None, {}
    outer = view.get("outer_profile")
    if outer and (outer.get("polygon_view_normalized") or []):
        if _is_rectangle(outer["polygon_view_normalized"]):
            outer_shape = "rectangle"
        else:
            outer_shape, conf = classify_profile(outer)
            if conf < 0.5:
                outer_shape = "polygon"
    result: dict[str, Any] = {"view_id": view.get("view_id"), "profiles": refined}
    if outer_shape:
        result["outer_profile_ideal"] = outer_shape
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
    rows = _cluster([e["center_view_normalized"][1] for e in pool], _axis_tol(pool, 1))
    cols = _cluster([e["center_view_normalized"][0] for e in pool], _axis_tol(pool, 0))
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
                     "sizes, grid loops) — never trace the raw wobbly polygon."),
        "views": [refine_view(view) for view in views],
    }
