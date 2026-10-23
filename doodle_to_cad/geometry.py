from __future__ import annotations

import math
from typing import Any

import cv2
import numpy as np


def _resample_closed(points: list[list[float]], count: int) -> list[list[float]]:
    """Evenly resample a closed polyline to `count` vertices."""
    n = len(points)
    if n < 3:
        return points
    total = 0.0
    gaps = []
    for i in range(n):
        d = math.dist(points[i], points[(i + 1) % n])
        gaps.append(d)
        total += d
    if total <= 0:
        return points
    step = total / count
    out: list[list[float]] = [list(points[0])]
    travelled, segment_start, index, used = 0.0, points[0], 0, 0.0
    for k in range(1, count):
        target = k * step
        while index < n - 1 and used + gaps[index] < target:
            used += gaps[index]
            index += 1
            segment_start = points[index]
        span = max(gaps[index], 1e-9)
        t = min(max((target - used) / span, 0.0), 1.0)
        nxt = points[(index + 1) % n]
        out.append([segment_start[0] + (nxt[0] - segment_start[0]) * t,
                    segment_start[1] + (nxt[1] - segment_start[1]) * t])
    return out


def _chord_deviation(pts: list[list[float]]) -> tuple[int, float]:
    """Index and distance of the point furthest from the chord of an open run."""
    a, b = pts[0], pts[-1]
    vx, vy = b[0] - a[0], b[1] - a[1]
    length_sq = vx * vx + vy * vy
    worst_i, worst_d = 0, 0.0
    for i in range(1, len(pts) - 1):
        if length_sq <= 1e-12:
            d = math.dist(pts[i], a)
        else:
            t = ((pts[i][0] - a[0]) * vx + (pts[i][1] - a[1]) * vy) / length_sq
            t = min(max(t, 0.0), 1.0)
            d = math.hypot(pts[i][0] - (a[0] + vx * t), pts[i][1] - (a[1] + vy * t))
        if d > worst_d:
            worst_i, worst_d = i, d
    return worst_i, worst_d


def _circle_from_three(a: list[float], b: list[float], c: list[float]) -> tuple[float, float, float] | None:
    """(cx, cy, r) through three points, or None when they are collinear."""
    ax, ay = a; bx, by = b; cx, cy = c
    d = 2 * (ax * (by - cy) + bx * (cy - ay) + cx * (ay - by))
    if abs(d) < 1e-9:
        return None
    ux = ((ax**2 + ay**2) * (by - cy) + (bx**2 + by**2) * (cy - ay) + (cx**2 + cy**2) * (ay - by)) / d
    uy = ((ax**2 + ay**2) * (cx - bx) + (bx**2 + by**2) * (ax - cx) + (cx**2 + cy**2) * (bx - ax)) / d
    return ux, uy, math.hypot(ax - ux, ay - uy)


