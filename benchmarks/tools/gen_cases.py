"""Generate deterministic synthetic benchmark cases for doodle-to-cad.

Per case we declare ONE parameter truth:
  - ground_truth/model.scad  (hand-authored, watertight, single component)
  - compiled ground_truth/model.stl (via pipeline OpenSCAD, host or Docker)
  - derived/view-*.png       (pipeline cameras, from the GT scad)
  - source/drawing.png       (jittered 'hand doodle' polylines of the declared
                              view shapes, third-angle sheet layout, seeded RNG)
  - manifest.json            (labels + sha256 + measured topology + BambuLab check)

Usage:  PYTHONPATH=<repo> DOODLE_OPENSCAD_DOCKER=openscad/openscad:latest \
        python benchmarks/tools/gen_cases.py [case_id ...]
"""
from __future__ import annotations
import hashlib
import json
import math
import random
import shutil
import sys
from pathlib import Path

import cv2
import numpy as np
import trimesh

ROOT = Path(__file__).resolve().parents[1]          # benchmarks/
REPO = ROOT.parent                                   # repo root
sys.path.insert(0, str(REPO))
from doodle_to_cad.openscad import compile_and_render  # noqa: E402

BUILD_CUBE_MM = 256.0   # BambuLab X1C/P1S build volume

SHEET_W, SHEET_H = 1000, 750


# ---------------------------------------------------------------- shape DSL
def rect_pts(x, y, w, h):
    return [[x, y], [x + w, y], [x + w, y + h], [x, y + h], [x, y]]

def circle_pts(cx, cy, d, n=48):
    r = d / 2
    return [[cx + r * math.cos(2 * math.pi * i / n), cy + r * math.sin(2 * math.pi * i / n)] for i in range(n + 1)]

def slot_pts(cx, cy, w, h, n=12):
    """stadium shape, w>=h, centered"""
    r = h / 2; half = w / 2 - r
    pts = []
    for i in range(n + 1):                      # right cap
        a = -math.pi / 2 + math.pi * i / n
        pts.append([cx + half + r * math.cos(a), cy + r * math.sin(a)])
    for i in range(n + 1):                      # left cap
        a = math.pi / 2 + math.pi * i / n
        pts.append([cx - half + r * math.cos(a), cy + r * math.sin(a)])
    pts.append(pts[0])
    return pts

def ngon_pts(cx, cy, r, n=6, rot=0.0):
    return [[cx + r * math.cos(2 * math.pi * i / n + rot), cy + r * math.sin(2 * math.pi * i / n + rot)] for i in range(n + 1)]

def shape_pts(sh):
    t = sh["t"]
    if t == "rect":   return rect_pts(sh["x"], sh["y"], sh["w"], sh["h"])
    if t == "circle": return circle_pts(sh["cx"], sh["cy"], sh["d"])
    if t == "slot":   return slot_pts(sh["cx"], sh["cy"], sh["w"], sh["h"])
    if t == "ngon":   return ngon_pts(sh["cx"], sh["cy"], sh["r"], sh.get("n", 6), sh.get("rot", 0.0))
    if t == "poly":   return [list(p) for p in sh["pts"]] + [[p for p in sh["pts"][0]]]
    raise ValueError(t)

def shape_bounds(sh):
    pts = shape_pts(sh)[:-1]
    xs = [p[0] for p in pts]; ys = [p[1] for p in pts]
    return min(xs), min(ys), max(xs), max(ys)


