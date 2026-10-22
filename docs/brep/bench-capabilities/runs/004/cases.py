"""Trusted-recipe capability cases for issue #82 (human-authored, no LLM).

Each case is a hand-written Direct-BRep recipe exercising one advertised
capability, with (a) expected measurements for the initial build and (b) a
PARAMETER-ONLY edit plus expectations about what changes and what is
preserved. Protected dimensions are checked with a tight tolerance; changed
dimensions must move to the requested value. An edit that silently breaks a
protected dimension fails the case even if the build succeeds.

Author effort is recorded (operation count, parameter count, iteration
count per first valid build) because the issue asks for the cost of the
trusted path.
"""

def box(i, x, y, z, **kw):
    return {"id": i, "kind": "box", "origin": [0, 0, 0], "size": [x, y, z], **kw}

def cyl(i, o, ax, r, h, **kw):
    return {"id": i, "kind": "cylinder", "origin": o, "axis": ax, "radius": r, "height": h, **kw}

def diff(i, left, right, **kw):
    return {"id": i, "kind": "difference", "left": left, "right": right, **kw}

def uni(i, l, r, **kw):
    return {"id": i, "kind": "union", "left": l, "right": r, **kw}

def _recipe(name, params, ops, output):
    for k, op in enumerate(ops):
        op.setdefault("frame", "world")
        # worker contract (construction_recipe.validate_v2): depends_on must
        # equal the op's own left/right/body references, nothing else.
        op["depends_on"] = [op[key] for key in ("left", "right", "body") if key in op]
        op.setdefault("evidence", ["e1"])
    return {
        "version": 2, "units": "mm", "name": name,
        "parameters": {n: {"value": v, "min": lo, "max": hi, "label": n.replace("_", " "), "unit": "mm"}
                       for n, v, lo, hi in params},
        "operations": ops, "output": output,
        "frames": {"world": {"origin": [0, 0, 0], "x": "width", "y": "depth", "z": "height"}},
        "bodies": [{"id": "part", "output": output}],
        "evidence": {"observed": [{"id": "e1", "text": "trusted human-authored recipe (issue #82)"}],
                     "inferred": [], "assumptions": [], "unresolved": []},
        "constraints": [],
    }

