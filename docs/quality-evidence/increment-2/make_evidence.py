# Increment 2 evidence: tilted doodle vs axis-aligned render, before/after pose alignment.
# Uses the REAL projection pipeline internals (crop, rotations, IoU/edge scoring).
import json, pathlib
import numpy as np, cv2
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from doodle_to_cad.evaluation import _decode, _projection_pair, _rotate_crop, _normalized_profile

out = pathlib.Path(__file__).parent

def make_sheet(angle):
    canvas = np.full((600, 600, 3), 255, np.uint8)
    sheet = np.full((300, 300, 3), 255, np.uint8)
    cv2.rectangle(sheet, (55, 55), (245, 245), (0, 0, 0), 5)
    cv2.circle(sheet, (110, 150), 26, (0, 0, 0), 5)
    cv2.circle(sheet, (190, 150), 26, (0, 0, 0), 5)
    m = cv2.getRotationMatrix2D((150, 150), angle, 1.0)
    canvas[150:450, 150:450] = cv2.warpAffine(sheet, m, (300, 300), borderValue=(255, 255, 255))
    ok, enc = cv2.imencode(".png", canvas); assert ok
    return enc.tobytes()

render = np.full((300, 300, 3), (245, 245, 220), np.uint8)
cv2.rectangle(render, (55, 55), (245, 245), (20, 170, 190), -1)
cv2.circle(render, (110, 150), 26, (245, 245, 220), -1)
cv2.circle(render, (190, 150), 26, (245, 245, 220), -1)
render_bgr = render.copy()
render_path = out / "front.png"; cv2.imwrite(str(render_path), render)
from doodle_to_cad.evaluation import projection_scores
evidence = {"view_groups": [{"bbox_normalized": [.25, .25, .5, .5], "center_normalized": [.5, .5], "relative_size": 1}],
            "closed_internal_profile_count": 2}
scores, topo = projection_scores(make_sheet(35), evidence, {"front": render_path})

source_img = _decode(make_sheet(35))
crop = source_img[150:450, 150:450]
rendered_img = _decode(render_path.read_bytes())
base_score, _, _ = _projection_pair(crop, rendered_img)
best = (base_score, 0, crop)
for a in range(-60, 61, 5):
    if not a: continue
    rc = _rotate_crop(crop, a); s, _, _ = _projection_pair(rc, rendered_img)
    if s > best[0]: best = (s, a, rc)
final_score, angle, aligned = best
print(json.dumps({"base": base_score, "chosen_rotation": angle, "final": final_score,
                  "gate_reported": scores}, indent=1))

def overlay(ax, crop_bgr, title, score):
    src, _ = _normalized_profile(crop_bgr, render=False)
    ren, _ = _normalized_profile(rendered_img, render=True)
    canvas = np.ones((96, 96, 3), np.uint8) * 255
    canvas[ren > 0] = (20, 170, 190)                      # render body (BGR teal)
    ys, xs = np.where(src > 0)
    rows = canvas[ys, xs]
    overlap = (rows == np.array([20, 170, 190])).all(axis=1)
    canvas[ys, xs] = np.where(overlap[:, None], np.array([0, 0, 0]), np.array([0, 0, 255]))
    ax.imshow(cv2.resize(canvas, (384, 384), interpolation=cv2.INTER_NEAREST))
    ax.set_title(f"{title}  similarity {score:.2f} ({'PASS' if score >= .45 else 'FAIL'} vs 0.45 floor)", fontsize=10)
    ax.set_axis_off()

fig, axes = plt.subplots(1, 3, figsize=(13.5, 4.8))
axes[0].imshow(cv2.cvtColor(source_img, cv2.COLOR_RGB2BGR)); axes[0].set_title("doodle as drawn (35° tilt)", fontsize=10); axes[0].set_axis_off()
axes[1].imshow(cv2.cvtColor(render_bgr, cv2.COLOR_RGB2BGR)); axes[1].set_title("CAD front render (axis-aligned)", fontsize=10); axes[1].set_axis_off()
overlay(axes[2], aligned, f"after pose search (rot {angle}°)", final_score)
axes[2].set_axis_off()
fig.suptitle(f"same drawing, same render — upright crop scored {base_score:.2f} (would burn a repair round); "
             f"pose-aligned crop scores {final_score:.2f}; gate reports {scores['front']}", fontsize=10)
fig.tight_layout(rect=[0, 0, 1, 0.93])
fig.savefig(out / "pose-alignment-before-after.png", dpi=110)
(out / "scores.json").write_text(json.dumps({"base": base_score, "chosen_rotation_deg": angle,
                                             "aligned": final_score, "gate_projection_scores": scores,
                                             "topology": topo}, indent=2))
print("WROTE", out / "pose-alignment-before-after.png")
