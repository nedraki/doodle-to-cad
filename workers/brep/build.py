"""One build per isolated Python 3.12 process. Never import in the web process."""
import json
import math
import os
from pathlib import Path
import sys
import time
from importlib.metadata import version

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from doodle_to_cad.brep_recipe import validate_recipe
from doodle_to_cad.build_contract import BuildError


def arc_curve(sm, center, radius, start, end):
    """Keep periodic angles in the kernel range without changing the arc."""
    sweep=end-start
    normalized_end=end % 360 or 360
    return sm.create_arc(center,radius,normalized_end-sweep,normalized_end)


def build(source, output):
    started = time.monotonic()
    if sys.version_info[:2] != (3, 12) or version("usd-brep") != "1.0.0":
        raise RuntimeError("Worker requires Python 3.12 and usd-brep==1.0.0")
    import usd_brep as sm
    import numpy as np
    import trimesh

    recipe, operations = validate_recipe(json.loads(source.read_text()))
    bodies, history = {}, []
    for op in operations:
        kind = op["kind"]
        if kind == 'shell':
            source_body=bodies[op['body']].copy()
            lo,hi=sm.brep_bounding_box(source_body);thickness=op['thickness']
            if thickness>=min((hi[0]-lo[0])/2,(hi[1]-lo[1])/2,hi[2]-lo[2])-.001:
                raise ValueError(f"{op['id']}: thickness removes the required interior or floor")
            top=[]
            for face in source_body.faces():
                lower,upper=sm.face_bounding_box(face,tight=True)
                if abs(upper[2]-lower[2])<.001 and abs(upper[2]-hi[2])<.001:top.append(face)
            if len(top)!=1:raise ValueError(f"{op['id']}: shell requires one planar highest face for its opening")
            try:
                body=sm.shell_brep(source_body,-thickness,faces_to_shell=top)
            except Exception as exc:
                raise ValueError(f"{op['id']}: inward shell failed at thickness {thickness:g} mm: {exc}") from exc
            shell_lo,shell_hi=sm.brep_bounding_box(body)
            if max(abs(a-b) for a,b in zip((*lo,*hi),(*shell_lo,*shell_hi)))>.001:
                raise ValueError(f"{op['id']}: shell changed protected outer bounds")
        elif kind == 'loft':
            rectangle,circle=op['profiles'];x,y,z=rectangle['center'];w,h=rectangle['width']/2,rectangle['height']/2
            points=[(x+w,y+h,z),(x-w,y+h,z),(x-w,y-h,z),(x+w,y-h,z),(x+w,y+h,z)]
            curves=[sm.create_line_segment(a,b) for a,b in zip(points,points[1:])]
            curves += [arc_curve(sm,tuple(circle['center']),circle['radius'],angle,angle+90) for angle in [45,135,225,315]]
            try:
                body=sm.create_skin_primitive([4,4],curves,degree=1,cap_ends=True)
            except Exception as exc:
                raise ValueError(f"{op['id']}: rectangular-to-round loft failed: {exc}") from exc
        elif kind == 'sweep':
            from doodle_to_cad.planar_sweep import tangent
            from doodle_to_cad.planar_profile import endpoints
            path=[];z=op['section_height']/2
            for edge in op['path']:
                if edge['kind']=='line':
                    path.append(sm.create_line_segment((*edge['start'],z),(*edge['end'],z)))
                else:
                    path.append(arc_curve(sm,(*edge['center'],z),edge['radius'],edge['start_angle'],edge['end_angle']))
            start=endpoints(op['path'][0])[0];t=tangent(op['path'][0]);n=[t[1],-t[0]]
            points=[(start[0]+u*n[0],start[1]+u*n[1],v) for u,v in [(-op['section_width']/2,0),(op['section_width']/2,0),(op['section_width']/2,2*z),(-op['section_width']/2,2*z),(-op['section_width']/2,0)]]
            profile=[sm.create_line_segment(a,b) for a,b in zip(points,points[1:])]
            try:
                body=sm.sweep_along_planar_path(profile,path,move_profile=True,cap_ends=sm.CapEnds.BOTH)
            except Exception as exc:
                raise ValueError(f"{op['id']}: rectangular sweep failed: {exc}") from exc
            sm.translate(body,tuple(op['origin']))
        elif kind == 'extrude':
            curves=[]
            for loop in op['loops']:
                for edge in loop:
                    if edge['kind']=='line':
                        curves.append(sm.create_line_segment((*edge['start'],0),(*edge['end'],0)))
                    else:
                        curves.append(arc_curve(sm,(*edge['center'],0),edge['radius'],edge['start_angle'],edge['end_angle']))
            body=sm.linear_sweep(curves,(0,0,op['direction']),op['depth'],cap_ends=True)
            sm.translate(body,tuple(op['origin']))
        elif kind == "box":
            body = sm.create_box(tuple(op["origin"]), *op["size"])
        elif kind == "cylinder":
            body = sm.create_cylinder((0, 0, 0), op["radius"], op["height"])
            if op["axis"] == "x":
                sm.rotate(body, (0, 0, 0), (0, 1, 0), 90)
            elif op["axis"] == "y":
                sm.rotate(body, (0, 0, 0), (1, 0, 0), -90)
            sm.translate(body, tuple(op["origin"]))
        elif kind == "rotate":
            body = bodies[op["body"]].copy()
            axis = tuple(1 if name == op["axis"] else 0 for name in "xyz")
            sm.rotate(body, tuple(op["origin"]), axis, op["angle"])
        elif kind in ("union", "difference"):
            operation = sm.boolean_union if kind == "union" else sm.boolean_difference
            body = operation(bodies[op["left"]].copy(), bodies[op["right"]].copy())
        elif kind in ("fillet", "chamfer"):
            body = bodies[op["body"]].copy()
            if kind == "chamfer":
                sm.chamfer_fillet(body, op["radius"])
            else:
                edges = body.edges()
                if op["selector"] != "all":
                    axis = "xyz".index(op["selector"][-1])
                    selected = []
                    for edge in edges:
                        lo, hi = sm.edge_bounding_box(edge, tight=True)
                        if hi[axis]-lo[axis] > 1e-6 and all(abs(hi[i]-lo[i]) < 1e-6 for i in range(3) if i != axis):
                            selected.append(edge)
                    edges = selected
                if not edges:
                    raise ValueError(f"{op['id']}: selector matched no edges")
                sm.fillet_edges(body, edges, radius=op["radius"])
        elif kind == "arc_pipe":
            path = arc_curve(sm,tuple(op["origin"]), op["bend_radius"], 0, op["angle"])
            body = sm.pipe_sweep(path, radius=op["radius"], cap_ends=True)
        if not body.is_manifold_solid():
            raise ValueError(f"{op['id']}: kernel produced an invalid solid")
        bodies[op["id"]] = body
        history.append({"id": op["id"], "kind": kind, "faces": len(body.faces())})
    body = bodies[recipe["output"]]
    connections = []
    for check in recipe.get("constraints", []):
        try:
            overlap = sm.boolean_intersection(bodies[check["left"]].copy(), bodies[check["right"]].copy())
            overlap_volume = abs(overlap.volume()) if overlap is not None else 0
            if not math.isfinite(overlap_volume) or overlap_volume < check["min_volume_mm3"]:
                raise ValueError(f"overlap {overlap_volume:.6g} mm3 is too small")
            # Later cuts must not remove the declared connection.
            retained = sm.boolean_intersection(overlap.copy(), body.copy())
            retained_volume = abs(retained.volume()) if retained is not None else 0
            if not math.isfinite(retained_volume) or retained_volume < check["min_volume_mm3"]:
                raise ValueError("final body removed the required connection")
        except Exception as exc:
            raise BuildError("connection_failed", f"{check['id']}: required connection failed between {check['left']} and {check['right']} (required overlap {check['min_volume_mm3']} mm3): {exc}") from exc
        connections.append({"id": check["id"], "overlap_mm3": retained_volume, "passed": True})
    # The API defaults to 1e-3 relative integration accuracy. Request accuracy
    # tighter than the 1e-5 export gate on both sides of the comparison.
    volume = body.volume(relative_accuracy=1e-8)
    if not math.isfinite(volume) or volume <= 0:
        raise ValueError("Invalid solid volume")
    # Loft faces can span the full transition; bound triangle length so
    # intermediate sections retain the profile correspondence.
    mesh_options={'max_edge_length':2.0} if any(o['kind']=='loft' for o in operations) else {}
    poly = sm.tessellate(body, chord_height_tolerance=0.05, **mesh_options)
    arrays = poly.to_mesh_arrays()
    stream, triangles, cursor = arrays["faces"], [], 0
    while cursor < len(stream):
        count = stream[cursor]
        if count != 3:
            raise ValueError("Expected triangle tessellation")
        triangles.append(stream[cursor+1:cursor+4])
        cursor += 4
    mesh = trimesh.Trimesh(vertices=arrays["points"], faces=triangles, process=True)
    # Do not repair winding: known kernel defects must fail visibly.
    if not np.isfinite(mesh.vertices).all() or not mesh.is_watertight or not mesh.is_winding_consistent or mesh.volume <= 0:
        raise ValueError("Independent mesh validation failed")
    components = len(mesh.split())
    if components != 1:
        raise BuildError("disconnected_output", f"Expected one connected part; components={components}")
    maximum = float(os.getenv('DOODLE_BREP_MAX_DIMENSION', '256'))
    if not math.isfinite(maximum) or not 1 <= maximum <= 256:
        raise ValueError('Invalid build maximum dimension')
    if max(mesh.extents) > min(256.001, maximum + .5) or abs(mesh.bounds[0, 2]) > 0.001:
        raise BuildError("placement_failed",
            f"Expected Z=0 and extents within requested maximum {maximum:g} mm; "
            f"minimum_z_mm={mesh.bounds[0, 2]:.6g}, extents_mm={mesh.extents.tolist()}")
    if abs(mesh.volume-volume)/volume > 0.02:
        raise ValueError("Mesh volume differs from solid by more than 2%")
    mesh.export(str(output / "model.stl"))
    # USDA metadata is text, so no second/conflicting pxr runtime is needed.
    usd = output / "model.usda"
    sm.usd.export_brep(body.copy(), str(usd))
    text = usd.read_text()
    header, rest = text.split("\n", 1)
    if rest.lstrip().startswith("("):
        start = rest.index("(") + 1
        rest = rest[:start] + '\n    metersPerUnit = 0.001\n    upAxis = "Z"\n' + rest[start:]
    else:
        rest = '(\n    metersPerUnit = 0.001\n    upAxis = "Z"\n)\n' + rest
    usd.write_text(header + "\n" + rest)
    imported = sm.usd.import_breps(str(usd))
    if len(imported) != 1 or abs(imported[0].volume(relative_accuracy=1e-8)-volume)/volume > 1e-5:
        raise ValueError(f"USD round-trip volume check failed: original_volume_mm3={volume:.12g}; reloaded_volumes_mm3={[item.volume(relative_accuracy=1e-8) for item in imported]}")
    reloaded = trimesh.load(output / "model.stl", force="mesh")
    if not reloaded.is_watertight or not reloaded.is_winding_consistent:
        raise ValueError("Exported STL validation failed")
    from selection_catalog import catalog
    try:
        selection_catalog = catalog(sm, body, bodies, operations, recipe['output'], mesh)
    except Exception as exc:
        # Selection is optional; retain a checked part and expose the failure.
        selection_catalog = {'version': 1, 'status': 'unavailable', 'targets': [], 'reason': str(exc)}
    diagnostics = {"selection_catalog": selection_catalog, "backend": "usd-brep", "version": "1.0.0", "recipe_version": recipe["version"], "solid_volume_mm3": volume,
                   "mesh_volume_mm3": mesh.volume, "extents_mm": mesh.extents.tolist(),
                   "bounds_mm": mesh.bounds.tolist(), "watertight": True, "winding_consistent": True,
                   "euler_number": int(mesh.euler_number), "triangles": len(mesh.faces),
                   "usd_roundtrip": True, "volume_relative_accuracy": 1e-8, "usd_volume_mm3": imported[0].volume(relative_accuracy=1e-8), "operations": history, "connections": connections,
                   "build_seconds": round(time.monotonic()-started, 3)}
    (output / "diagnostics.json").write_text(json.dumps(diagnostics, indent=2))


if __name__ == "__main__":
    try:
        build(Path(sys.argv[1]), Path(sys.argv[2]))
    except Exception as exc:
        (Path(sys.argv[2]) / "construction-error.json").write_text(json.dumps({
            "code": getattr(exc, "code", "build_failed"), "message": str(exc)}))
        print(f"BRep build failed: {exc}", file=sys.stderr)
        sys.exit(1)
