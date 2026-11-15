"""Resumable quality trials over the benchmark cases (ported from the BRep
branch's evaluate_brep.py discipline, adapted to the OpenSCAD product).

One cell = case x trial. A cell is COMPLETE when its verdict.json exists and
parses — reruns skip completed cells, so an interrupted campaign resumes.
Every cell records the machine fingerprint of the code that produced it; the
run records environment.json once. GT checks are numeric only (extents,
components, gates) — no prose verdicts.

Usage (always under the jail):
  scripts/run_jailed.sh -m 12G -t 5400 -- uv run python scripts/evaluate_quality.py \
      --cases 004_flat_mounting_plate --trials 1 [--cache DIR]
"""
from __future__ import annotations

import argparse
import httpx
import json
import os
import platform
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from doodle_to_cad.config import settings  # noqa: E402  (loads .env)
from doodle_to_cad.pipeline import build_fingerprint  # noqa: E402


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cases", default="", help="comma-separated case ids; empty = all")
    ap.add_argument("--trials", type=int, default=1)
    ap.add_argument("--out", default=str(ROOT / "benchmarks" / "runs"))
    ap.add_argument("--run", default="", help="resume a named run dir under --out instead of a new timestamp")
    ap.add_argument("--cache", default=os.getenv("DOODLE_LLM_CACHE", ""),
                    help="reply-cache dir (empty = no cache for this campaign)")
    ap.add_argument("--port", type=int, default=8123)
    ap.add_argument("--dimension-from-gt", action="store_true", default=True,
                    help="pass the GT max extent as the user dimension target")
    return ap.parse_args()


def cases(root: Path, wanted: str) -> list[Path]:
    ids = [c.strip() for c in wanted.split(",") if c.strip()]
    dirs = sorted(d for d in root.iterdir() if (d / "manifest.json").exists())
    return [d for d in dirs if not ids or d.name in ids]


