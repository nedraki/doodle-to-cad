# Issue #62 offline calibration harness.
# Re-scores every frozen #34 trial (80 rows) + today's live-regression trials under the
# CURRENT product gate plus three candidate deterministic rules whose thresholds are
# chosen from measured distributions (never guessed):
#   R1 ink-derived dimensions : per-axis extents vs derive_physical_sizes(evidence, dim)
#   R2 per-view features      : rendered_internal_profiles >= crop_internal_profiles per view
#   R3 genus floor            : through-holes (euler) >= per-view demanded openings
# Output: runs.jsonl (one row per trial, raw measurements) — thresholds applied in analysis.
import json, sys
from pathlib import Path
import trimesh

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from doodle_to_cad.geometry import analyze_image, label_view_geometry
from doodle_to_cad.evaluation import assign_view_groups, evaluate_candidate
from doodle_to_cad.sizes import derive_physical_sizes
from doodle_to_cad.openscad import mesh_health

ROOT = Path(__file__).resolve().parents[1]
RUNS = ROOT / "docs/brep/task-17-comparison/runs"
OUT = ROOT / "docs/brep/issue-62-gate/data/runs.jsonl"
OUT.parent.mkdir(parents=True, exist_ok=True)
ACCEPT_SCORE = 70.0

def through_holes(stl: Path):
    m = trimesh.load_mesh(stl, process=True)
    if not m.is_watertight:
        comps = m.split(only_watertight=False)
        if len(comps) > 1:
            return None  # genus meaningless across disconnected shells here
    return sum(max((2 - c.euler_number) // 2, 0) for c in m.split(only_watertight=False))

def score_trial(drawing, backend, trial, image: bytes, stl: Path, views: dict, spec: dict,
                dim, strict, primary, standard, gt_checks):
    evidence, _ = analyze_image(image)
    assigned = assign_view_groups(evidence, primary, standard)
    evidence = label_view_geometry(evidence, assigned)
    derived = derive_physical_sizes(evidence, dim)
    health = mesh_health(stl) if stl else None
    holes = through_holes(stl) if (stl and health and health["triangles"]) else None
    ok = bool(stl and health and health["triangles"])
    ev = evaluate_candidate(stl=stl if ok else None, health=health if ok else None,
                            scad="", views=views, source=image, evidence=evidence, spec=spec,
                            target_dimension=dim or "", strict=strict, primary_view=primary,
                            projection_standard=standard)
    old_accepted = bool(ev.get("accepted") and (ev.get("score") or 0) >= ACCEPT_SCORE)
    topo = ev.get("profile_topology") or {}
    pt = {d: {"crop": t.get("crop_internal_profiles", 0), "rendered": t.get("rendered_internal_profiles", 0)}
          for d, t in topo.items()}
    ax = {"width": 0, "depth": 1, "height": 2}
    r1 = {}
    if derived and ok:
        for name, i in ax.items():
            exp = derived.get(f"{name}_mm")
            if exp:
                r1[name] = {"expected_mm": exp, "actual_mm": health["extents_mm"][i],
                            "ratio": round(health["extents_mm"][i] / exp, 3)}
    trusted = bool(gt_checks and gt_checks.get("build_success") and gt_checks.get("extents_pass")
                   and gt_checks.get("genus_pass"))
    return {"drawing": drawing, "backend": backend, "trial": trial,
            "old_accepted": old_accepted, "old_score": ev.get("score"),
            "gates": ev.get("mandatory_gates"), "failures": ev.get("failures"),
            "health": health, "through_holes": holes, "profile_topology": pt,
            "derived_sizes": {k: derived.get(k) for k in ("width_mm", "depth_mm", "height_mm")} if derived else None,
            "r1_ratios": r1, "gt_checks": gt_checks, "trusted": trusted}

def iter_frozen():
    for ddir in sorted(RUNS.iterdir()):
        if not ddir.is_dir(): continue
        for bdir in sorted(ddir.iterdir()):
            for tdir in sorted(bdir.glob("trial-*")):
                row = json.loads((tdir / "row.json").read_text())
                req = json.loads((tdir / "request.json").read_text())
                form = req["form"]
                img = (tdir / "input.png").read_bytes()
                sf = tdir / "sketch-spec.json"
                spec = json.loads(sf.read_text()) if sf.is_file() else {}
                views = {k: tdir / "views" / f"{k}.png" for k in ("isometric", "front", "top", "right")
                         if (tdir / "views" / f"{k}.png").is_file()}
                stl = tdir / "stl/model.stl"
                stl = stl if stl.is_file() else None
                yield ddir.name, bdir.name, tdir.name, img, stl, views, spec, \
                      form.get("dimension", ""), str(form.get("strict_watertight", "true")) == "true", \
                      form.get("primary_view", "front"), form.get("projection_standard", "third-angle"), row.get("checks")

with OUT.open("w") as f:
    for drawing, backend, trial, img, stl, views, spec, dim, strict, prim, std, checks in iter_frozen():
        try:
            rec = score_trial(drawing, backend, trial, img, stl, views, spec, dim, strict, prim, std, checks)
        except Exception as exc:
            rec = {"drawing": drawing, "backend": backend, "trial": trial, "error": repr(exc)[:200]}
        f.write(json.dumps(rec) + "\n")
        print(drawing, backend, trial, "accepted" if rec.get("old_accepted") else "rejected",
              "| holes", rec.get("through_holes"), "| trusted", rec.get("trusted"), flush=True)
print("wrote", OUT)