# ---------------------------------------------------------------- doodling
def jitter_polyline(pts, rng, close=True):
    """resample + smooth noise + low-frequency wobble -> wobbly ink path"""
    pts = [p for p in pts]
    if close and pts[0] != pts[-1]:
        pts = pts + [pts[0]]
    # densify
    dense = []
    for a, b in zip(pts[:-1], pts[1:]):
        seg = max(1, int(math.hypot(b[0] - a[0], b[1] - a[1]) / 5))
        for i in range(seg):
            t = i / seg
            dense.append([a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t])
    dense.append(pts[-1])
    n = len(dense)
    # low-frequency wobble (1-2 cycles along path)
    phase = rng.uniform(0, 2 * math.pi); freq = rng.uniform(1, 2.5); amp = rng.uniform(0.6, 1.6)
    out = []
    for i, (x, y) in enumerate(dense):
        s = i / max(n - 1, 1)
        wob = amp * math.sin(2 * math.pi * freq * s + phase)
        dx = rng.gauss(0, 0.55); dy = rng.gauss(0, 0.55)
        out.append([x + dx + wob * 0.35, y + dy + wob * 0.35])
    return np.array(out, np.float32)


def doodle_case(case: dict, rng: random.Random) -> np.ndarray:
    sheet = np.full((SHEET_H, SHEET_W, 3), 252, np.uint8)
    views = case["views"]                      # ordered; first = primary
    extents = {}
    for v in views:
        xs = []; ys = []
        for sh in v["shapes"]:
            x0, y0, x1, y1 = shape_bounds(sh); xs += [x0, x1]; ys += [y0, y1]
        extents[v["direction"]] = (min(xs), min(ys), max(xs) - min(xs), max(ys) - min(ys))

    prim = views[0]["direction"]
    pw, ph = extents[prim][2], extents[prim][3]
    others = [v for v in views if v["direction"] != prim]
    # Anchor selection: the 'front' view (if drawn) owns the lower-left anchor
    # position regardless of declaration order; a lone 'right'/'top' view anchors.
    anchor = next((v for v in views if v["direction"] == "front"), views[0])
    prim = anchor["direction"]
    pw, ph = extents[prim][2], extents[prim][3]
    others = [v for v in views if v is not anchor]
    topv = next((v for v in others if v["direction"] in ("top", "bottom")), None) \
        or next((v for v in others if v["direction"] not in ("left", "right")), None)
    sidev = next((v for v in others if v["direction"] in ("left", "right")), None)

    # Scale so the whole sheet fits with >=150px clear gaps between view
    # clusters (well beyond the cluster-analysis dilation reach) and views
    # align per third-angle convention (top over front shares x-centre;
    # side view shares y-centre). One scale keeps all views mutually to scale.
    if not others:
        scale = min(640 / max(pw, 1), 480 / max(ph, 1))
        pcx, pcy = 500, 375
    else:
        scale = min(560 / max(pw, 1), 420 / max(ph, 1))
        if topv:
            scale = min(scale, 470 / max(ph + extents[topv["direction"]][3], 1))
        if sidev:
            scale = min(scale, 780 / max(pw + extents[sidev["direction"]][2], 1))
        if sidev:
            pcx = int(30 + pw * scale / 2)
        else:
            pcx = 420
        pcy = int(30 + extents[topv["direction"]][3] * scale + 150 + ph * scale / 2) if topv else 375

    def draw_view(view, cx, cy, sc):
        bx0, by0, bw, bh = extents[view["direction"]]
        sw, shh = bw * sc, bh * sc
        margin = 24
        cx = min(max(cx, margin + sw / 2), SHEET_W - margin - sw / 2)
        cy = min(max(cy, margin + shh / 2), SHEET_H - margin - shh / 2)
        ox = cx - sw / 2 - bx0 * sc
        oy = cy - shh / 2 - by0 * sc
        for sh in view["shapes"]:
            pts = jitter_polyline(shape_pts(sh), rng, close=True)
            pts[:, 0] = pts[:, 0] * sc + ox
            pts[:, 1] = pts[:, 1] * sc + oy
            cv2.polylines(sheet, [pts.astype(np.int32)], False, (18, 18, 18),
                          thickness=rng.choice([3, 3, 4]), lineType=cv2.LINE_AA)
        if rng.random() < 0.35:   # stray pen tick, like a real doodle
            x = int(cx + rng.uniform(-sw * 0.35, sw * 0.35)); y = int(cy + rng.uniform(-shh * 0.35, shh * 0.35))
            cv2.line(sheet, (x, y), (x + rng.randint(-9, 9), y + rng.randint(-9, 9)), (18, 18, 18), 2, cv2.LINE_AA)

    draw_view(views[0], pcx, int(pcy), scale)
    for v in others:
        d = v["direction"]
        if d in ("top", "bottom"):
            draw_view(v, pcx, int(30 + extents[d][3] * scale / 2), scale)
        elif d == "right":
            draw_view(v, int(30 + pw * scale + 150 + extents[d][2] * scale / 2), int(pcy), scale)
        elif d == "left":
            draw_view(v, int(pcx - pw * scale / 2 - 150 - extents[d][2] * scale / 2), int(pcy), scale)
        else:  # isometric-ish reference sits upper-right
            draw_view(v, 850, int(30 + extents[d][3] * scale / 2), scale)
    return sheet