CASES = [
    {
        "id": "c1_fillet_enclosure", "capability": "fillet (vertical corner rounding) + preserved through-holes",
        "params": [("length", 120, 60, 200), ("width", 80, 40, 160), ("height", 40, 20, 80),
                   ("fillet_r", 6, 1, 20), ("hole_d", 8, 2, 20)],
        "ops": [
            box("slab", "length", "width", "height"),
            cyl("h1", ["length/4", 0, "height/2"], "y", "hole_d/2", "width"),
            cyl("h2", ["length*3/4", 0, "height/2"], "y", "hole_d/2", "width"),
            diff("drilled", "slab", "h1"), diff("drilled2", "drilled", "h2"),
            {"id": "rounded", "kind": "fillet", "body": "drilled2", "radius": "fillet_r", "selector": "outer_vertical"},
        ], "output": "rounded",
        "initial": {"extents": [120.0, 80.0, 40.0], "genus": 2, "watertight": True, "components": 1,
                    "volume_mm3": (120*80*40 - 2*3.14159265*4*4*80 - 0, 0.05)},
        "edit": {"param": "fillet_r", "new": 12.0,
                 "protected": {"extents": [120.0, 80.0, 40.0], "genus": 2},
                 "changed_note": "corner arcs deepen; volume drops"},
        "author_ops": 6, "author_params": 5,
    },
    {
        "id": "c2_chamfer_block", "capability": "chamfer (edge bevel) — documents all-edges constraint",
        "params": [("length", 60, 30, 120), ("width", 40, 20, 80), ("height", 25, 10, 50),
                   ("chamfer_c", 1.5, 0.5, 5)],
        "ops": [box("slab", "length", "width", "height"),
                {"id": "bevelled", "kind": "chamfer", "body": "slab", "radius": "chamfer_c"}],
        "output": "bevelled",
        "initial": {"extents": [60.0, 40.0, 25.0], "extents_tol": 0.02,
                    "genus": 0, "watertight": True, "components": 1,
                    "chamfer_45_facets": 12, "volume_less_than": 60*40*25},
        "edit": {"param": "chamfer_c", "new": 3.0,
                 "protected": {"genus": 0},
                 "changed_note": "bbox preserved; 45-degree chamfer setback is chamfer_c/sqrt(2), matching the kernel radius convention"},
        "author_ops": 2, "author_params": 4,
        "constraint_note": "chamfer applies to ALL edges (build.py chamfer_fillet); hole-inlet chamfer unsupported",
    },
    {
        "id": "c3_sweep_handle", "capability": "curved sweep (bent bar, tangent legs, rectangular section)",
        "params": [("bend_r", 30, 10, 80), ("leg", 20, 5, 60), ("sec_w", 8, 2, 20), ("sec_h", 3, 1, 10)],
        "ops": [
            {"id": "b1", "kind": "sweep", "origin": [0, 0, 0],
             "plane": "xy", "frame_rule": "normal_to_path_z_up",
             "section_width": "sec_w", "section_height": "sec_h",
             "path": [
                 {"kind": "line", "start": ["bend_r", "-leg"], "end": ["bend_r", 0]},
                 {"kind": "arc", "center": [0, 0], "radius": "bend_r", "start_angle": 0, "end_angle": 180},
                 {"kind": "line", "start": ["-bend_r", 0], "end": ["-bend_r", "-leg"]},
             ]},
        ], "output": "b1",
        "initial": {"extents": [68.0, 54.0, 3.0], "extents_tol": 0.35, "genus": 0,
                    "watertight": True, "components": 1,
                    "volume_mm3": (24.0 * (2*20 + 3.14159265*30), 0.05)},
        "edit": {"param": "bend_r", "new": 40.0,
                 "protected": {"extents_z": 3.0},
                 "changed": {"extents_x": 88.0, "relation": "extents_x == 2*bend_r + sec_w"},
                 "changed_note": "bend radius requested 30->40; section 8x3 and leg 20 preserved"},
        "author_ops": 1, "author_params": 4,
    },
    {
        "id": "c4_loft_transition", "capability": "loft (rectangular end to circular end)",
        "params": [("rect", 40, 10, 100), ("circ_r", 30, 10, 60), ("span", 30, 5, 80)],
        "ops": [
            {"id": "skin", "kind": "loft", "plane": "xy",
             "correspondence": "rectangle_corners_to_circle_diagonals",
             "profiles": [
                 {"shape": "rectangle", "width": "rect", "height": "rect", "center": [0, 0, 0]},
                 {"shape": "circle", "radius": "circ_r", "center": [0, 0, "span"]},
             ]},
        ], "output": "skin",
        "initial": {"extents": [60.0, 60.0, 30.0], "extents_tol": 0.35, "genus": 0,
                    "watertight": True, "components": 1, "volume_mm3": None},
        "edit": {"param": "circ_r", "new": 34.0,
                 "protected": {"extents_z": 30.0},
                 "changed": {"extents_x": 68.0},
                 "changed_note": "circular end grows to R34; rectangular end and span preserved"},
        "author_ops": 1, "author_params": 3,
    },
    {
        "id": "c5_shell_tray", "capability": "shell (open-top tray, protected outer faces)",
        "params": [("length", 100, 50, 200), ("width", 70, 35, 140), ("height", 25, 10, 60),
                   ("wall", 3, 1, 8), ("fillet_r", 5, 1, 15)],
        "ops": [
            box("slab", "length", "width", "height"),
            {"id": "rounded", "kind": "fillet", "body": "slab", "radius": "fillet_r", "selector": "outer_vertical"},
            {"id": "tray", "kind": "shell", "body": "rounded", "thickness": "wall",
             "opening": "top", "preserve": "outer"},
        ], "output": "tray",
        "initial": {"extents": [100.0, 70.0, 25.0], "genus": 0, "watertight": True, "components": 1,
                    "volume_mm3": (100*70*25 - (100-6)*(70-6)*(25-3), 0.02)},
        "edit": {"param": "wall", "new": 2.0,
                 "protected": {"extents": [100.0, 70.0, 25.0]},
                 "changed_note": "wall 3->2: volume must approach 100*70*25-96*66*23 (~175000-145728)"},
        "author_ops": 3, "author_params": 5,
    },
    {
        "id": "c6_combined", "capability": "feature coexistence: fillet + shell + window pierce",
        "params": [("length", 100, 50, 200), ("depth", 60, 30, 120), ("height", 30, 15, 60),
                   ("wall", 2.5, 1, 6), ("fillet_r", 5, 1, 12), ("win_d", 10, 4, 24)],
        "ops": [
            box("slab", "length", "depth", "height"),
            {"id": "rounded", "kind": "fillet", "body": "slab", "radius": "fillet_r", "selector": "outer_vertical"},
            {"id": "tray", "kind": "shell", "body": "rounded", "thickness": "wall",
             "opening": "top", "preserve": "outer"},
            cyl("win", ["length/2", 0, "height/2"], "y", "win_d/2", "depth"),
            diff("final", "tray", "win"),
        ], "output": "final",
        "initial": {"extents": [100.0, 60.0, 30.0], "extents_tol": 0.05, "genus": 2,
                    "watertight": True, "components": 1, "volume_mm3": None},
        "edit": {"param": "win_d", "new": 16.0,
                 "protected": {"extents": [100.0, 60.0, 30.0], "genus": 2},
                 "changed_note": "window grows; two wall tunnels remain, one per pierced wall"},
        "author_ops": 5, "author_params": 6,
    },
    {
        "id": "c7_chamfer_stress", "capability": "chamfer after drilling (all-edges stress; may honestly fail)",
        "params": [("side", 40, 20, 80), ("thick", 10, 5, 20), ("hole_d", 6, 2, 12), ("chamfer_c", 1.0, 0.5, 3)],
        "ops": [
            box("slab", "side", "side", "thick"),
            cyl("h1", ["side/4", "side/4", 0], "z", "hole_d/2", "thick"),
            cyl("h2", ["side*3/4", "side*3/4", 0], "z", "hole_d/2", "thick"),
            diff("d1", "slab", "h1"), diff("d2", "d1", "h2"),
            {"id": "bev", "kind": "chamfer", "body": "d2", "radius": "chamfer_c"},
        ], "output": "bev",
        "initial": {"extents": None, "genus": 2, "watertight": True, "components": 1, "volume_mm3": None},
        "exploratory": True,
        "edit": None, "author_ops": 6, "author_params": 4,
    },
]
