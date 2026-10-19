# Issue #67: per-view crop counts vs sheet internal profiles for motor holder 103
import json, sys
from pathlib import Path
import cv2, numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from doodle_to_cad.geometry import analyze_image
from doodle_to_cad.evaluation import (assign_view_groups, _crop_internal_profile_count,
                                      _profile_centroids)

def report(name: str, image_bytes: bytes, views_dir: Path | None = None):
    print("=" * 72)
    print(name)
    evidence, _ = analyze_image(image_bytes)
    w, h = evidence["image_size_px"]
    print(f"image {w}x{h}  contours={evidence['contour_count']}  "
          f"view_groups={evidence['view_group_count']}  "
          f"sheet_closed_internal_profile_count={evidence['closed_internal_profile_count']}")
    print("sheet-level logical internal profiles:")
    for s in evidence["closed_internal_profiles"]:
        print(f"  {s['contour_id']} depth={s['hierarchy_depth']} area_ratio={s['area_ratio']} "
              f"center={s['center_normalized']} bbox={s['bbox_normalized']} "
              f"circularity={s['circularity']}")
    assigned = assign_view_groups(evidence, "front", "third-angle")
    print("registered views -> group bbox:")
    for d, g in assigned.items():
        print(f"  {d}: {g['bbox_normalized']}")
    # What _geometry_by_view assigned per view
    print("view_geometry internal profile assignments:")
    for v in evidence["view_geometry"]:
        print(f"  {v['view_id']}: outer={'yes' if v['outer_profile'] else 'NONE'} "
              f"internal={len(v['internal_profiles'])} "
              f"ids={[p['profile_id'] for p in v['internal_profiles']]}")
    # What the EVALUATION crop gate sees per registered view
    image = cv2.imdecode(np.frombuffer(image_bytes, np.uint8), cv2.IMREAD_COLOR)
    ih, iw = image.shape[:2]
    totals = {}
    for direction, group in assigned.items():
        x, y, gw, gh = group["bbox_normalized"]
        x0, y0, x1, y1 = max(0, int(x*iw)), max(0, int(y*ih)), min(iw, int((x+gw)*iw)), min(ih, int((y+gh)*ih))
        crop = image[y0:y1, x0:x1]
        cc = _crop_internal_profile_count(crop)
        cents = _profile_centroids(crop, render=False)
        totals[direction] = cc
        print(f"crop gate {direction}: crop_internal_profiles={cc} "
              f"box=({x0},{y0},{x1},{y1}) centroids={[[round(a,3),round(b,3)] for a,b in cents]}")
    print(f"SUM registered crop counts = {sum(totals.values())}  "
          f"(sheet says {evidence['closed_internal_profile_count']})")
    # Raw contour dump in each crop box at depth 2 to see what is being rejected
    for direction, group in assigned.items():
        x, y, gw, gh = group["bbox_normalized"]
        x0, y0, x1, y1 = max(0, int(x*iw)), max(0, int(y*ih)), min(iw, int((x+gw)*iw)), min(ih, int((y+gh)*ih))
        crop = image[y0:y1, x0:x1]
        ink = cv2.threshold(cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY), 190, 255, cv2.THRESH_BINARY_INV)[1]
        ink = cv2.morphologyEx(ink, cv2.MORPH_CLOSE, np.ones((3,3), np.uint8))
        contours, hierarchy = cv2.findContours(ink, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
        if not contours or hierarchy is None:
            continue
        hz = hierarchy[0]
        depths = []
        for i in range(len(contours)):
            d = 0; p = int(hz[i][3])
            while p >= 0: d += 1; p = int(hz[p][3])
            depths.append(d)
        print(f"raw contours inside {direction} crop (ink.size={ink.size}, "
              f"min_area_gate={ink.size*0.0005:.1f}):")
        for i, (c, d) in enumerate(zip(contours, depths)):
            a = cv2.contourArea(c)
            if d >= 1 and a > 5:
                bx, by, bw, bh = cv2.boundingRect(c)
                print(f"  i={i} depth={d} area={a:.0f} bbox=({bx},{by},{bw},{bh})")
    return evidence, totals

CASE = Path(__file__).resolve().parents[1] / "benchmarks/cases/103_y_motor_holder/source/drawing.png"
report("benchmarks/cases/103_y_motor_holder/source/drawing.png", CASE.read_bytes())

LIVE = Path("/tmp/doodle-brep-32/results/7c274ef76d20")
if (LIVE / "input.png").is_file():
    report("live job 7c274ef76d20 input.png", (LIVE / "input.png").read_bytes(), LIVE)
