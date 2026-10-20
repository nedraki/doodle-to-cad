"""Forensic probe for issue #90: what IS the reloaded USD solid?

Intercepts usd_brep.usd.import_breps during a real worker build of the c1
fillet+holes recipe, tessellates every reloaded item, saves it as STL and
writes reloaded_probe.json next to the build output.

Run (worker venv):
  PYTHONPATH=<repo> <worker-venv>/bin/python probe_inject90.py <c1-recipe.json> <outdir>
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))  # repo (for build.py import path)
import usd_brep as base  # noqa: E402
import trimesh  # noqa: E402

CAPTURE = {}


class UsdShim:
    def __getattr__(self, name):
        return getattr(base.usd, name)

    def import_breps(self, path):
        items = base.usd.import_breps(path)
        report = []
        for i, item in enumerate(items):
            d = {"index": i, "volume": item.volume(relative_accuracy=1e-8)}
            try:
                poly = base.tessellate(item, chord_height_tolerance=0.05)
                a = poly.to_mesh_arrays()
                stream, tris, cur = a["faces"], [], 0
                while cur < len(stream):
                    count = stream[cur]
                    tris.append(stream[cur + 1:cur + 4])
                    cur += count + 1
                m = trimesh.Trimesh(vertices=a["points"], faces=tris, process=False)
                d.update(faces=int(len(m.faces)), watertight=bool(m.is_watertight),
                         euler=int(m.euler_number),
                         extents=[round(float(x), 3) for x in m.extents],
                         mesh_volume=round(float(m.volume), 1))
                if m.is_watertight and len(m.split()) == 1:
                    d["genus"] = (2 - int(m.euler_number)) // 2
                m.export(str(Path(sys.argv[3]) / f"reloaded_{i}.stl"))
            except Exception as exc:
                d["tess_error"] = str(exc)
            report.append(d)
        CAPTURE["imported"] = report
        return items


class ModuleShim:
    usd = UsdShim()

    def __getattr__(self, name):
        return getattr(base, name)


sys.modules["usd_brep"] = ModuleShim()

import runpy  # noqa: E402

sys.argv = ["build.py", sys.argv[1], sys.argv[2]]
Path(sys.argv[2]).mkdir(parents=True, exist_ok=True)
try:
    runpy.run_path(str(Path(__file__).resolve().parents[4] / "workers" / "brep" / "build.py"),
                   run_name="__main__")
except SystemExit:
    pass
out = Path(sys.argv[2]) / "reloaded_probe.json"
out.write_text(json.dumps({"imported": CAPTURE.get("imported", [])}, indent=2))
print(out.read_text())
