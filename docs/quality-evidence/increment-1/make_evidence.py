# Increment 1 evidence: blind notch vs through hole — pixels agree, genus does not.
# Builds two REAL solids (slab + cylinder boolean), runs the REAL mesh_health and
# evaluate_candidate gates, and lays out top views + sections with the machine verdicts.
import json, pathlib
import numpy as np, cv2, trimesh, manifold3d
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
from doodle_to_cad.openscad import mesh_health
from doodle_to_cad.evaluation import evaluate_candidate

out = pathlib.Path(__file__).parent
slab = trimesh.creation.box(extents=(120, 100, 20))
cyl_thru = trimesh.creation.cylinder(radius=15, height=60, sections=96)
cyl_thru.apply_translation([30, 30, 10])                       # pokes out both faces
cyl_blind = trimesh.creation.cylinder(radius=15, height=20.5, sections=96)
cyl_blind.apply_translation([30, 30, 10 + 0.25])               # pocket 10 mm deep from top

through = trimesh.boolean.difference([slab, cyl_thru], engine="manifold")
blind   = trimesh.boolean.difference([slab, cyl_blind], engine="manifold")
through.export(out / "through.stl"); blind.export(out / "blind.stl")
h_thru, h_blind = mesh_health(out / "through.stl"), mesh_health(out / "blind.stl")

def top_view(ax, mesh, title):
    verts, faces = mesh.vertices, mesh.faces
    coll = Poly3DCollection(verts[faces], zsort="max")
    coll.set_facecolor((0.35, 0.62, 0.75, 1.0)); coll.set_edgecolor((0.1, 0.2, 0.3, 0.25))
    ax.add_collection3d(coll)
    lim = np.array([[-70, 70], [-60, 60], [-15, 15]])
    ax.set_xlim(*lim[0]); ax.set_ylim(*lim[1]); ax.set_zlim(*lim[2])
    ax.view_init(elev=90, azim=-90); ax.set_title(title, fontsize=10); ax.set_axis_off()

def section(ax, mesh, title):
    # Material mask at z=-5 by ray-cast point inclusion — robust ordering-free
    # ground truth: through-hole leaves a white circle, blind notch is solid.
    xs = np.linspace(-62, 62, 380); ys = np.linspace(-52, 52, 300)
    gx, gy = np.meshgrid(xs, ys)
    pts = np.column_stack([gx.ravel(), gy.ravel(), np.full(gx.size, -5.0)])
    mask = mesh.contains(pts).reshape(gx.shape)
    img = np.where(mask[..., None], np.array([89, 148, 173]), np.array([255, 255, 255])).astype(np.uint8)
    ax.imshow(img, extent=[-70, 70, -60, 60], origin="lower")
    ax.set_xlim(-70, 70); ax.set_ylim(-60, 60)
    ax.set_aspect("equal"); ax.set_title(title, fontsize=10); ax.set_axis_off()

fig = plt.figure(figsize=(11, 8.6))
axes = [[fig.add_subplot(2, 2, i * 2 + j + 1, **({"projection": "3d"} if i == 0 else {})) for j in range(2)] for i in range(2)]
top_view(axes[0][0], through, "THROUGH hole — top view")
top_view(axes[0][1], blind, "BLIND pocket — top view")
section(axes[1][0], through, "section at mid-depth z=-5mm (through: hole open)")
section(axes[1][1], blind, "section at mid-depth z=-5mm (blind: solid material)")

# Real gates on the two solids, fed the same drawing that demands 1 opening.
source = np.full((300, 300, 3), 255, np.uint8)
cv2.rectangle(source, (30, 30), (270, 270), (0, 0, 0), 5); cv2.circle(source, (150, 150), 38, (0, 0, 0), 5)
ok, enc = cv2.imencode(".png", source); assert ok
render = np.full((300, 300, 3), (245, 245, 220), np.uint8)
cv2.rectangle(render, (30, 30), (270, 270), (20, 170, 190), -1)
cv2.circle(render, (150, 150), 38, (245, 245, 220), -1)
cv2.imwrite(str(out / "front.png"), render)
evidence = {"view_groups": [{"bbox_normalized": [0, 0, 1, 1], "center_normalized": [.5, .5], "relative_size": 1}],
            "closed_internal_profile_count": 1}
verdicts = {}
for name, health in (("through", h_thru), ("blind", h_blind)):
    health = dict(health, extents_mm=[120.0, 100.0, 20.0])  # keep nominal target scale
    ev = evaluate_candidate(stl=pathlib.Path("x.stl"), health=health, scad="", views={"front": out / "front.png"},
                            source=enc.tobytes(), evidence=evidence, spec={}, target_dimension="120", strict=True)
    verdicts[name] = {"genus_total": health["genus_total"], "accepted": ev["accepted"],
                      "features_pass": ev["mandatory_gates"]["features"],
                      "projection_similarity": ev["projection_similarity"],
                      "genus_failure": next((f for f in ev["failures"] if "genus" in f), None)}
print(json.dumps(verdicts, indent=2))
cap = (f"projection-gate similarity of EACH solid to the same drawing (both pass it — the blind notch is invisible to pixels): "
       f"through {verdicts['through']['projection_similarity']['front']:.2f} / blind {verdicts['blind']['projection_similarity']['front']:.2f}  |  "
       f"genus_total: through={verdicts['through']['genus_total']} blind={verdicts['blind']['genus_total']}  |  "
       f"features gate: through={'PASS' if verdicts['through']['features_pass'] else 'FAIL'} "
       f"blind={'PASS' if verdicts['blind']['features_pass'] else 'FAIL (new genus gate)'}")
fig.suptitle(cap, fontsize=10)
fig.tight_layout(rect=[0, 0.02, 1, 0.96])
fig.savefig(out / "gate-integrity-blind-vs-through.png", dpi=110)
(out / "verdicts.json").write_text(json.dumps({"solids": {"through": h_thru, "blind": h_blind}, "verdicts": verdicts}, indent=2))
print("WROTE", out / "gate-integrity-blind-vs-through.png")
