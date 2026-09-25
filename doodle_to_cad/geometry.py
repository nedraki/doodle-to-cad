from __future__ import annotations

from typing import Any

import cv2
import numpy as np


def _point_in_group(point: list[float], group: dict[str, Any]) -> bool:
    x, y, width, height = group["bbox_normalized"]
    return x <= point[0] <= x + width and y <= point[1] <= y + height


def _view_local_shape(shape: dict[str, Any], group: dict[str, Any]) -> dict[str, Any]:
    gx, gy, gw, gh = group["bbox_normalized"]
    x, y, width, height = shape["bbox_normalized"]
    local_bbox = [(x-gx)/gw, (y-gy)/gh, width/gw, height/gh]
    local_center = [(shape["center_normalized"][0]-gx)/gw, (shape["center_normalized"][1]-gy)/gh]
    local_polygon = [[(px-gx)/gw, (py-gy)/gh] for px,py in shape.get("polygon_sheet_normalized",[])]
    return {
        "profile_id": shape["contour_id"],
        "bbox_view_normalized": [round(value,4) for value in local_bbox],
        "center_view_normalized": [round(value,4) for value in local_center],
        "polygon_view_normalized": [[round(px,4),round(py,4)] for px,py in local_polygon],
        "vertices": shape["vertices"],
        "circularity": shape["circularity"],
        "area_ratio_of_sheet": shape["area_ratio"],
    }


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
            "outer_profile":_view_local_shape(outer,group) if outer else None,
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
    shapes: list[dict[str, Any]] = []
    indexed = sorted(enumerate(contours), key=lambda pair: cv2.contourArea(pair[1]), reverse=True)[:80]
    for contour_index, contour in indexed:
        area = float(cv2.contourArea(contour))
        if area < min_area:
            continue
        perimeter = float(cv2.arcLength(contour, True))
        approx = cv2.approxPolyDP(contour, 0.015 * perimeter, True)
        x, y, cw, ch = cv2.boundingRect(contour)
        circularity = 4 * np.pi * area / (perimeter * perimeter) if perimeter else 0
        depth, parent = 0, int(tree[contour_index][3]) if len(tree) else -1
        cursor = parent
        while cursor >= 0 and len(tree):
            depth += 1
            cursor = int(tree[cursor][3])
        polygon=[[round(float(point[0][0])/w,4),round(float(point[0][1])/h,4)] for point in approx]
        shapes.append({
            "contour_id":f"contour_{contour_index}",
            "parent_contour_id":f"contour_{parent}" if parent>=0 else None,
            "area_ratio": round(area / (w * h), 5),
            "bbox_normalized": [round(x/w,4), round(y/h,4), round(cw/w,4), round(ch/h,4)],
            "center_normalized": [round((x+cw/2)/w,4), round((y+ch/2)/h,4)],
            "vertices": len(approx), "circularity": round(float(circularity), 3),
            "hierarchy_depth": depth,
            "closed_internal_profile": bool(depth >= 2 and area < w*h*0.08),
            "polygon_sheet_normalized":polygon,
        })
    lines = cv2.HoughLinesP(binary, 1, np.pi/180, threshold=max(25, min(w,h)//12), minLineLength=min(w,h)//12, maxLineGap=12)
    line_count = 0 if lines is None else min(len(lines), 200)
    view_groups = _view_groups(binary, w, h)
    for index,group in enumerate(view_groups,1):group["view_id"]=f"view_{index}"
    internal_profiles = [shape for shape in shapes if shape["closed_internal_profile"]]
    # A thick pen stroke produces two nested contours for one opening. Even
    # hierarchy depths identify the physical enclosed profiles without counting
    # both borders of the same stroke.
    logical_internal_profiles = [shape for shape in internal_profiles if shape["hierarchy_depth"] % 2 == 0]
    evidence = {
        "image_size_px": [w, h],
        "ink_fraction": round(float(np.count_nonzero(binary))/(w*h), 4),
        "contour_count": len(shapes), "line_count": line_count,
        "drawing_sheet_contract": "All spatial groups are projections or isometric depictions of ONE physical object.",
        "view_group_count": len(view_groups), "view_groups": view_groups,
        "closed_internal_profile_count": len(logical_internal_profiles),
        "closed_internal_profiles": logical_internal_profiles[:24],
        "largest_regions": shapes[:20],
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
