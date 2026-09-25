from __future__ import annotations
import re
from typing import Any

_GEOMETRY_CALLS = (
    "cube", "cylinder", "sphere", "polyhedron", "polygon", "circle", "square",
    "linear_extrude", "rotate_extrude", "surface", "import", "union", "difference",
    "intersection", "hull", "minkowski", "offset", "resize",
)


def _strip_comments(scad: str) -> str:
    # Token checks must never see comment prose ("bounding box (0,0,0)" used to
    # trip the box() ban and killed a compilable model).
    scad = re.sub(r"/\*.*?\*/", " ", scad, flags=re.S)
    return re.sub(r"//[^\n]*", " ", scad)


def preflight_scad(scad:str,spec:dict[str,Any])->dict[str,Any]:
    errors=[];warnings=[]
    code=_strip_comments(scad)
    scad=code
    if re.search(r"\bfunction\s+\w+\s*\([^)]*\)\s*\{",scad):errors.append("OpenSCAD functions require '=' expressions; use module for geometry blocks")
    geometry_names="|".join(_GEOMETRY_CALLS + ("box", "revolve"))
    if re.search(rf"^\s*\w+\s*=\s*(?:{geometry_names})\s*\(",scad,re.M):errors.append("CSG geometry cannot be assigned to a scalar variable; place it in a module or CSG block")
    if re.search(r"\bbox\s*\(",scad):errors.append("unknown OpenSCAD module box(); use cube()")
    if re.search(r"\brevolve\s*\(",scad):errors.append("unknown OpenSCAD module revolve(); use rotate_extrude() with a 2D radius/height profile")
    if scad.count("{")!=scad.count("}"):errors.append("unbalanced braces")
    if scad.count("(")!=scad.count(")"):errors.append("unbalanced parentheses")
    top_level=[];depth=0
    for line in scad.splitlines():
        stripped=re.sub(r"//.*$", "", line).strip()
        if depth==0 and stripped and not stripped.startswith(("module ","function ","include ","use ")):
            if re.match(r"(?:difference|union|intersection|hull|minkowski|cube|cylinder|sphere|polyhedron|linear_extrude|rotate_extrude|[A-Za-z_]\w*)\s*\(",stripped):
                top_level.append(stripped)
        depth += stripped.count("{")-stripped.count("}")
    if len(top_level)>1:
        warnings.append(f"multiple top-level geometry expressions detected ({len(top_level)}); ensure they intentionally form one connected design")
    def feature_kind(feature:Any)->str:
        return str(feature.get("type",feature.get("geometry",""))) if isinstance(feature,dict) else str(feature)
    expected=sum(1 for f in spec.get("features") or [] if any(word in feature_kind(f).lower() for word in ("hole","slot","cutout","opening")))
    if expected and not re.search(r"\bdifference\s*\(",scad):errors.append("subtractive features are specified but no difference() operation exists")
    if expected and not re.search(r"(?:translate|rotate|multmatrix)\s*\(",scad):warnings.append("multiple subtractive features have no visible placement transforms")
    if re.search(r"\bcircle\s*\([^)]*\bcenter\s*=",scad):warnings.append("circle() does not use a center position; position it with translate()")
    return {"passed":not errors,"errors":errors,"warnings":warnings,"expected_subtractive_feature_groups":expected}