def fit_curve_segments(points: list[list[float]], *, tolerance: float = 0.015,
                       min_chord: float = 0.03, max_segments: int = 24) -> dict[str, Any]:
    """Split a closed normalized polygon into line and arc runs, with fit errors.

    Greedy recursive chord splitting: a run whose interior points deviate from
    its chord by more than `tolerance` is split at the worst point; short low-
    deviation runs become lines, curved runs are fitted as circular arcs
    through (start, worst-deviation point, end). Every emitted segment carries
    its max fit error so downstream stages (and tests) can reject a "regularized"
    curve that no longer matches the ink.
    """
    pts = _resample_closed(points, 72)
    n = len(pts)
    intervals: list[tuple[int, int]] = []
    # Seed with two arc-length-opposed intervals: a single (0, n) interval has
    # a zero-length chord (start == end on a closed loop) and never splits.
    stack = [(0, n // 2), (n // 2, n)] if n >= 4 else [(0, n)]
    while stack:
        i, j = stack.pop()
        run = pts[i:j] if j <= n else pts[i:] + pts[:j - n]
        k, dev = _chord_deviation(run)
        chord = math.dist(pts[i], pts[j % n])
        if dev > tolerance and (j - i) > 6 and chord > 2 * min_chord and len(intervals) + len(stack) < max_segments:
            mid = i + k
            stack.append((i, mid)); stack.append((mid, j))
            continue
        intervals.append((i, j))
    segments: list[dict[str, Any]] = []
    worst_error = 0.0
    for i, j in intervals:
        run = pts[i:j] if j <= n else pts[i:] + pts[:j - n]
        k, dev = _chord_deviation(run)
        a, b = list(pts[i]), list(pts[j % n])
        worst_error = max(worst_error, dev)
        if dev <= max(tolerance * 0.4, 1e-4):
            segments.append({"type": "line", "from": a, "to": b, "max_error": round(dev, 4)})
            continue
        mid_pt = list(pts[(i + k) % n])
        circle = _circle_from_three(a, mid_pt, b)
        if circle is None:
            segments.append({"type": "line", "from": a, "to": b, "max_error": round(dev, 4)})
            continue
        cx, cy, r = circle
        arc_error = max(abs(math.hypot(p[0] - cx, p[1] - cy) - r) for p in run) if len(run) else dev
        worst_error = max(worst_error, arc_error)
        segments.append({"type": "arc", "from": a, "to": b, "mid": mid_pt,
                         "radius": round(r, 4), "max_error": round(min(arc_error, dev), 4)})
    return {"segments": [{**s, "from": [round(v, 4) for v in s["from"]],
                          "to": [round(v, 4) for v in s["to"]],
                          **({"mid": [round(v, 4) for v in s["mid"]]} if "mid" in s else {})}
                         for s in segments],
            "fit_error": round(worst_error, 4)}


def _point_in_group(point: list[float], group: dict[str, Any]) -> bool:
    x, y, width, height = group["bbox_normalized"]
    return x <= point[0] <= x + width and y <= point[1] <= y + height


def _view_local_shape(shape: dict[str, Any], group: dict[str, Any], *, outer: bool = False) -> dict[str, Any]:
    gx, gy, gw, gh = group["bbox_normalized"]
    x, y, width, height = shape["bbox_normalized"]
    local_bbox = [(x-gx)/gw, (y-gy)/gh, width/gw, height/gh]
    local_center = [(shape["center_normalized"][0]-gx)/gw, (shape["center_normalized"][1]-gy)/gh]
    local_polygon = [[(px-gx)/gw, (py-gy)/gh] for px,py in shape.get("polygon_sheet_normalized",[])]
    result = {
        "profile_id": shape["contour_id"],
        "bbox_view_normalized": [round(value,4) for value in local_bbox],
        "center_view_normalized": [round(value,4) for value in local_center],
        "polygon_view_normalized": [[round(px,4),round(py,4)] for px,py in local_polygon],
        "vertices": shape["vertices"],
        "circularity": shape["circularity"],
        "area_ratio_of_sheet": shape["area_ratio"],
    }
    if outer:
        # The outer silhouette is an extrusion profile the generator must keep:
        # give it a high-fidelity polygon (1/4 the simplification epsilon of
        # the display polygon) plus a line/arc decomposition with per-segment
        # fit errors, so "regularized" never silently means "flattened".
        dense = shape.get("dense_polygon_sheet_normalized") or shape.get("polygon_sheet_normalized") or []
        local_dense = [[(px-gx)/gw, (py-gy)/gh] for px,py in dense]
        result["polygon_dense_view_normalized"] = [[round(px,4),round(py,4)] for px,py in local_dense]
        if len(local_dense) >= 3:
            result.update(fit_curve_segments(local_dense))
    return result


def _geometry_by_view(groups: list[dict[str, Any]], shapes: list[dict[str, Any]], image_width: int, image_height: int) -> list[dict[str, Any]]:
    result=[]
    for group in groups:
        members=[shape for shape in shapes if _point_in_group(shape["center_normalized"],group)]
        outer_candidates=[shape for shape in members if not shape["closed_internal_profile"] and shape["hierarchy_depth"] in (0,1)]
        outer=max(outer_candidates,key=lambda shape:shape["area_ratio"],default=None)
        internal=[shape for shape in members if shape["closed_internal_profile"] and shape["hierarchy_depth"]%2==0]
        _,_,width,height=group["bbox_normalized"]
        result.append({
            "view_id":group["view_id"],
            "sheet_bbox_normalized":group["bbox_normalized"],
            "pixel_aspect_ratio_width_over_height":round((width*image_width)/max(height*image_height,1),4),
            # What the drawn ink measures in pixels along this view's own axes.
            # (view-local fractions are scale-blind; these are not.)
            "measured_span_pixels":{"horizontal_axis_u":max(int(round(width*image_width)),1),
                                    "vertical_axis_v":max(int(round(height*image_height)),1)},
            "coordinate_system":{
                "origin":"top-left of this view crop",
                "u_axis":"right",
                "v_axis":"down",
                "range":"u and v are normalized from 0 to 1 within this view",
            },
            "outer_profile":_view_local_shape(outer,group,outer=True) if outer else None,
            "internal_profiles":[_view_local_shape(shape,group) for shape in sorted(internal,key=lambda shape:(shape["center_normalized"][1],shape["center_normalized"][0]))],
        })
    return result


def label_view_geometry(evidence: dict[str, Any], assigned: dict[str, dict[str, Any]]) -> dict[str, Any]:
    """Attach semantic view directions and an explicit view-local-to-CAD mapping."""
    direction_by_id={group.get("view_id"):direction for direction,group in assigned.items()}
    axis_contracts={
        "front":{"plane":"XZ","view_axis":"Y","u_maps_to":"+X","v_maps_to":"-Z"},
        "rear":{"plane":"XZ","view_axis":"Y","u_maps_to":"-X","v_maps_to":"-Z"},
        # Measured against the pipeline's own orthographic cameras AND third-angle
        # drafting convention: on the sheet, the top view's DOWN direction is the
        # FRONT of the part (-Y); +Y (back) is toward the top of the sheet.
        "top":{"plane":"XY","view_axis":"Z","u_maps_to":"+X","v_maps_to":"-Y"},
        "bottom":{"plane":"XY","view_axis":"Z","u_maps_to":"+X","v_maps_to":"+Y"},
        "right":{"plane":"YZ","view_axis":"X","u_maps_to":"+Y","v_maps_to":"-Z"},
        "left":{"plane":"YZ","view_axis":"X","u_maps_to":"-Y","v_maps_to":"-Z"},
    }
    for view in evidence.get("view_geometry",[]):
        direction=direction_by_id.get(view.get("view_id"))
        if direction:
            view["direction"]=direction
            view["cad_mapping"]=axis_contracts.get(direction,{})
    evidence["coordinate_contract"]={
        "sheet":{"origin":"top-left","x_axis":"right","y_axis":"down","units":"normalized image fraction"},
        "cad":{"origin":"shared object origin","x_axis":"width","y_axis":"front-to-back depth","z_axis":"height","units":"millimetres"},
        "rule":"Use view-local profile coordinates and cad_mapping; sheet placement separates views and is never physical geometry.",
    }
    return evidence


# Issue #67: a hand-drawn opening is a small round STROKE RING — an outer
# boundary whose child (the stroke's inner edge) encloses 15..92% of its own
# area. Circles drawn inside a view group but NOT geometrically enclosed by the
# view outline (hook elevations, stepped brackets) sit at hierarchy depth 0/1,
# so the depth>=2 rule silently drops them and no per-view gate can demand
# them. Circularity separates hand-inked circles (measured 0.84-0.92 on the
# corpus) from view silhouettes (measured <=0.57); the dominance cap keeps a
# view's own circular outline from being counted as an opening.
RING_CIRCULARITY_MIN = 0.75
RING_CHILD_RATIO_RANGE = (0.15, 0.92)
RING_AREA_SHARE_OF_GROUP_DOMINANT_MAX = 0.15


def _stroke_ring_stats(contours: list, tree) -> list[dict[str, Any]]:
    """Per-contour {area, circularity, max_child_area, center} from the RAW
    contour set — before analyze_image's top-80 truncation, so a ring's
    stroke child is never missing from the ratio check."""
    stats: list[dict[str, Any]] = []
    for index, contour in enumerate(contours):
        area = float(cv2.contourArea(contour))
        perimeter = float(cv2.arcLength(contour, True))
        circularity = 4 * np.pi * area / (perimeter * perimeter) if perimeter else 0.0
        x, y, cw, ch = cv2.boundingRect(contour)
        child_area = 0.0
        if len(tree):
            for other_index, row in enumerate(tree):
                if int(row[3]) == index:
                    child_area = max(child_area, float(cv2.contourArea(contours[other_index])))
        stats.append({"area": area, "circularity": circularity,
                      "max_child_area": child_area, "center": (x + cw / 2, y + ch / 2)})
    return stats


def _is_stroke_ring(stat: dict[str, Any]) -> bool:
    if stat["circularity"] < RING_CIRCULARITY_MIN or stat["max_child_area"] <= 0:
        return False
    ratio = stat["max_child_area"] / max(stat["area"], 1e-9)
    return RING_CHILD_RATIO_RANGE[0] <= ratio <= RING_CHILD_RATIO_RANGE[1]


def analyze_image(data: bytes) -> tuple[dict[str, Any], bytes]:
    image = cv2.imdecode(np.frombuffer(data, np.uint8), cv2.IMREAD_COLOR)
    if image is None:
        raise ValueError("Unsupported or corrupt image")
    h, w = image.shape[:2]
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(gray, (5, 5), 0)
    binary = cv2.adaptiveThreshold(blur, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 31, 9)
    binary = cv2.morphologyEx(binary, cv2.MORPH_OPEN, np.ones((2, 2), np.uint8))
    contours, hierarchy = cv2.findContours(binary, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
    tree = hierarchy[0] if hierarchy is not None else []
    min_area = max(20.0, w * h * 0.00015)
    contour_stats = _stroke_ring_stats(contours, tree)
    # View groups come FIRST: an orphan opening ring counts as a closed
    # internal profile only when it lies inside a registered view group.
    view_groups = _view_groups(binary, w, h)
    group_rects_px = [(g["bbox_normalized"][0] * w, g["bbox_normalized"][1] * h,
                       (g["bbox_normalized"][0] + g["bbox_normalized"][2]) * w,
                       (g["bbox_normalized"][1] + g["bbox_normalized"][3]) * h)
                      for g in view_groups]
    group_dominant_area = []
    for rect in group_rects_px:
        dominant = 0.0
        for stat in contour_stats:
            cx, cy = stat["center"]
            if rect[0] <= cx <= rect[2] and rect[1] <= cy <= rect[3]:
                dominant = max(dominant, stat["area"])
        group_dominant_area.append(dominant)

    def _orphan_ring_in_view(index: int) -> bool:
        """A small round stroke ring that lies inside a view group but is not
        the group's dominant outline: an opening drawn beside an open hook
        elevation rather than enclosed by it (issue #67)."""
        stat = contour_stats[index]
        if not _is_stroke_ring(stat) or stat["area"] >= w * h * 0.08:
            return False
        cx, cy = stat["center"]
        for group_index, rect in enumerate(group_rects_px):
            if rect[0] <= cx <= rect[2] and rect[1] <= cy <= rect[3]:
                if stat["area"] <= RING_AREA_SHARE_OF_GROUP_DOMINANT_MAX * group_dominant_area[group_index]:
                    return True
        return False
    shapes: list[dict[str, Any]] = []
    indexed = sorted(enumerate(contours), key=lambda pair: cv2.contourArea(pair[1]), reverse=True)[:80]
    for contour_index, contour in indexed:
        area = float(cv2.contourArea(contour))
        if area < min_area:
            continue
        perimeter = float(cv2.arcLength(contour, True))
        approx = cv2.approxPolyDP(contour, 0.015 * perimeter, True)
        dense_approx = cv2.approxPolyDP(contour, 0.004 * perimeter, True)
        if len(dense_approx) > 96:  # bound the evidence payload; keep shape by uniform thinning
            stride = -(-len(dense_approx) // 96)
            dense_approx = dense_approx[::stride]
        x, y, cw, ch = cv2.boundingRect(contour)
        circularity = 4 * np.pi * area / (perimeter * perimeter) if perimeter else 0
        depth, parent = 0, int(tree[contour_index][3]) if len(tree) else -1
        cursor = parent
        while cursor >= 0 and len(tree):
            depth += 1
            cursor = int(tree[cursor][3])
        polygon=[[round(float(point[0][0])/w,4),round(float(point[0][1])/h,4)] for point in approx]
        dense_polygon=[[round(float(point[0][0])/w,4),round(float(point[0][1])/h,4)] for point in dense_approx]
        enclosed_profile = bool(depth >= 2 and area < w*h*0.08)
        orphan_ring = (not enclosed_profile) and depth % 2 == 0 and _orphan_ring_in_view(contour_index)
        shapes.append({
            "contour_id":f"contour_{contour_index}",
            "parent_contour_id":f"contour_{parent}" if parent>=0 else None,
            "area_ratio": round(area / (w * h), 5),
            "bbox_normalized": [round(x/w,4), round(y/h,4), round(cw/w,4), round(ch/h,4)],
            "center_normalized": [round((x+cw/2)/w,4), round((y+ch/2)/h,4)],
            "vertices": len(approx), "circularity": round(float(circularity), 3),
            "hierarchy_depth": depth,
            "closed_internal_profile": bool(enclosed_profile or orphan_ring),
            "orphan_opening_ring": bool(orphan_ring),
            "polygon_sheet_normalized":polygon,
            "dense_polygon_sheet_normalized":dense_polygon,
        })
    lines = cv2.HoughLinesP(binary, 1, np.pi/180, threshold=max(25, min(w,h)//12), minLineLength=min(w,h)//12, maxLineGap=12)
    line_count = 0 if lines is None else min(len(lines), 200)
    for index,group in enumerate(view_groups,1):group["view_id"]=f"view_{index}"
    internal_profiles = [shape for shape in shapes if shape["closed_internal_profile"]]
    # A thick pen stroke produces two nested contours for one opening. Even
    # hierarchy depths identify the physical enclosed profiles without counting
    # both borders of the same stroke.
    logical_internal_profiles = [shape for shape in internal_profiles if shape["hierarchy_depth"] % 2 == 0]
    def _slim(shape: dict[str, Any]) -> dict[str, Any]:  # dense polygons live in view_geometry only
        return {key: value for key, value in shape.items() if key != "dense_polygon_sheet_normalized"}
    evidence = {
        "image_size_px": [w, h],
        "ink_fraction": round(float(np.count_nonzero(binary))/(w*h), 4),
        "contour_count": len(shapes), "line_count": line_count,
        "drawing_sheet_contract": "All spatial groups are projections or isometric depictions of ONE physical object.",
        "view_group_count": len(view_groups), "view_groups": view_groups,
        "closed_internal_profile_count": len(logical_internal_profiles),
        "closed_internal_profiles": [_slim(shape) for shape in logical_internal_profiles[:24]],
        "largest_regions": [_slim(shape) for shape in shapes[:20]],
        "view_geometry":_geometry_by_view(view_groups,shapes,w,h),
    }
    overlay = image.copy()
    cv2.drawContours(overlay, [c for c in contours if cv2.contourArea(c)>=min_area], -1, (70, 235, 170), 2)
    ok, encoded = cv2.imencode(".png", overlay)
    return evidence, encoded.tobytes() if ok else data


def _view_groups(binary: np.ndarray, width: int, height: int) -> list[dict[str, Any]]:
    """Find spatial drawing clusters without interpreting them as separate objects."""
    kernel = cv2.getStructuringElement(
        cv2.MORPH_RECT,
        (max(7, width // 55), max(7, height // 55)),
    )
    joined = cv2.dilate(binary, kernel, iterations=1)
    count, _, stats, _ = cv2.connectedComponentsWithStats(joined, connectivity=8)
    raw_groups = []
    for label in range(1, count):
        x, y, w, h, area = map(int, stats[label])
        if area < width * height * 0.002:
            continue
        raw_groups.append({"x": x, "y": y, "w": w, "h": h, "area": area})
    # Internal holes and slots are disconnected ink islands but belong to the
    # surrounding view. Merge any component whose center lies inside a larger
    # component's drawing bounds.
    keep = []
    for index, group in enumerate(raw_groups):
        cx, cy = group["x"] + group["w"]/2, group["y"] + group["h"]/2
        contained = False
        for other_index, other in enumerate(raw_groups):
            if index == other_index or other["w"]*other["h"] <= group["w"]*group["h"]:
                continue
            margin_x, margin_y = other["w"]*.03, other["h"]*.03
            if other["x"]-margin_x <= cx <= other["x"]+other["w"]+margin_x and other["y"]-margin_y <= cy <= other["y"]+other["h"]+margin_y:
                contained = True
                break
        if not contained:
            keep.append(group)
    groups = []
    for group in keep:
        x, y, w, h = group["x"], group["y"], group["w"], group["h"]
        groups.append({
            "bbox_normalized": [round(x/width, 4), round(y/height, 4), round(w/width, 4), round(h/height, 4)],
            "center_normalized": [round((x+w/2)/width, 4), round((y+h/2)/height, 4)],
            "relative_size": round((w*h)/(width*height), 4),
            "meaning": "view_of_same_object",
        })
    return sorted(groups, key=lambda group: (group["center_normalized"][1], group["center_normalized"][0]))[:12]
