"""Independent section measurements for the frozen human-authored cases.

All dimensions are in mm. The 0.15 mm tolerance covers mesh tessellation,
not parameter drift. Near-end loft sections are 0.01 mm inside the end caps.
"""
import numpy as np
import trimesh


def feature_checks(path, case, recipe):
    checks = []
    def check(name, got, want, tolerance=0.15):
        checks.append({"check": name, "got": float(got), "expected": float(want),
                       "tolerance": tolerance, "pass": bool(abs(got-want) <= tolerance)})
    try:
        mesh = trimesh.load(path, force="mesh")
        p = {k: v["value"] for k, v in recipe["parameters"].items()}
        def loops(axis, value):
            normal = np.eye(3)[axis]
            section = mesh.section(plane_normal=normal, plane_origin=normal*value)
            if section is None:
                raise ValueError("missing section")
            return sorted(section.discrete, key=lambda x: np.prod(np.ptp(np.delete(x, axis, axis=1), axis=0)), reverse=True)
        def bounds(points):
            return np.ptp(points, axis=0)
        def radius(points, axes=(0,1)):
            xy = points[:, axes]
            coefficients = np.linalg.lstsq(np.c_[2*xy, np.ones(len(xy))], (xy*xy).sum(axis=1), rcond=None)[0]
            return np.sqrt(coefficients[2] + (coefficients[:2]**2).sum())
        name = case["id"][:2]
        if name in ("c1", "c2", "c5", "c6"):
            for i, key in enumerate(("length", "depth" if name == "c6" else "width", "height")):
                check("protected_"+key, mesh.extents[i], p[key], .05)
        if name == "c2":
            for z in (.1, .5):
                span = bounds(loops(2,z)[0])
                for axis, key in enumerate(("length", "width")):
                    check(f"chamfer_{key}_at_{z}", (p[key]-span[axis])/2+z, p["chamfer_c"] / np.sqrt(2))
        elif name == "c3":
            points = loops(2,0)[0]
            top = points[points[:,1] > 1]
            radii = np.linalg.norm(top[:,:2],axis=1)
            check("bend_radius", (radii.max()+radii.min())/2, p["bend_r"])
            check("section_width", radii.max()-radii.min(), p["sec_w"])
            check("section_height", mesh.extents[2], p["sec_h"])
            check("leg_length", -mesh.bounds[0,1], p["leg"])
        elif name == "c4":
            bottom, top = loops(2,.01)[0], loops(2,p["span"]-.01)[0]
            for axis in (0,1):
                check(f"rectangle_{axis}", bounds(bottom)[axis], p["rect"])
            check("circle_radius", radius(top), p["circ_r"])
            check("span", mesh.extents[2], p["span"])
        elif name in ("c1", "c5", "c6"):
            section = loops(2,p["height"]*.8)
            outer = section[0]
            # Fit the low-left corner, excluding its straight tangent segments.
            r = p["fillet_r"]
            corner = outer[(outer[:,0] > .02) & (outer[:,0] < r-.02) &
                           (outer[:,1] > .02) & (outer[:,1] < r-.02)]
            if len(corner) < 3:
                raise ValueError("corner arc missing")
            check("fillet_radius", radius(corner), r)
            if name in ("c5", "c6"):
                inner = section[1]
                for axis in (0,1):
                    check(f"wall_{axis}", (bounds(outer)[axis]-bounds(inner)[axis])/2, p["wall"])
                # A vertical section includes the inner floor.
                cross=loops(0,p["length"]/2)
                zs=np.concatenate(cross)[:,2]
                check("floor_thickness", zs[zs>.01].min(), p["wall"])
            if name in ("c1", "c6"):
                for y in (.5, mesh.bounds[1,1]-.5):
                    holes=loops(1,y)[1:]
                    expected_count=2 if name=="c1" else 1
                    check(f"hole_count_{y}", len(holes), expected_count, 0)
                    for index,hole in enumerate(holes):
                        check(f"hole_diameter_{y}_{index}", 2*radius(hole,(0,2)), p["hole_d" if name=="c1" else "win_d"])
    except Exception as exc:
        checks.append({"check": "feature_measurement", "pass": False, "error": str(exc)})
    return checks
