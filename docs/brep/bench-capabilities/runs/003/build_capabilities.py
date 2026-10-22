"""Trusted-recipe capability runner for issue #82.

Run with the WORKER venv python (needs trimesh+numpy; doodle_to_cad.brep_recipe
is stdlib-only so the product's own validator is used verbatim):

  python docs/brep/bench-capabilities/build_capabilities.py --output <new-run-dir>
      --worker-python <worker-venv>/bin/python

For every case: validate -> build via workers/brep/build.py -> measure ->
compare to expected. Then (if the case defines an edit) change ONLY the named
parameter value, rebuild, and verify protected dimensions did not move and
changed dimensions reached the requested value. Builds that fail are still
recorded (matrix cell 'failed') — no case is dropped.
"""
import argparse, json, os, subprocess, sys, time
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(HERE))
from doodle_to_cad.brep_recipe import validate_recipe  # product validator, verbatim
from cases import CASES
from feature_checks import feature_checks
import trimesh

WORKER_PY = Path(os.environ.get("DOODLE_BREP_PYTHON", ROOT / "workers/brep/.venv/bin/python"))
BUILD = ROOT / "workers" / "brep" / "build.py"
OUT = HERE / "evidence"


def build(recipe: dict, tag: str) -> dict:
    """Write recipe bytes, run the worker, return diagnostics + measurement."""
    d = OUT / tag
    d.mkdir(parents=True, exist_ok=False)
    rp = d / "model.recipe.json"
    rp.write_text(json.dumps(recipe, indent=1, sort_keys=True))
    t0 = time.time()
    env = dict(os.environ)
    env.pop("PYTHONPATH", None)
    env.pop("PYTHONHOME", None)
    try:
        p = subprocess.run([str(WORKER_PY), str(BUILD), str(rp), str(d)],
                           capture_output=True, text=True, timeout=300, env=env)
        code, stdout, stderr = p.returncode, p.stdout, p.stderr
    except (subprocess.TimeoutExpired, OSError) as exc:
        code = -1
        stdout = getattr(exc, "stdout", None) or ""
        stderr = getattr(exc, "stderr", None) or str(exc)
    def decoded(value):
        return value.decode(errors="replace") if isinstance(value, bytes) else value
    (d / "stdout.log").write_text(decoded(stdout))
    (d / "stderr.log").write_text(decoded(stderr))
    record = {"worker_exit": code, "wall_seconds": round(time.time() - t0, 2),
              "stderr_tail": decoded(stderr).strip().splitlines()[-3:]}
    diag = d / "diagnostics.json"
    err = d / "construction-error.json"
    if diag.exists():
        record["diagnostics"] = json.loads(diag.read_text())
    elif err.exists():
        record["construction_error"] = json.loads(err.read_text())
    stl = d / "model.stl"
    if stl.exists():
        m = trimesh.load(str(stl), force="mesh")
        watertight = bool(m.is_watertight)
        comps = m.split(only_watertight=False) if not watertight else m.split()
        genus = None
        if watertight and len(comps) == 1:
            genus = (2 - int(m.euler_number)) // 2
        record["measure"] = {
            "extents": [round(float(x), 3) for x in m.extents],
            "watertight": watertight,
            "components": int(len(comps)),
            "genus": genus,
            "mesh_volume_mm3": round(float(m.volume), 1) if watertight else None,
            "stl_sha256": __import__("hashlib").sha256(stl.read_bytes()).hexdigest(),
        }
    return record


def compare(rec: dict, expect: dict, tag: str, tol_ext=0.05, tol_vol=0.02) -> list:
    checks = []
    def add(name, ok, got, want):
        checks.append({"check": name, "pass": bool(ok), "got": got, "expected": want})
    meas = rec.get("measure") or {}
    diag = rec.get("diagnostics") or {}
    if expect.get("extents"):
        add("extents", meas.get("extents") and all(
            abs(g - w) <= expect.get("extents_tol", tol_ext)
            for g, w in zip(meas["extents"], expect["extents"])),
            meas.get("extents"), expect["extents"])
    for key in ("genus", "watertight", "components"):
        if expect.get(key) is not None:
            add(key, meas.get(key) == expect[key], meas.get(key), expect[key])
    ev = expect.get("volume_mm3")
    if ev:
        want, rel = ev
        got = diag.get("solid_volume_mm3")
        got_src = "solid_volume_mm3"
        if got is None:
            got, got_src = meas.get("mesh_volume_mm3"), "mesh_volume_mm3(native n/a)"
        add("volume", got is not None and abs(got - want) / want <= rel, got, round(want, 1))
    if expect.get("chamfer_45_facets"):
        # A true chamfer of a drilled box shows 45-degree facets per bevelled
        # edge; bbox extents are NOT a valid chamfer probe (bevel endpoints
        # preserve the extremes). Count facet normals at 45 degrees.
        stl = (OUT / tag / "model.stl")
        want_n = expect["chamfer_45_facets"]
        ok, got_n = False, None
        if stl.exists():
            import numpy as np
            m = trimesh.load(str(stl), force="mesh")
            n = m.face_normals
            pairs = []
            for a, b in ((0, 1), (0, 2), (1, 2)):
                for sa in (1, -1):
                    for sb in (1, -1):
                        v = np.zeros(3); v[a] = sa; v[b] = sb
                        v = v / np.linalg.norm(v)
                        pairs.append(v)
            hit = {tuple(np.round(nn, 2)) for nn in n for p in pairs
                   if bool(np.all(np.abs(nn - p) < 0.02))}
            got_n = len(hit)
            ok = got_n == want_n
        add("chamfer_45_facets", ok, got_n, want_n)
    if expect.get("volume_less_than"):
        got = diag.get("solid_volume_mm3") or meas.get("mesh_volume_mm3")
        add("volume_less_than", got is not None and got < expect["volume_less_than"],
            got, f"< {expect['volume_less_than']}")
    return checks


