"""Cross-branch A/B arm: drive ONE product checkout through /api/generate.

Same image bytes, same form fields, same model endpoint on every arm — the
only variable is the product code the uvicorn subprocess runs (cwd=repo).
Per cell: raw.json (full job poll incl. result) + row.json (normalized).
After both arms finish, score.py re-scores every raw.json offline with one
evaluator, so verdicts come from a single judge reading two students.

Usage: ab_arm.py --repo <checkout> --port <p> --cases a,b,c --trials 3
                 --out <dir> --side <label> [--python <exe>]
"""
from __future__ import annotations
import argparse, json, os, subprocess, sys, time
from pathlib import Path

import httpx


def parse_args():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", required=True)
    ap.add_argument("--port", type=int, required=True)
    ap.add_argument("--cases", required=True)
    ap.add_argument("--trials", type=int, default=3)
    ap.add_argument("--out", required=True)
    ap.add_argument("--side", required=True)
    ap.add_argument("--python", default=sys.executable)
    return ap.parse_args()


def drive(client, drawing: Path, tag: str) -> dict:
    with drawing.open("rb") as fh:
        response = client.post(
            "/api/generate",
            files={"image": ("drawing.png", fh.read(), "image/png")},
            data={"dimension": "", "primary_view": "front",
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
    repo = Path(args.repo).resolve()
    out = Path(args.out) / args.side
    out.mkdir(parents=True, exist_ok=True)
    case_dirs = sorted(d for d in (repo / "benchmarks" / "cases").iterdir()
                       if (d / "manifest.json").exists() and d.name in args.cases.split(","))
    assert len(case_dirs) == len(args.cases.split(",")), "missing staged cases"
    # identical image bytes across arms: pin every drawing's sha256 in the log
    import hashlib
    for d in case_dirs:
        print("SHA", d.name, hashlib.sha256((d / "source" / "drawing.png").read_bytes()).hexdigest()[:16], flush=True)
    server_log = (out / "server.log").open("wb")
    env = dict(os.environ, DOODLE_LLM_CACHE="")  # cacheless both arms
    server = subprocess.Popen([args.python, "-m", "uvicorn", "doodle_to_cad.app:app",
                               "--host", "127.0.0.1", "--port", str(args.port), "--log-level", "warning"],
                              cwd=str(repo), stdout=server_log, stderr=subprocess.STDOUT, env=env)
    base = f"http://127.0.0.1:{args.port}"
    accepted = 0
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
        print("HEALTH", args.side, httpx.get(base + "/api/health", timeout=5).text[:120], flush=True)
        client = httpx.Client(base_url=base, timeout=60)
        for case_dir in case_dirs:
            for trial in range(1, args.trials + 1):
                cell = out / case_dir.name / f"trial-{trial}"
                if (cell / "row.json").exists():
                    print(f"SKIP  {case_dir.name} t{trial}", flush=True)
                    row = json.loads((cell / "row.json").read_text())
                    accepted += bool(row.get("accepted"))
                    continue
                cell.mkdir(parents=True, exist_ok=True)
                started = time.monotonic()
                try:
                    poll = drive(client, case_dir / "source" / "drawing.png", f"{args.side} {case_dir.name} t{trial}")
                except Exception as exc:  # noqa: BLE001
                    poll = {"status": "error", "error": f"{type(exc).__name__}: {exc}"}
                (cell / "raw.json").write_text(json.dumps(poll))
                result = poll.get("result") or {}
                evaluation = result.get("evaluation") or {}
                health = result.get("mesh_health") or {}
                gates = evaluation.get("gates") or evaluation.get("mandatory_gates") or {}
                row = {"side": args.side, "case": case_dir.name, "trial": trial,
                       "status": poll.get("status"),
                       "success": result.get("success"),
                       "accepted": evaluation.get("accepted"),
                       "score": evaluation.get("score"),
                       "gates": gates,
                       "health": {k: health.get(k) for k in
                                  ("watertight", "components", "extents_mm", "volume_mm3",
                                   "genus_total", "inverted_solids") if health.get(k) is not None},
                       "run_id": result.get("id"),
                       "wall_seconds": round(time.monotonic() - started, 1)}
                (cell / "row.json").write_text(json.dumps(row))
                accepted += bool(row.get("accepted"))
                print(f"DONE  {case_dir.name} t{trial}: accepted={row['accepted']} "
                      f"score={row['score']} gates_fail={[k for k,v in gates.items() if v is False]} "
                      f"{row['wall_seconds']}s", flush=True)
    finally:
        server.terminate()
        try:
            server.wait(timeout=10)
        except Exception:
            server.kill()
    print(f"SUMMARY {args.side}: accepted {accepted}/{len(case_dirs) * args.trials}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
