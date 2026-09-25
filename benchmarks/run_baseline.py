from __future__ import annotations
import json
from pathlib import Path
import trimesh
from doodle_to_cad.evaluation import projection_scores
from doodle_to_cad.geometry import analyze_image

ROOT=Path(__file__).resolve().parent

def run_case(case:Path)->dict:
    manifest=json.loads((case/"manifest.json").read_text());drawing=(case/"source/drawing.png").read_bytes()
    evidence,_=analyze_image(drawing)
    views={name:case/f"derived/view-{name}.png" for name in ("front","top","right","isometric")}
    views={name:path for name,path in views.items() if path.exists()}
    declared=(manifest.get("drawing") or {}).get("views") or manifest.get("views") or []
    controls=manifest.get("controls") or {}
    primary=controls.get("primary_view") or next((v["direction"] for v in declared if v.get("direction") in {"front","top","right","left"}),"front")
    projection=str(controls.get("projection_standard") or (manifest.get("drawing") or {}).get("projection_standard") or "third-angle").split("_")[0]
    similarities,profiles=projection_scores(drawing,evidence,views,primary,projection)
    mesh=trimesh.load_mesh(case/"ground_truth/model.stl",process=True)
    expected=manifest.get("acceptance",{}).get("mandatory",{}).get("through_cutout_count")
    observed=profiles.get(primary,{}).get("rendered_internal_profiles")
    return {"id":manifest["id"],"family":manifest["semantic_labels"].get("family") or manifest["semantic_labels"].get("construction_family"),
        "reference_quality_status":manifest["status"],"drawing_evidence":{"view_group_count":evidence["view_group_count"],"logical_internal_profile_count":evidence["closed_internal_profile_count"]},
        "reference_mesh":{"watertight":bool(mesh.is_watertight),"components":len(mesh.split(only_watertight=False)),"extents_mm":[round(float(x),4) for x in mesh.extents]},
        "registered_projection_similarity":similarities,"profile_topology":profiles,
        "reference_cutout_check":{"expected":expected,"rendered":observed,"matches":None if expected is None or observed is None else observed==expected},
        "eligible_for_threshold_calibration":manifest["status"].startswith("reference_pair_verified")}

def main()->int:
    cases=[run_case(path.parent) for path in sorted((ROOT/"cases").glob("*/manifest.json"))]
    report={"schema_version":1,"case_count":len(cases),"warning":"Descriptive baseline only; three development cases are insufficient for threshold calibration.","cases":cases}
    target=ROOT/"baseline-report.json";target.write_text(json.dumps(report,indent=2)+"\n");print(json.dumps(report,indent=2));return 0

if __name__=="__main__":raise SystemExit(main())