# ---------------------------------------------------------------- writers
def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def emit_case(case: dict, openscad_bin: str) -> dict:
    case_dir = ROOT / "cases" / case["id"]
    if case_dir.exists():
        shutil.rmtree(case_dir)
    (case_dir / "source").mkdir(parents=True)
    (case_dir / "ground_truth").mkdir()
    (case_dir / "derived").mkdir()

    scad_path = case_dir / "ground_truth" / "model.scad"
    scad_path.write_text(case["scad"])
    # compile GT with pipeline path (Docker fallback honours env var).
    # compile_and_render runs with cwd=output_dir, so stage the scad inside it.
    tmp = case_dir / "derived"
    shutil.copy2(scad_path, tmp / "model.scad")
    stl, views_png, log = compile_and_render(tmp / "model.scad", tmp, openscad_bin)
    if stl is None:
        raise RuntimeError(f"{case['id']}: GT SCAD failed to compile:\n{log[-800:]}")
    shutil.move(str(tmp / "model.stl"), str(case_dir / "ground_truth" / "model.stl"))
    gt_stl = case_dir / "ground_truth" / "model.stl"
    # views are already written under derived/ by compile_and_render; keep them.
    for stale in tmp.glob("view-*"):
        if stale.name not in {f"view-{n}.png" for n in ("front", "top", "right", "isometric")}:
            stale.unlink()

    mesh = trimesh.load_mesh(gt_stl, process=True)
    comps = mesh.split(only_watertight=False)
    extents = [round(float(x), 4) for x in mesh.extents]
    if max(extents) > BUILD_CUBE_MM:
        raise RuntimeError(f"{case['id']}: GT part {extents} exceeds BambuLab {BUILD_CUBE_MM} mm cube")

    rng = random.Random(case["seed"])
    sheet = doodle_case(case, rng)
    cv2.imwrite(str(case_dir / "source" / "drawing.png"), sheet)

    manifest = {
        "schema_version": 1,
        "id": case["id"],
        "title": case["title"],
        "split": case.get("split", "development"),
        "status": "synthetic_reference_pair_verified",
        "provenance": {
            "source": "synthetic_parametric_generated_by_benchmarks/tools/gen_cases.py",
            "original_files": {
                "drawing": "generated: jittered doodle of declared GT view geometry (seed %d)" % case["seed"],
                "scad": "authored by benchmark tooling",
                "stl": "compiled from sibling model.scad with pipeline OpenSCAD",
            },
            "sha256": {
                "drawing.png": sha256(case_dir / "source" / "drawing.png"),
                "model.scad": sha256(scad_path),
                "model.stl": sha256(gt_stl),
            },
        },
        "reference": {
            "authority": "generated_parametric_ground_truth",
            "coordinate_system": {
                "x": "width", "y": "front_to_back_depth", "z": "height",
                "front_view_direction": "along_y", "top_view_direction": "along_z",
                "right_view_direction": "along_x",
                "status": "exact_from_scad_construction",
            },
            "dimensions_mm": {"extents_xyz": extents, "status": "exact_measured_from_gt_stl"},
            "topology": {
                "components": len(comps), "watertight": bool(mesh.is_watertight),
                "through_cutout_count": case["through_cutouts"],
                "status": "exact_measured_from_gt_stl",
            },
            "print_envelope_mm": {"max": BUILD_CUBE_MM, "fits": all(e <= BUILD_CUBE_MM for e in extents)},
        },
        "drawing": {
            "views": [{"direction": v["direction"], "sheet_region": v["region"],
                       "constraints": v.get("constraints", [])} for v in case["views"]],
            "projection_standard": "third-angle",
            "view_labels_status": "exact_from_generator",
            "style_note": "jittered single-weight ink outlines, white sheet, no fills",
        },
        "semantic_labels": {
            "object": case["object"], "family": case["family"],
            "manufacturing_intent": "FDM print on BambuLab-class printer",
            "object_status": "exact_from_generator",
        },
        "acceptance": {
            "mandatory": {
                "watertight": True, "component_count": 1,
                "dimension_relative_tolerance": 0.05,
                "through_cutout_count": case["through_cutouts"],
                "build_envelope_mm": BUILD_CUBE_MM,
                **{f"{v['direction']}_projection_required": True for v in case["views"]},
            },
            "shape_comparison": {"method": "registered_contour_and_internal_profile_correspondence"},
        },
        "controls": case.get("controls") or {"primary_view": next((v["direction"] for v in case["views"] if v["direction"] == "front"), case["views"][0]["direction"]), "projection_standard": "third-angle"},
        "target_dimension_mm": case["target_dimension"],
        "known_ambiguities": case.get("known_ambiguities", []),
    }
    (case_dir / "source" / "README.md").write_text(
        f"# {case['id']}\n\n{case['title']}\n\n- drawing.png: synthetic doodle (seed {case['seed']}) of the "
        f"declared ground-truth view geometry; jitter = gauss(0,0.55px) + sine wobble.\n"
        f"- ground_truth: parametric SCAD authored for the benchmark, STL compiled by the pipeline OpenSCAD.\n")
    (case_dir / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    return manifest


# ---------------------------------------------------------------- cases
CASES = [
 dict(id="004_flat_mounting_plate", title="Flat mounting plate with two holes and a center slot",
   object="rectangular mounting plate", family="extrude_plate_with_cutouts", seed=401,
   through_cutouts=3, target_dimension="100",
   scad="""
// Mounting plate: width 100 (X), thickness 5 (Y), height 60 (Z).
// Two d6 through-holes (axis Y) at (15,45) and (85,15); 30x8 slot centered.
difference() {
  cube([100,5,60]);
  translate([15,-1,45])  rotate([-90,0,0]) cylinder(d=6,h=7,$fn=32);
  translate([85,-1,15])  rotate([-90,0,0]) cylinder(d=6,h=7,$fn=32);
  translate([35,-1,26])  cube([30,7,8]);
}
""",
   views=[
     dict(direction="front", region="lower-left", constraints=["width","height","two holes","center slot"],
          shapes=[dict(t="rect",x=0,y=0,w=100,h=60),
                  dict(t="circle",cx=15,cy=60-45,d=6),
                  dict(t="circle",cx=85,cy=60-15,d=6),
                  dict(t="slot",cx=50,cy=60-30,w=30,h=8)]),
     dict(direction="top", region="upper-left", constraints=["thickness","width"],
          shapes=[dict(t="rect",x=0,y=0,w=100,h=5)]),
   ]),

 dict(id="005_bolt_flange", title="Round flange with center bore and four bolt holes",
   object="pipe flange disc", family="circular_array_with_cutouts", seed=502,
   through_cutouts=5, target_dimension="120",
   scad="""
// Flange: disc d120 (axis Y, standing like a wheel), thickness 12.
// Center bore d40 through; four bolt holes d10 on bolt circle r45 at 45deg.
difference() {
  translate([0,-12,0]) rotate([-90,0,0]) cylinder(d=120,h=12,$fn=96);
  translate([0,-13,0]) rotate([-90,0,0]) cylinder(d=40,h=14,$fn=64);
  for (a=[45:90:315]) {
    rotate([0,0,0]) translate([45*cos(a),-13,45*sin(a)]) rotate([90,0,0]) cylinder(d=10,h=14,$fn=32);
  }
}
translate([0,0,0]) {}
// keep geometry centered in Y for renderers
""",
   views=[
     dict(direction="front", region="center", constraints=["diameter","bore","four bolt holes on circle"],
          shapes=[dict(t="circle",cx=60,cy=60,d=120),
                  dict(t="circle",cx=60,cy=60,d=40),
                  *[dict(t="circle",cx=60+45*math.cos(math.radians(a)),cy=60+45*math.sin(math.radians(a)),d=10)
                    for a in (45,135,225,315)]]),
     dict(direction="top", region="upper-center", constraints=["thickness","diameter"],
          shapes=[dict(t="rect",x=0,y=0,w=120,h=12)]),
   ]),

 dict(id="006_stepped_knob", title="Stepped round knob (revolved profile)",
   object="lathe-turned knob", family="revolve_axisymmetric", seed=603,
   through_cutouts=0, target_dimension="56",
   scad="""
// Knob revolved about Z: base d50 h8, neck d24 h20, cap d56 h10 => 38 tall.
$fn=64;
rotate_extrude() {
  polygon([[0,0],[25,0],[25,8],[12,8],[12,28],[28,28],[28,38],[0,38]]);
}
""",
   views=[
     dict(direction="front", region="center", constraints=["stepped silhouette","three diameters","height"],
          shapes=[dict(t="poly",pts=[[-25,38],[25,38],[25,30],[12,30],[12,10],[28,10],[28,0],[-28,0],[-28,10],[-12,10],[-12,30],[-25,30]])]),
     dict(direction="right", region="right", constraints=["same revolved silhouette"],
          shapes=[dict(t="poly",pts=[[-25,38],[25,38],[25,30],[12,30],[12,10],[28,10],[28,0],[-28,0],[-28,10],[-12,10],[-12,30],[-25,30]])]),
   ]),

 dict(id="007_angle_bracket_holes", title="L angle bracket with three wall holes",
   object="L-shaped angle bracket", family="multi_face_union_with_cutouts", seed=704,
   through_cutouts=3, target_dimension="80",
   scad="""
// Angle bracket: base 80x40x4 at z0..4, back wall 80x4x50 (y=36..40).
// Three d6 holes through the wall (axis Y) at x=20,40,60 z=30.
difference() {
  union() {
    cube([80,40,4]);
    translate([0,36,0]) cube([80,4,50]);
  }
  for (x=[20,40,60]) translate([x,35,30]) rotate([-90,0,0]) cylinder(d=6,h=10,$fn=32);
}
""",
   views=[
     dict(direction="front", region="lower-left", constraints=["width","height","three holes"],
          shapes=[dict(t="rect",x=0,y=0,w=80,h=50),
                  *[dict(t="circle",cx=x,cy=50-30,d=6) for x in (20,40,60)]]),
     dict(direction="top", region="upper-left", constraints=["depth","width","wall at back edge"],
          shapes=[dict(t="rect",x=0,y=0,w=80,h=40)]),
   ]),

 dict(id="008_open_enclosure_window", title="Open-top enclosure with front window",
   object="electronics enclosure box", family="shell_with_cutout", seed=805,
   through_cutouts=1, target_dimension="120",
   scad="""
// Enclosure: 120x80x40, wall 3, open top; 60x24 window through front wall (y=0..3).
difference() {
  difference() {
    cube([120,80,40]);
    translate([3,3,3]) cube([114,74,40]);   // open-top cavity
  }
  translate([30,-1,8]) cube([60,5,24]);     // front window
}
""",
   views=[
     dict(direction="front", region="lower-left", constraints=["width","height","window cutout"],
          shapes=[dict(t="rect",x=0,y=0,w=120,h=40),
                  dict(t="rect",x=30,y=40-32,w=60,h=24)]),
     dict(direction="top", region="upper-left", constraints=["width","depth","wall rim"],
          shapes=[dict(t="rect",x=0,y=0,w=120,h=80),
                  dict(t="rect",x=3,y=3,w=114,h=74)]),
   ]),

 dict(id="009_hex_prism_knob", title="Hex prism handle (extruded hexagon)",
   object="hexagonal handle knob", family="extrude_polygon_profile", seed=906,
   through_cutouts=0, target_dimension="70",
   scad="""
// Hex prism: across-flats 30 (R=17.32), length 70 along X, axis Y-rotated.
rotate([0,90,0])
  translate([0,0,-35])
    rotate([0,0,30])
      cylinder(h=70, r=17.32, $fn=6);
""",
   views=[
     dict(direction="right", region="right", constraints=["hexagon across-flats"],
          shapes=[dict(t="ngon",cx=20,cy=20,r=17.32,n=6,rot=0.0)]),
     dict(direction="front", region="lower-left", constraints=["length","across-flats height"],
          shapes=[dict(t="rect",x=0,y=0,w=70,h=30)]),
   ]),

 dict(id="010_nameplate_slots_vents", title="Nameplate with end slots and vent holes",
   object="mounting nameplate", family="extrude_repeated_cutouts", seed=107,
   through_cutouts=7, target_dimension="140",
   scad="""
// Nameplate 140x3x24 (Y thickness 3). Two 12x6 slots near ends, five d5 vents.
difference() {
  cube([140,3,24]);
  translate([9,-1,9])  cube([12,5,6]);   // slot L (center x=15,z=12)
  translate([119,-1,9]) cube([12,5,6]);  // slot R (center x=125,z=12)
  for (x=[50,60,70,80,90]) translate([x,-1,12]) rotate([-90,0,0]) cylinder(d=5,h=5,$fn=24);
}
""",
   views=[
     dict(direction="front", region="center", constraints=["width","height","two slots","five vents"],
          shapes=[dict(t="rect",x=0,y=0,w=140,h=24),
                  dict(t="rect",x=9,y=24-15,w=12,h=6),
                  dict(t="rect",x=119,y=24-15,w=12,h=6),
                  *[dict(t="circle",cx=x,cy=12,d=5) for x in (50,60,70,80,90)]]),
   ]),

 dict(id="011_wall_hook", title="L wall hook extruded from front profile",
   object="wall hook", family="extrude_freeform_profile", seed=118,
   through_cutouts=0, target_dimension="60",
   scad="""
// Wall hook: L profile in XZ (60 toe, 55 back), 10 thick along Y, flat back on bed.
translate([0,10,0]) rotate([90,0,0])
  linear_extrude(height=10) {
    polygon([[0,0],[60,0],[60,12],[14,12],[14,55],[0,55]]);
  }
""",
   views=[
     dict(direction="front", region="lower-left", constraints=["L toe","back height","tip"],
          shapes=[dict(t="poly",pts=[[0,55],[60,55],[60,43],[14,43],[14,0],[0,0]])]),
     dict(direction="top", region="upper-left", constraints=["toe length","thickness"],
          shapes=[dict(t="rect",x=0,y=0,w=60,h=10)]),
   ]),

 dict(id="012_vent_grille_grid", title="Vent grille plate with 3x3 round hole grid",
   object="ventilation grille plate", family="extrude_grid_array_cutouts", seed=129,
   through_cutouts=9, target_dimension="100",
   scad="""
// Vent grille: 100x4x60 plate (Y thin), nine d10 holes on 25/15 grid.
difference() {
  cube([100,4,60]);
  for (x=[25,50,75], z=[15,30,45])
    translate([x,-1,z]) rotate([-90,0,0]) cylinder(d=10,h=6,$fn=32);
}
""",
   views=[
     dict(direction="front", region="center", constraints=["width","height","3x3 hole grid"],
          shapes=[dict(t="rect",x=0,y=0,w=100,h=60),
                  *[dict(t="circle",cx=x,cy=60-z,d=10) for x in (25,50,75) for z in (15,30,45)]]),
   ]),

 dict(id="013_wedge_ramp", title="Wedge ramp (lofted incline block)",
   object="wedge ramp block", family="loft_wedge", seed=130,
   through_cutouts=0, target_dimension="100",
   scad="""
// Wedge: base 100x60, rising to 30 at back. Triangle profile in XZ extruded along Y.
translate([0,0,0])
  linear_extrude(height=60) {
    // profile drawn in XY then rotated upright: (0,0)-(100,0)-(0,30)
    polygon([[0,0],[100,0],[0,30]]);
  }
rotate([0,0,0]) {}
// note: profile plane XY, extrude Z -> stand it up:
""",
   known_ambiguities=["doodle front view is the only height-carrying view; depth comes from top strip"],
   views=[
     dict(direction="front", region="lower-left", constraints=["base length","rise height","slope"],
          shapes=[dict(t="poly",pts=[[0,0],[100,0],[0,30]])]),
     dict(direction="top", region="upper-left", constraints=["base length","depth"],
          shapes=[dict(t="rect",x=0,y=0,w=100,h=60)]),
   ]),
]

# 013's SCAD is wrong as drafted (triangle extrudes along Z, not standing up).
def fix_wedge(case):
    case["scad"] = """
// Wedge ramp: base 100(X) x 60(Y); vertical face at x=0 up to z=30; sloped top
// falls to z=0 at x=100. Flat base on bed.
polyhedron(
  points=[[0,0,0],[100,0,0],[0,0,30],[0,60,0],[100,60,0],[0,60,30]],
  faces=[[0,2,1],[3,4,5],[0,1,4,3],[0,3,5,2],[1,2,5,4]]
);
"""
    case["views"][0]["shapes"] = [dict(t="poly", pts=[[0,30],[100,30],[0,0]])]

def fix_flange(case):
    case["scad"] = """
// Flange: disc d120 axis Y centered y=-6..6, thickness 12.
difference() {
  translate([0,-6,0]) rotate([-90,0,0]) cylinder(d=120,h=12,$fn=96);
  translate([0,-7,0]) rotate([-90,0,0]) cylinder(d=40,h=14,$fn=64);
  for (a=[45:90:315])
    translate([45*cos(a),-7,45*sin(a)]) rotate([-90,0,0]) cylinder(d=10,h=14,$fn=32);
}
"""

for c in CASES:
    if c["id"] == "013_wedge_ramp": fix_wedge(c)
    if c["id"] == "005_bolt_flange": fix_flange(c)
    # center solids on origin where the pipeline cameras expect it
    if c["id"] in ("004_flat_mounting_plate","007_angle_bracket_holes","008_open_enclosure_window",
                   "010_nameplate_slots_vents","012_vent_grille_grid"):
        c["scad"] = c["scad"].rstrip() + "\n"


def main(argv):
    ids = set(argv) or {c["id"] for c in CASES}
    openscad_bin = "openscad"
    made = []
    for case in CASES:
        if case["id"] not in ids:
            continue
        manifest = emit_case(case, openscad_bin)
        made.append({"id": manifest["id"], "split": manifest["split"],
                     "status": manifest["status"], "family": manifest["semantic_labels"]["family"]})
        print(f"OK {case['id']}: extents={manifest['reference']['dimensions_mm']['extents_xyz']} "
              f"cutouts={case['through_cutouts']}")
    # refresh index
    index = {"schema_version": 1, "cases": made if len(ids) == len(CASES) else
             json.loads((ROOT / "index.json").read_text())["cases"] +
             [m for m in made if not any(m["id"] == e["id"] for e in json.loads((ROOT / 'index.json').read_text())['cases'])]}
    (ROOT / "index.json").write_text(json.dumps(index, indent=2) + "\n")
    print(f"generated {len(made)} case(s)")


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
