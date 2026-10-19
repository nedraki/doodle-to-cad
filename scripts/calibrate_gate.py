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

LIVE_TRIALS = [
    # (name, results dir, case GT checks measured against ground truth this session)
    ("jeep-012-accepted", "/tmp/doodle-brep-32/results/c4182aeca6b7",
     {"build_success": True, "extents_pass": False, "genus_pass": True}),   # 100x5x61 vs 100x4x60
    ("grille-003-regression", "/tmp/doodle-brep-32/results/7c0175c7ff7d",
     {"build_success": True, "extents_pass": False, "genus_pass": False}),   # genus 0, thickness 5 vs 3
    ("motor-103-accepted", "/tmp/doodle-brep-32/results/7c274ef76d20",
     {"build_success": True, "extents_pass": False, "genus_pass": False}),   # 2/4 bores, +16% height
]
for side, jobs in (("main", ["34962e61b41f", "e17a9ccd5e68", "e8107d64c913"]),
                   ("branch", ["06de487133d8", "dfa8a3608afc", "4cf6e48320db"])):
    for i, job in enumerate(jobs, 1):
        LIVE_TRIALS.append((f"grille-ab-{side}-{i}", f"/tmp/doodle-brep-{'main' if side=='main' else '32'}/results/{job}",
                            {"build_success": True, "extents_pass": False, "genus_pass": None}))

def iter_live():
    for name, d, checks in LIVE_TRIALS:
        tdir = Path(d)
        form = {"dimension": "100" if "jeep" in name else ("130" if "grille" in name else "60")}
        for key, truth in (("jeep-012", "100"), ("grille", "130"), ("motor", "60")):
            if name.startswith(key): form["dimension"] = truth
        sf = tdir / "sketch-spec.json"
        spec = json.loads(sf.read_text()) if sf.is_file() else {}
        views = {k: tdir / f"view-{k}.png" for k in ("isometric", "front", "top", "right")
                 if (tdir / f"view-{k}.png").is_file()}
        stl = tdir / "model.stl"; stl = stl if stl.is_file() else None
        yield (name, "live", "trial-01", (tdir / "input.png").read_bytes(), stl, views, spec,
               form["dimension"], True, "front", "third-angle", checks)

if "--no-gate" in sys.argv:
    # Baseline pass: neutralize the shipped R3 gate so old/new come from ONE
    # deterministic code path, never from a race between two processes.
    import doodle_to_cad.evaluation as _ev
    _ev.openings_through_check = lambda health, expected, best_direction, strict: (True, "")

if "--live" in sys.argv:
    OUT = OUT.parent / ("runs-live-newgate.jsonl" if "--no-gate" not in sys.argv else "runs-live.jsonl")
    with OUT.open("w") as f:
        for name, backend, trial, img, stl, views, spec, dim, strict, prim, std, checks in iter_live():
            try:
                rec = score_trial(name, backend, trial, img, stl, views, spec, dim, strict, prim, std, checks)
            except Exception as exc:
                rec = {"drawing": name, "backend": backend, "trial": trial, "error": repr(exc)[:200]}
            f.write(json.dumps(rec) + "\n")
            print(name, "accepted" if rec.get("old_accepted") else "rejected",
                  "| holes", rec.get("through_holes"), "| r1", rec.get("r1_ratios"),
                  "| pt", rec.get("profile_topology"), flush=True)
    print("wrote", OUT)
    sys.exit(0)

if "--no-gate" not in sys.argv and "--live" not in sys.argv:
    OUT = OUT.parent / "runs-newgate.jsonl"
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
