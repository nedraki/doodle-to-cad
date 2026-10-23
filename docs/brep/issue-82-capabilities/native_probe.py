"""Run ONLY with the isolated kernel interpreter; read the exported native USD.
Native sections are sampled curves, not exact analytic radius verification.
"""
import json,sys
from pathlib import Path
import usd_brep as sm
import numpy as np

body, = sm.usd.import_breps(sys.argv[1])
lo,hi=sm.brep_bounding_box(body)
sections={}
for z in [.05,hi[2]*.25,hi[2]*.5,hi[2]*.75,hi[2]-.05]:
    loops=[]
    for curve in sm.intersect_brep_with_plane(body,(0.,0.,z),(0.,0.,1.)):
        a,b=curve.parameter_range()
        loops.append([list(sm.evaluate_curve(curve,float(t))['point']) for t in np.linspace(a,b,257)])
    sections[str(round(z,4))]=loops
print(json.dumps({'volume_mm3':body.volume(relative_accuracy=1e-8),'bounds':[list(lo),list(hi)],
    'face_count':len(body.faces()),'surface_area_mm2':sum(sm.face_area(f) for f in body.faces()),
    'area_relative_accuracy':.001,'xy_sections':sections,
    'analytic_surface_radii':'unavailable in this measurement; native sections sampled at 257 points/curve'}))