def edit_variants(case, base):
    e = case["edit"]
    edited = json.loads(json.dumps(base))
    edited["parameters"][e["param"]]["value"] = e["new"]
    return edited


def main():
    global OUT, WORKER_PY
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True, help="New run directory; existing paths are refused")
    parser.add_argument("--worker-python", type=Path, default=WORKER_PY)
    args = parser.parse_args()
    OUT = args.output.resolve()
    WORKER_PY = args.worker_python.absolute()
    OUT.mkdir(parents=True, exist_ok=False)
    for source in (Path(__file__), HERE / "cases.py", HERE / "feature_checks.py"):
        (OUT / source.name).write_bytes(source.read_bytes())
    (OUT / "plan.json").write_text(json.dumps(CASES, indent=2))
    (OUT / "environment.json").write_text(json.dumps({
        "started_utc": datetime.now(timezone.utc).isoformat(),
        "python": sys.version, "worker_python": str(WORKER_PY),
        "git_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "git_status": subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT, text=True),
        "trimesh": trimesh.__version__,
    }, indent=2))
    results = {"schema": 2, "issue": 82, "trust": "trusted-recipe (human authored, no LLM)",
               "worker_python": str(WORKER_PY), "cases": []}
    for case in CASES:
        name = case["id"]
        entry = {"id": name, "capability": case["capability"],
                 "author_effort": {"operations": case["author_ops"],
                                   "parameters": case["author_params"],
                                   "exploratory": case.get("exploratory", False)}}
        if case.get("constraint_note"):
            entry["constraint_note"] = case["constraint_note"]
        try:
            base = _build_recipe(case)
            validate_recipe(base)
        except Exception as exc:  # authoring bug — record, keep going
            entry["initial"] = {"status": "invalid_recipe", "error": str(exc)}
            results["cases"].append(entry)
            print(f"{name}: INVALID RECIPE: {exc}")
            (OUT / "results.json").write_text(json.dumps(results, indent=1))
            continue
        initial = build(base, f"{name}/initial")
        initial["checks"] = compare(initial, case["initial"] or {}, f"{name}/initial") if case["initial"] else []
        if case["edit"]:
            initial["checks"].extend(feature_checks(OUT / f"{name}/initial/model.stl", case, base))
        # The worker's own verdict outranks a present STL: the round-trip
        # guard can abort AFTER writing artifacts, so a build with a
        # construction-error or non-zero exit is FAILED regardless of bytes.
        if "construction_error" in initial or initial.get("worker_exit") != 0:
            initial["status"] = "failed"
        else:
            initial["status"] = ("built" if "measure" in initial else "failed")
        if initial["status"] == "built" and initial["checks"]:
            initial["status"] = "pass" if all(c["pass"] for c in initial["checks"]) else "checks_failed"
        entry["initial"] = initial

        if case["edit"] and initial["status"] in ("pass", "checks_failed", "built"):
            edited = edit_variants(case, base)
            validate_recipe(edited)
            edit_rec = build(edited, f"{name}/edited")
            exp = {k: v for k, v in case["initial"].items()
                   if k in ("genus", "watertight", "components")}
            checks = compare(edit_rec, exp, f"{name}/edited")
            checks.extend(feature_checks(OUT / f"{name}/edited/model.stl", case, edited))
            edit_rec["checks"] = checks
            edit_rec["status"] = ("failed" if ("construction_error" in edit_rec
                                               or edit_rec.get("worker_exit") != 0)
                                  else ("pass" if edit_rec.get("measure") and all(k["pass"] for k in checks)
                                        else ("failed" if "measure" not in edit_rec else "checks_failed")))
            edit_rec["param_changed"] = {case["edit"]["param"]: case["edit"]["new"]}
            edit_rec["ops_identical"] = (
                [ {k: v for k, v in op.items() if k != "evidence"} for op in base["operations"] ]
                == [ {k: v for k, v in op.items() if k != "evidence"} for op in edited["operations"] ])
            entry["edit"] = edit_rec
        results["cases"].append(entry)
        line = (f"{name}: initial={initial['status']} "
                f"edit={'-' if 'edit' not in entry else entry['edit']['status']}")
        print(line, flush=True)
        (OUT / "results.json").write_text(json.dumps(results, indent=1))
    (OUT / "results.json").write_text(json.dumps(results, indent=1))
    print("wrote", OUT / "results.json")
    fails = [c["id"] for c in results["cases"]
             if c["initial"]["status"] != "pass" or
             (c.get("edit", {}).get("status", "pass") != "pass")]
    print("cells not passing:", fails or "none")
    return int(bool(fails))


def _build_recipe(case):
    from cases import _recipe
    return _recipe(case["id"], case["params"], json.loads(json.dumps(case["ops"])), case["output"])



if __name__ == "__main__":
    sys.exit(main())
