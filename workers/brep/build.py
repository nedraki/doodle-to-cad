"""One build per isolated Python 3.12 process. Never import in the web process."""
import json
import math
from pathlib import Path
import sys
import time
from importlib.metadata import version

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from doodle_to_cad.brep_recipe import validate_recipe


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
        if kind == "box":
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
            path = sm.create_arc(tuple(op["origin"]), op["bend_radius"], 0, op["angle"])
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
            raise ValueError(f"{check['id']}: required connection failed: {exc}") from exc
        connections.append({"id": check["id"], "overlap_mm3": retained_volume, "passed": True})
    volume = body.volume()
    if not math.isfinite(volume) or volume <= 0:
        raise ValueError("Invalid solid volume")
    poly = sm.tessellate(body, chord_height_tolerance=0.05)
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
    if len(mesh.split()) != 1 or max(mesh.extents) > 256.001 or abs(mesh.bounds[0, 2]) > 0.001:
        raise ValueError(
            "Expected one connected part on Z=0 within the 256 mm build cube; "
            f"components={len(mesh.split())}, minimum_z_mm={mesh.bounds[0, 2]:.6g}, "
            f"extents_mm={mesh.extents.tolist()}")
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
    if len(imported) != 1 or abs(imported[0].volume()-volume)/volume > 1e-5:
        raise ValueError("USD round-trip volume check failed")
    reloaded = trimesh.load(output / "model.stl", force="mesh")
    if not reloaded.is_watertight or not reloaded.is_winding_consistent:
        raise ValueError("Exported STL validation failed")
    diagnostics = {"backend": "usd-brep", "version": "1.0.0", "recipe_version": recipe["version"], "solid_volume_mm3": volume,
                   "mesh_volume_mm3": mesh.volume, "extents_mm": mesh.extents.tolist(),
                   "bounds_mm": mesh.bounds.tolist(), "watertight": True, "winding_consistent": True,
                   "euler_number": int(mesh.euler_number), "triangles": len(mesh.faces),
                   "usd_roundtrip": True, "operations": history, "connections": connections,
                   "build_seconds": round(time.monotonic()-started, 3)}
    (output / "diagnostics.json").write_text(json.dumps(diagnostics, indent=2))


if __name__ == "__main__":
    try:
        build(Path(sys.argv[1]), Path(sys.argv[2]))
    except Exception as exc:
        print(f"BRep build failed: {exc}", file=sys.stderr)
        sys.exit(1)