def gt_stl_metrics(case_dir: Path) -> dict:
    """Authoritative numeric GT from the reference STL, not manifest prose.

    Genus is summed per watertight component (a multi-solid GT gives nonsense
    on the whole-mesh Euler); extents are sorted descending so an axis-order
    flip between GT model coordinates and the built part cannot fake a pass.
    """
    stl = case_dir / "ground_truth" / "model.stl"
    if not stl.exists():
        return {}
    try:
        import trimesh
        mesh = trimesh.load(str(stl), force="mesh")
        comps = list(mesh.split()) or [mesh]
        open_comps = sum(1 for c in comps if not c.is_watertight)
        genus = sum(max((2 - int(c.euler_number)) // 2, 0)
                    for c in comps if c.is_watertight)
        return {"gt_genus": genus, "gt_components": len(comps),
                "gt_nonwatertight_components": open_comps,
                "gt_volume_mm3": round(float(mesh.volume), 1),
                "gt_stl_extents_sorted": [round(v, 2) for v in sorted(mesh.extents, reverse=True)]}
    except Exception as exc:  # noqa: BLE001 — a broken GT must not kill the sweep
        return {"gt_error": f"{type(exc).__name__}: {exc}"}


def _volume_ratio_pass(built_v: float | None, gt_v: float | None, tol: float = 0.25) -> bool | None:
    """Material truth: a filled block where an L-bracket belongs passes every
    silhouette check but uses 6x the material. One number, no prose."""
    if not built_v or not gt_v or gt_v <= 0:
        return None
    return abs(built_v / gt_v - 1.0) <= tol


def verdict_genus_pass(genus_total: int | None, gtm: dict) -> bool | None:
    """Genus vs GT only when BOTH sides are measurable closed solids."""
    gt_g = gtm.get("gt_genus")
    if genus_total is None or gt_g is None or gtm.get("gt_nonwatertight_components"):
        return None
    return genus_total == gt_g


def _axiswise_dims_pass(ext: list | None, gt_sorted: list | None, tol: float = 0.10) -> bool | None:
    """Sorted-descending per-axis compare; axes under 2 mm are not measured."""
    if not ext or not gt_sorted or len(ext) != 3 or len(gt_sorted) != 3:
        return None
    a = sorted((float(v) for v in ext), reverse=True)
    b = sorted((float(v) for v in gt_sorted), reverse=True)
    pairs = [(x, y) for x, y in zip(a, b) if y >= 2.0]
    if not pairs:
        return None
    return all(abs(x - y) / y <= tol for x, y in pairs)


def drive(client: httpx.Client, drawing: Path, dimension_target: str, tag: str = "") -> dict:
    with drawing.open("rb") as fh:
        response = client.post(
            "/api/generate",
            files={"image": ("drawing.png", fh.read(), "image/png")},
            data={"dimension": dimension_target, "primary_view": "front",
                  "projection_standard": "third-angle", "strict_watertight": "true",
                  "view_directions": "[]", "refine_mode": "regularize"},
        )
    response.raise_for_status()
    job_id = response.json()["job_id"]
    deadline = time.monotonic() + 2400
    last = None
    while time.monotonic() < deadline:
        poll = client.get(f"/api/generate/{job_id}").json()
        cur = (poll.get("status"), poll.get("stage"))
        if cur != last:
            print(f"      [{tag}] {cur[0]}/{cur[1]}", flush=True)
            last = cur
        if cur[0] in {"done", "error", "cancelled"}:
            return poll
        time.sleep(2)
    raise TimeoutError(f"job {job_id} did not finish")


def main() -> int:
    args = parse_args()
    if args.cache:
        os.environ["DOODLE_LLM_CACHE"] = args.cache

    stamp = time.strftime("%Y%m%d-%H%M%S")
    run_dir = Path(args.out) / (args.run or f"quality-{stamp}")
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "environment.json").write_text(json.dumps({
        "fingerprint": build_fingerprint(settings),
        "python": platform.python_version(),
        "model_endpoint": settings.base_url,
        "requested_model": settings.requested_model or "auto",
        "llm_cache_dir": args.cache or None,
        "agent_max_attempts": settings.agent_max_attempts,
    }, indent=2))

    # Drive the REAL server: TestClient's anyio request scope cancels the job
    # task spawned via asyncio.create_task the moment POST returns — only a
    # real uvicorn process keeps background jobs alive, and driving the real
    # process is what actually proves the product path.
    port = args.port
    server_log = (run_dir / "server.log").open("ab")
    server = subprocess.Popen([sys.executable, "-m", "uvicorn", "doodle_to_cad.app:app",
                               "--host", "127.0.0.1", "--port", str(port), "--log-level", "warning"],
                              cwd=str(ROOT), stdout=server_log, stderr=subprocess.STDOUT)
    base = f"http://127.0.0.1:{port}"
    results: list[dict] = []
    try:
        for _ in range(60):
            try:
                if httpx.get(base + "/api/generate/nope", timeout=2).status_code in {404, 200}:
                    break
            except Exception:
                pass
            time.sleep(1)
        else:
            raise RuntimeError("uvicorn did not come up")
        client = httpx.Client(base_url=base, timeout=60)
        for case_dir in cases(ROOT / "benchmarks" / "cases", args.cases):
            manifest = json.loads((case_dir / "manifest.json").read_text())
            gt = manifest.get("reference", {}).get("dimensions_mm", {}).get("extents_xyz") or []
            gtm = gt_stl_metrics(case_dir)
            if not gt:
                gt = gtm.get("gt_stl_extents_sorted") or []
            target = str(max(gt)) if gt and args.dimension_from_gt else ""
            for trial in range(1, args.trials + 1):
                cell = run_dir / case_dir.name / f"trial-{trial}"
                if (cell / "verdict.json").exists():
                    print(f"SKIP  {case_dir.name} trial-{trial} (complete)", flush=True)
                    results.append(json.loads((cell / "verdict.json").read_text()))
                    continue
                cell.mkdir(parents=True, exist_ok=True)
                started = time.monotonic()
                try:
                    poll = drive(client, case_dir / "source" / "drawing.png", target,
                                 tag=f"{case_dir.name} t{trial}")
                except Exception as exc:  # noqa: BLE001 — harness must survive a broken run
                    poll = {"status": "error", "error": f"{type(exc).__name__}: {exc}"}
                verdict = {"case": case_dir.name, "trial": trial,
                           "wall_seconds": round(time.monotonic() - started, 1),
                           "status": poll.get("status"), "error": poll.get("error")}
                result = poll.get("result") or {}
                evaluation = result.get("evaluation") or {}
                health = result.get("mesh_health") or {}
                verdict.update({
                    "success": result.get("success"),
                    "accepted": evaluation.get("accepted"),
                    "verified_acceptance": evaluation.get("verified_acceptance"),
                    "gates_state": evaluation.get("gates_state"),
                    "unverified_gates": evaluation.get("unverified_gates"),
                    "unverified_axes": evaluation.get("unverified_axes"),
                    "warnings": evaluation.get("warnings"),
                    "projection_similarity": evaluation.get("projection_similarity"),
                    "extents_mm": health.get("extents_mm"), "gt_extents_mm": gt or None,
                    "genus_total": health.get("genus_total"),
                    "inverted_solids": health.get("inverted_solids"),
                    **gtm,
                    "checks": {
                        "genus_pass": (verdict_genus_pass(health.get("genus_total"), gtm)),
                        "dims_axiswise_pass": _axiswise_dims_pass(
                            health.get("extents_mm"), gtm.get("gt_stl_extents_sorted")),
                        "volume_ratio_pass": _volume_ratio_pass(
                            health.get("volume_mm3"), gtm.get("gt_volume_mm3")),
                    },
                    "selected_attempt": result.get("selected_attempt"),
                    "cache_stats": result.get("llm_cache"),
                    "fingerprint": result.get("fingerprint"),
                    "run_id": result.get("id"),
                })
                (cell / "result.json").write_text(json.dumps(result, indent=2))
                (cell / "verdict.json").write_text(json.dumps(verdict, indent=2))
                print(f"DONE  {case_dir.name} trial-{trial}: status={verdict['status']} "
                      f"accepted={verdict['accepted']} verified={verdict['verified_acceptance']} "
                      f"unverified={verdict['unverified_gates']} {verdict['wall_seconds']}s "
                      f"cache={verdict['cache_stats']}", flush=True)
                results.append(verdict)
    finally:
        server.terminate()
        try:
            server.wait(timeout=10)
        except subprocess.TimeoutExpired:
            server.kill()

    verified = sum(1 for r in results if r.get("verified_acceptance"))
    accepted = sum(1 for r in results if r.get("accepted"))
    print(f"\nSUMMARY cases={len(results)} accepted={accepted} verified={verified}")
    print(f"run dir: {run_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
