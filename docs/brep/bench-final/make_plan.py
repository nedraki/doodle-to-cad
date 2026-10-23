import json, datetime, math
from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]  # repo root: never a hard-coded author dir
base = json.loads((ROOT/'docs/brep/task-17-comparison/TRIAL-PLAN.json').read_text())
import trimesh
corpus = []
for cdir in sorted((ROOT/'benchmarks/cases').iterdir()):
    if not cdir.is_dir():
        continue
    m = json.loads((cdir/'manifest.json').read_text())
    dpath = cdir/'source'/'drawing.png'
    assert dpath.is_file(), cdir
    dim = m.get('target_dimension_mm')
    if dim is None:
        stl = cdir/'ground_truth'/'model.stl'
        if stl.is_file():
            ext = max(trimesh.load(stl, force='mesh').extents)
            dim = str(int(math.ceil(ext)))
        else:
            dim = "120"
    title = m.get('title') or cdir.name.split('_', 1)[-1].replace('_', ' ')
    corpus.append({"id": cdir.name, "role": "benchmark case: " + title,
                   "drawing": "benchmarks/cases/" + cdir.name + "/source/drawing.png",
                   "notes": title, "dimension": str(dim),
                   "primary_view": (m.get('controls') or {}).get('primary_view', 'front'),
                   "reference": "ground_truth/model.stl (see case manifest)",
                   "checks": {"openscad": "all", "usd_brep": "all"}})
    print(cdir.name, "dim", dim)
feats = [
    ("constant_radius_handle", "benchmarks/brep-baseline/curved_handle/drawing.png", "curved handle: constant-radius arc bend", "100"),
    ("rounded_housing", "benchmarks/brep-features/rounded_housing/drawing.png", "housing block with rounded (filleted) vertical edges", "90"),
    ("bevelled_block", "benchmarks/brep-features/bevelled_block/drawing.png", "block with chamfered top edges", "80"),
    ("rectangular_sweep", "benchmarks/brep-features/rectangular_sweep/drawing.png", "rectangular section swept along a curved path", "100"),
    ("solid_transition", "benchmarks/brep-baseline/transition/drawing.png", "solid transition from rectangular to round end", "100"),
    ("wheel", "benchmarks/brep-baseline/wheel/drawing.png", "spoked wheel: rim, hub, spokes, circular", "100"),
]
for fid, path, notes, dim in feats:
    assert (ROOT/path).is_file(), path
    corpus.append({"id": fid, "role": "feature drawing (curves/fillets/chamfers)",
                   "drawing": path, "notes": notes, "dimension": dim, "primary_view": "front",
                   "reference": "#42/#43 feature contract (benchmarks/brep-features/selection.json)",
                   "checks": {"openscad": "all", "usd_brep": "all"}})
plan = {"schema_version": 1,
        "issue": "nedraki/doodle-to-cad#17 (BRep line final evaluation)",
        "title": "Final product evaluation on the merged BRep line: 17 benchmark cases + 6 feature drawings x 2 backends",
        "frozen_at": datetime.datetime.now().astimezone().isoformat(timespec='seconds'),
        "frozen_git_rev": __import__('subprocess').run(['git', '-C', str(ROOT), 'rev-parse', 'HEAD'], capture_output=True, text=True).stdout.strip(),
        "honesty_rules": base["honesty_rules"],
        "new_since_issue_34": [
            "issue #62 openings_through genus floor is active in the evaluator",
            "issue #67 registers stroke-ring openings outside view outlines; demanded openings now sum per view",
            "issue #68 size-ask runs with ask_missing_dimensions=false (harness default) so unattended trials never stall",
            "003 grille drawing re-inked from trusted STL (24946c7); ink and reference now agree"],
        "infrastructure": dict(base["infrastructure"], trials_per_cell=2),
        "model_settings": base["model_settings"],
        "tolerances": base["tolerances"],
        "reference_measurements": base.get("reference_measurements", {}),
        "pass_criteria": base["pass_criteria"],
        "clarification_policy": base["clarification_policy"],
        "corpus": corpus,
        "evidence_layout": base["evidence_layout"]}
out = ROOT/'docs/brep/bench-final'
out.mkdir(exist_ok=True)
(out/'TRIAL-PLAN.json').write_text(json.dumps(plan, indent=2) + "\n")
print("plan items:", len(corpus), "| matrix:", len(corpus) * 2 * 2, "runs | frozen:", plan['frozen_git_rev'][:7])
