"""Trusted-recipe capability runner for issue #82.

Run with the WORKER venv python (needs trimesh+numpy; doodle_to_cad.brep_recipe
is stdlib-only so the product's own validator is used verbatim):

  PYTHONPATH=<repo> <worker-venv>/bin/python docs/brep/bench-capabilities/build_capabilities.py

For every case: validate -> build via workers/brep/build.py -> measure ->
compare to expected. Then (if the case defines an edit) change ONLY the named
parameter value, rebuild, and verify protected dimensions did not move and
changed dimensions reached the requested value. Builds that fail are still
recorded (matrix cell 'failed') — no case is dropped.
"""
import json, subprocess, sys, time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(HERE))
from doodle_to_cad.brep_recipe import validate_recipe  # product validator, verbatim
from cases import CASES
import trimesh

WORKER_PY = Path("/home/sparkie/playground/doodle-to-cad/workers/brep/.venv/bin/python")
BUILD = ROOT / "workers" / "brep" / "build.py"
OUT = HERE / "evidence"


def build(recipe: dict, tag: str) -> dict:
    """Write recipe bytes, run the worker, return diagnostics + measurement."""
    d = OUT / tag
    if d.exists():  # never trust evidence from a previous run
        import shutil
        shutil.rmtree(d)
    d.mkdir(parents=True, exist_ok=True)
    rp = d / "model.recipe.json"
    rp.write_text(json.dumps(recipe, indent=1, sort_keys=True))
    t0 = time.time()
    p = subprocess.run([str(WORKER_PY), str(BUILD), str(rp), str(d)],
                       capture_output=True, text=True, timeout=300)
    record = {"worker_exit": p.returncode, "wall_seconds": round(time.time() - t0, 2),
              "stderr_tail": (p.stderr or "").strip().splitlines()[-3:]}
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
    OUT.mkdir(exist_ok=True)
    results = {"schema": 1, "issue": 82, "trust": "trusted-recipe (human authored, no LLM)",
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
        except Exception as exc:  # authoring bug — record, keep going
            entry["initial"] = {"status": "invalid_recipe", "error": str(exc)}
            results["cases"].append(entry)
            print(f"{name}: INVALID RECIPE: {exc}")
            continue
        initial = build(base, f"{name}/initial")
        initial["checks"] = compare(initial, case["initial"] or {}, f"{name}/initial") if case["initial"] else []
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
        _save(base, f"{name}/initial")

        if case["edit"] and initial["status"] in ("pass", "checks_failed", "built"):
            edited = edit_variants(case, base)
            edit_rec = build(edited, f"{name}/edited")
            exp = {"extents": case["edit"]["protected"].get("extents"),
                   "genus": case["edit"]["protected"].get("genus")}
            checks = compare(edit_rec, {k: v for k, v in exp.items() if v is not None}, f"{name}/edited") if exp else []
            # explicit protected-dimension comparisons (tight tolerance)
            p = case["edit"]["protected"]
            meas = edit_rec.get("measure") or {}
            if "extents" in p:
                ok = meas.get("extents") and all(abs(g - w) <= 0.01 for g, w in zip(meas["extents"], p["extents"]))
                checks.append({"check": "protected_extents_unchanged", "pass": ok,
                               "got": meas.get("extents"), "expected": p["extents"]})
            if "extents_z" in p:
                ok = meas.get("extents") and abs(meas["extents"][2] - p["extents_z"]) <= 0.01
                checks.append({"check": "protected_z", "pass": ok,
                               "got": (meas.get("extents") or [None])[2], "expected": p["extents_z"]})
            c = case["edit"].get("changed") or {}
            if "extents_x" in c:
                want = c["extents_x"]
                # new outer parameter feeds extents; tolerance loose: tessellation
                ok = meas.get("extents") and abs(meas["extents"][0] - want) <= max(0.35, abs(want) * 0.01)
                checks.append({"check": "changed_x_reached", "pass": ok,
                               "got": (meas.get("extents") or [None])[0], "expected": want})
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
            _save(edited, f"{name}/edited")
        results["cases"].append(entry)
        line = (f"{name}: initial={initial['status']} "
                f"edit={'-' if 'edit' not in entry else entry['edit']['status']}")
        print(line)
    (HERE / "results.json").write_text(json.dumps(results, indent=1))
    print("wrote", HERE / "results.json")
    fails = [c["id"] for c in results["cases"]
             if c["initial"]["status"] not in ("pass",) and not c["author_effort"]["exploratory"]]
    print("non-exploratory cells not passing:", fails or "none")


def _build_recipe(case):
    from cases import _recipe
    return _recipe(case["id"], case["params"], json.loads(json.dumps(case["ops"])), case["output"])


def _save(recipe, tag):
    p = OUT / tag
    p.mkdir(parents=True, exist_ok=True)
    (p / "model.recipe.json").write_text(json.dumps(recipe, indent=1, sort_keys=True))


if __name__ == "__main__":
    main()
