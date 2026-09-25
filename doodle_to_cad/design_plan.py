from __future__ import annotations
from typing import Any

FAMILIES={"extrude","revolve","multi_face_union","loft","sweep","shell","assembled","freeform","ambiguous"}
OPERATIONS={"base_feature","union","through_cut","pocket","boss","revolve","extrude","loft","sweep","shell","fillet","chamfer","pattern"}

def normalize_design_plan(spec:dict[str,Any])->dict[str,Any]:
    raw=spec.get("construction_plan") if isinstance(spec.get("construction_plan"),dict) else {}
    family=str(raw.get("family") or _infer_family(spec)).lower()
    if family not in FAMILIES:family="ambiguous"
    operations=[]
    for index,item in enumerate(raw.get("operations") or []):
        if not isinstance(item,dict):continue
        kind=str(item.get("operation","")).lower()
        if kind not in OPERATIONS:continue
        operations.append({"id":str(item.get("id") or f"op_{index+1}"),"operation":kind,
            "profile_plane":item.get("profile_plane"),"direction_axis":item.get("direction_axis"),
            "owner":item.get("owner"),"parameters":item.get("parameters") or {},"source_views":item.get("source_views") or []})
    if not operations:
        operations=[{"id":"body","operation":"base_feature","profile_plane":None,"direction_axis":None,"owner":None,"parameters":{},"source_views":[]}]
    represented={str(operation.get("owner") or operation.get("id")) for operation in operations}
    for i,feature in enumerate(spec.get("features") or []):
        if isinstance(feature,dict):
            feature_id=str(feature.get("id") or f"feature_{i+1}");kind=str(feature.get("type","")).lower();description=feature.get("description") or feature.get("geometry");owner=feature.get("owning_part")
        else:
            feature_id=f"feature_{i+1}";kind=str(feature).lower();description=str(feature);owner=None
        op="through_cut" if any(word in kind for word in ("hole","slot","cutout","opening")) else "boss" if any(word in kind for word in ("boss","protrusion")) else None
        if op and feature_id not in represented:
            operations.append({"id":feature_id,"operation":op,"profile_plane":None,"direction_axis":None,"owner":owner,"parameters":{"description":description},"source_views":[]})
            represented.add(feature_id)
    return {"schema_version":1,"family":family,"coordinate_frame":{"x":"width","y":"depth","z":"height",
        "front":{"plane":"XZ","view_axis":"Y"},"top":{"plane":"XY","view_axis":"Z"},"right":{"plane":"YZ","view_axis":"X"}},
        "operations":operations,"unresolved_constraints":raw.get("unresolved_constraints") or spec.get("uncertainties") or []}

def _infer_family(spec:dict[str,Any])->str:
    parts=[str(p.get("primitive",p.get("name",""))) if isinstance(p,dict) else str(p) for p in spec.get("parts") or []]
    text=" ".join([str(spec.get("manufacturing_strategy","")),str(spec.get("dimensionality",""))]+parts).lower()
    if any(k in text for k in ("revolv","axisym","lathe")):return "revolve"
    if any(k in text for k in ("shell","hollow")):return "shell"
    if any(k in text for k in ("bent","l-shaped","assembled","union")):return "multi_face_union"
    if any(k in text for k in ("extrud","plate","laser","sheet")):return "extrude"
    return "ambiguous"
