"""Drive the running app over HTTP with benchmark drawings; record outcomes.

Usage:
  PYTHONPATH=<repo> python benchmarks/run_pipeline.py --base http://127.0.0.1:8081 \
      --tag pre-fix [--cases 004,007] [--mode assisted|raw]

Writes benchmarks/pipeline-report-<tag>.json (+ per-case artifacts under
benchmarks/runs/<tag>/<case>/). Scored against ground_truth metrics, not the
pipeline's own opinion alone.
"""
from __future__ import annotations
import argparse
import json
import shutil
import time
import urllib.request
from pathlib import Path

import trimesh

ROOT = Path(__file__).resolve().parent
CASES = ROOT / "cases"
RUNS = ROOT / "runs"


def post_generate(base: str, drawing: Path, payload: dict, timeout: int = 1200) -> dict:
    import uuid
    boundary = uuid.uuid4().hex
    parts = []
    for key, value in payload.items():
        parts.append(f"--{boundary}\r\nContent-Disposition: form-data; name=\"{key}\"\r\n\r\n{value}\r\n".encode())
    parts.append(
        (f"--{boundary}\r\nContent-Disposition: form-data; name=\"image\"; filename=\"drawing.png\"\r\n"
         f"Content-Type: image/png\r\n\r\n").encode() + drawing.read_bytes() + b"\r\n")
    parts.append(f"--{boundary}--\r\n".encode())
    body = b"".join(parts)
    request = urllib.request.Request(
        f"{base}/api/generate", data=body,
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"}, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            submission = json.loads(response.read())
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", "replace")
        raise RuntimeError(f"HTTP {exc.code} from /api/generate: {detail[:1500]}") from exc
    # Async job API: the POST returns {job_id}; poll until the job settles.
    if "job_id" in submission and "result" not in submission:
        deadline = time.time() + timeout
        while time.time() < deadline:
            time.sleep(3)
            try:
                with urllib.request.urlopen(f"{base}/api/generate/{submission['job_id']}", timeout=30) as response:
                    job = json.loads(response.read())
            except urllib.error.HTTPError as exc:
                raise RuntimeError(f"HTTP {exc.code} polling job {submission['job_id']}") from exc
            if job.get("status") == "done":
                return job["result"]
            if job.get("status") == "error":
                raise RuntimeError(f"job {submission['job_id']} failed: {job.get('error')}")
            if job.get("status") == "cancelled":
                raise RuntimeError(f"job {submission['job_id']} cancelled")
        raise RuntimeError(f"job {submission['job_id']} timed out after {timeout}s")
    return submission


def ratio(actual, expected):
    if not expected:
        return None
    return round(float(actual) / float(expected), 4)


def score_case(result: dict, case_dir: Path, run_dir: Path) -> dict:
    manifest = json.loads((case_dir / "manifest.json").read_text())
    gt = trimesh.load_mesh(case_dir / "ground_truth" / "model.stl", process=True)
    gt_extents = [float(x) for x in gt.extents]
    files = result.get("files") or {}
    evaluation = result.get("evaluation") or {}
    health = result.get("mesh_health") or {}
    labels = manifest.get("semantic_labels") or {}
    record = {
        "id": manifest["id"], "family": labels.get("family") or labels.get("construction_family") or "unknown",
        "success": result.get("success"), "score": evaluation.get("score"),
        "accepted_gates": evaluation.get("mandatory_gates"),
        "failures": evaluation.get("failures"),
        "projection_similarity": evaluation.get("projection_similarity"),
        "profile_topology": evaluation.get("profile_topology"),
        "selected_attempt": result.get("selected_attempt"), "attempt_count": len(result.get("attempts") or []),
        "repaired": result.get("repaired"), "duration_s": result.get("duration_seconds"),
        "model": result.get("model"), "run_id": result.get("id"),
    }
    if health:
        extents = health.get("extents_mm") or [0, 0, 0]
        record["extents_mm"] = extents
        record["extent_ratios_vs_gt"] = [ratio(a, e) for a, e in zip(extents, gt_extents)]
        envelope = ((manifest.get("reference") or {}).get("print_envelope_mm") or {}).get("max", 256.0)
        record["fits_build_envelope"] = all(e <= envelope for e in extents)
        record["watertight"] = health.get("watertight")
        record["components"] = health.get("components")
        gt_vol = abs(gt.volume)
        if gt_vol:
            record["volume_ratio_vs_gt"] = round(health.get("volume_mm3", 0) / gt_vol, 4)
    # keep artifacts for post-hoc inspection
    run_dir.mkdir(parents=True, exist_ok=True)
    for key, name in (("scad", "model.scad"), ("stl", "model.stl")):
        url = files.get(key)
        if not url:
            continue
        source = ROOT.parent / url.lstrip("/")
        if source.exists():
            shutil.copy2(source, run_dir / name)
    results_root = ROOT.parent / "results" / str(result.get("id"))
    if results_root.exists():
        shutil.copytree(results_root, run_dir / "pipeline", dirs_exist_ok=True)
    (run_dir / "record.json").write_text(json.dumps(record, indent=2))
    return record


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", default="http://127.0.0.1:8081")
    parser.add_argument("--tag", default="adhoc")
    parser.add_argument("--cases", default="", help="comma list of id prefixes; default all")
    parser.add_argument("--mode", choices=("assisted", "raw"), default="assisted")
    parser.add_argument("--split", default="", help="filter by split (development/validation/holdout)")
    args = parser.parse_args()

    selected = []
    for manifest_path in sorted(CASES.glob("*/manifest.json")):
        manifest = json.loads(manifest_path.read_text())
        if args.split and manifest.get("split") != args.split:
            continue
        if args.cases and not any(manifest["id"].startswith(prefix.strip()) for prefix in args.cases.split(",")):
            continue
        selected.append((manifest_path.parent, manifest))

    report = {"tag": args.tag, "mode": args.mode, "base": args.base,
              "started": time.strftime("%Y-%m-%d %H:%M:%S"), "cases": []}
    for case_dir, manifest in selected:
        primary = (manifest.get("controls") or {}).get("primary_view", "front")
        object_name = (manifest.get("semantic_labels") or {}).get("object", "")
        notes = "" if args.mode == "raw" else object_name
        object_type = "" if args.mode == "raw" else object_name
        dimension = "" if args.mode == "raw" else str(manifest.get("target_dimension_mm") or "")
        if args.mode != "raw" and not dimension.strip():
            gt_stl = case_dir / "ground_truth" / "model.stl"
            if gt_stl.exists():
                try:
                    import trimesh
                    ext = trimesh.load_mesh(gt_stl, process=False).extents
                    dimension = str(round(float(max(ext)), 1))
                except Exception:
                    dimension = ""
        payload = {"notes": notes, "dimension": dimension, "object_type": object_type,
                   "method": "3D print", "primary_view": primary,
                   "projection_standard": "third-angle", "strict_watertight": "true",
                   "view_directions": "[]"}
        print(f"== {manifest['id']} ({args.mode})", flush=True)
        started = time.monotonic()
        try:
            result = post_generate(args.base, case_dir / "source" / "drawing.png", payload)
        except Exception as exc:  # HTTP 500 etc.
            report["cases"].append({"id": manifest["id"], "error": f"{type(exc).__name__}: {exc}"[:500]})
            print(f"   ERROR {exc}"[:300], flush=True)
            continue
        record = score_case(result, case_dir, RUNS / args.tag / manifest["id"])
        report["cases"].append(record)
        gates = record.get("accepted_gates") or {}
        print(f"   score={record.get('score')} success={record.get('success')} "
              f"gates={ {k: int(bool(v)) for k, v in gates.items()} } "
              f"ratios={record.get('extent_ratios_vs_gt')} ({time.monotonic()-started:.0f}s)", flush=True)
    target = ROOT / f"pipeline-report-{args.tag}.json"
    target.write_text(json.dumps(report, indent=2) + "\n")
    done = [c for c in report["cases"] if "error" not in c]
    ok = sum(1 for c in done if c.get("success"))
    print(f"\n{ok}/{len(done)} succeeded; {sum(1 for c in done if c.get('accepted_gates') and all(c['accepted_gates'].values()))} accepted all-gates. Report: {target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
