
import sys, json, numpy as np, cv2
sys.path.insert(0, "/tmp/doodle-brep-67")
from pathlib import Path
from doodle_to_cad.geometry import analyze_image
from doodle_to_cad.evaluation import assign_view_groups
RUNS = Path("/tmp/doodle-brep-67/docs/brep/task-17-comparison/runs")
for name in ("profiles_empty_notes","ambiguous"):
    tdir = sorted((RUNS/name).glob("*/trial-01"))[0]
    img = (tdir/"input.png").read_bytes()
    ev,_ = analyze_image(img)
    print("="*70); print(name, "groups:", ev["view_group_count"], "sheet_internal:", ev["closed_internal_profile_count"])
    assigned = assign_view_groups(ev, "front", "third-angle")
    print("registered:", {d:(tuple(g["center_normalized"]),tuple(g["bbox_normalized"])) for d,g in assigned.items()})
    for g in ev["view_groups"]:
        print("  group", tuple(g["bbox_normalized"]))
    for s in ev["closed_internal_profiles"]:
        print("  ring", s["contour_id"], "d=",s["hierarchy_depth"], "center",s["center_normalized"], "circ",s["circularity"], "orphan",s.get("orphan_opening_ring"))
