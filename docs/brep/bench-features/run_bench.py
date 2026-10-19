"""Build every bench fixture through the real worker boundary, then measure
the exported STL with bench_measure.py. Nothing here trusts kernel claims:
diagnostics are recorded for the report but pass/fail comes from the mesh.

Usage (repo root):
    export DOODLE_BREP_PYTHON=$PWD/workers/brep/.venv/bin/python
    PYTHONPATH=. .venv/bin/python docs/brep/bench-features/run_bench.py [job_name ...]

Raw STL + USDA + diagnostics + resolved recipe for every build land under
artifacts/<job>/. Measurement verdicts land under measurements/<job>.json.
"""
from __future__ import annotations

import json
import shutil
import sys
import time
import traceback
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(HERE))

import bench_measure as bm  # noqa: E402
import jobs as job_registry  # noqa: E402
from doodle_to_cad.brep import build_brep  # noqa: E402
from doodle_to_cad.build_contract import BuildInput  # noqa: E402


def stage(job, run_dir):
    doc = json.loads((job_registry.FIXTURES / f"{job['fixture']}.json").read_text())
    for name, value in job["overrides"].items():
        assert name in doc["parameters"], f"unknown override {name}"
        doc["parameters"][name]["value"] = value
    run_dir.mkdir(parents=True, exist_ok=True)
    source = run_dir / "model.recipe.json"
    source.write_text(json.dumps(doc, indent=2))
    return source


def mesh_summary(path):
    mesh = bm.load(path)
    return {"watertight": bool(mesh.is_watertight),
            "winding_consistent": bool(mesh.is_winding_consistent),
            "volume_mm3": round(float(mesh.volume), 3),
            "extents_mm": [round(v, 4) for v in mesh.bounds[1] - mesh.bounds[0]],
            "bounds_mm": [[round(v, 4) for v in mesh.bounds[0]], [round(v, 4) for v in mesh.bounds[1]]],
            "triangles": int(len(mesh.faces)),
            "euler_number": int(mesh.euler_number),
            "components": len(mesh.split())}


def face_delta(diagnostics, kind):
    """Face-count change introduced by the first op of `kind`, from worker history."""
    history = (diagnostics or {}).get("operations", [])
    for i, entry in enumerate(history):
        if entry["kind"] == kind:
            before = history[i - 1]["faces"] if i else 0
            return {"op": entry["id"], "kind": kind, "faces_before": before,
                    "faces_after": entry["faces"], "face_delta": entry["faces"] - before}
    return None


def run_job(job):
    out = job_registry.ARTIFACTS / job["name"]
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    stage_root = HERE / "work" / job["name"]
    if stage_root.exists():
        shutil.rmtree(stage_root)
    source = stage(job, stage_root)
    started = time.monotonic()
    build = build_brep(BuildInput("usd-brep", source, stage_root / "run", render=False))
    record = {"job": job["name"], "category": job["category"], "fixture": job["fixture"],
              "overrides": job["overrides"], "build_ok": build.ok,
              "build_seconds": round(time.monotonic() - started, 2),
              "diagnostics_errors": [vars(d) for d in build.diagnostics],
              "worker_log_tail": build.log[-2000:]}
    stl = out / "model.stl"
    verdict = None
    if build.stl is not None:
        shutil.copy(build.stl, stl)
        shutil.copy(build.exports["usd"], out / "model.usda")
        shutil.copy(build.source, out / "model.recipe.json")
        (out / "diagnostics.json").write_text(json.dumps(build.backend_details, indent=2))
        (out / "worker.log").write_text(build.log)
        record["mesh_summary"] = mesh_summary(stl)
        record["worker_diagnostics"] = {k: build.backend_details.get(k)
                                        for k in ("solid_volume_mm3", "mesh_volume_mm3",
                                                  "usd_roundtrip", "extents_mm", "triangles")}
        if job["checker"]:
            fn = getattr(bm, job["checker"])
            record["checker"] = job["checker"]
            record["expected_args"] = job["args"]
            result = fn(stl, *job["args"])
            if job.get("extra", {}).get("expected_face_delta") is not None:
                fd = face_delta(build.backend_details, "fillet")
                record["face_count_change"] = fd
                ok_fd = fd is not None and fd["face_delta"] == job["extra"]["expected_face_delta"]
                result["checks"]["face count change"] = {
                    "status": "passed" if ok_fd else "failed", **(fd or {}),
                    "expected_face_delta": job["extra"]["expected_face_delta"]}
                result["ok"] = result["ok"] and ok_fd
            verdict = result
    elif job["checker"]:
        verdict = {"ok": False, "checks": {"build": {"status": "failed",
                 "reason": "worker build failed; see artifacts/" + job["name"] + "/build.json"}}}
    (out / "build.json").write_text(json.dumps(record, indent=2))
    job_registry.MEASUREMENTS.mkdir(exist_ok=True)
    measurement = {"job": job["name"], "category": job["category"], "build_ok": build.ok,
                   "expected_fail": job["expected_fail"], "verdict": verdict,
                   "mesh_summary": record.get("mesh_summary"),
                   "face_count_change": record.get("face_count_change"),
                   "note": job.get("note"), "captured_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    if job["category"] == "regression-probe":
        measurement["status"] = ("built" if build.ok else
                                 "kernel_failure" if not build.ok else "?")
        measurement["expected_fail"] = False  # probe: either outcome is data, never a skip
    elif job["checker"]:
        measurement["status"] = ("passed" if verdict["ok"] != job["expected_fail"] else "checker_broken")
    (job_registry.MEASUREMENTS / f"{job['name']}.json").write_text(json.dumps(measurement, indent=2))
    shutil.rmtree(stage_root, ignore_errors=True)
    return measurement


def main():
    selected = sys.argv[1:]
    failures = []
    for job in job_registry.JOBS:
        if selected and job["name"] not in selected:
            continue
        print(f"=== {job['name']} ({job['category']})", flush=True)
        try:
            m = run_job(job)
        except Exception:
            traceback.print_exc()
            failures.append((job["name"], "crashed in harness"))
            continue
        status = m["status"]
        # A probe kernel_failure is published data, not a harness problem.
        ok = status in ("passed", "built", "kernel_failure")
        print(f"{'OK  ' if ok else 'FAIL'} {job['name']}: {status} build_ok={m['build_ok']}", flush=True)
        if not ok:
            failures.append((job["name"], status))
        if m.get("verdict"):
            for name, chk in m["verdict"]["checks"].items():
                if chk["status"] != "passed":
                    print(f"     ✗ {name}: {json.dumps(chk)}", flush=True)
    print("\nSUMMARY")
    for name, status in failures:
        print(f"  problem: {name}: {status}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
