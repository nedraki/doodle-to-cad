"""One-judge scorer for the cross-branch A/B (ab_arm.py output).

Both arms' archived SCADs are recompiled and re-rendered with the SAME
quality-side compiler/renderer and judged by the SAME evaluate_candidate,
using the quality arm's interpretation evidence for the case. That way a
verdict difference means the PART differs, not the grader.

Run from the main-quality checkout (its code is the judge):
  uv run python -u scripts/ab_score.py --dir <ab-out> --cases a,b,c
"""
from __future__ import annotations
import argparse, json, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from doodle_to_cad.config import Settings          # noqa: E402
from doodle_to_cad.evaluation import assign_view_groups, evaluate_candidate  # noqa: E402
from doodle_to_cad.geometry import analyze_image, label_view_geometry  # noqa: E402
from doodle_to_cad.openscad import compile_and_render, mesh_health  # noqa: E402

CASES = ["200_rocket", "201_person", "202_lamp", "203_scooter",
         "204_flower", "205_mug", "206_car_ink"]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", required=True)
    ap.add_argument("--cases", default=",".join(CASES))
    ap.add_argument("--trials", type=int, default=3)
    args = ap.parse_args()
    root = Path(args.dir)
    settings = Settings()
    cases = args.cases.split(",")
    judge_dir = root / "judge"; judge_dir.mkdir(exist_ok=True)

    # rubric: deterministic OpenCV evidence per case (no LLM involved) —
    # identical reference measurement for both students
    rubric = {}
    for case in cases:
        source = (Path("/home/sparkie/playground/d2c-main-quality/benchmarks/cases")
                  / case / "source" / "drawing.png").read_bytes()
        evidence, _overlay = analyze_image(source)
        assigned = assign_view_groups(evidence, "front", "third-angle")
        rubric[case] = {"evidence": label_view_geometry(evidence, assigned),
                        "spec": json.loads((root / "quality" / case / "trial-1" / "raw.json")
                                           .read_text()).get("result", {}).get("spec") or {},
                        "source": source}

    rows = []
    for case in cases:
        source = rubric[case]["source"]
        for side in ("main", "quality"):
            for trial in range(1, args.trials + 1):
                cell = root / side / case / f"trial-{trial}"
                raw_path = cell / "raw.json"
                if not raw_path.exists():
                    continue
                result = (json.loads(raw_path.read_text()).get("result")) or {}
                attempts = result.get("attempts") or []
                sel = result.get("selected_attempt")
                attempt = next((a for a in attempts if a.get("attempt") == sel),
                               attempts[-1] if attempts else {})
                run_root = Path("/home/sparkie/playground") / (
                    "d2c-ab-main" if side == "main" else "d2c-main-quality") / "results" / str(result.get("id"))
                if not run_root.exists():  # same-repo A/B arms: both runs live here
                    run_root = Path("/home/sparkie/playground/d2c-main-quality/results") / str(result.get("id"))
                scad_rel = (attempt.get("files") or {}).get("scad") or (result.get("files") or {}).get("scad")
                scad = None
                if scad_rel:
                    cand = Path(scad_rel)
                    for guess in (cand, run_root / scad_rel,
                                  run_root / cand.name if cand.match("*/model.scad") else None):
                        if guess and guess.exists():
                            scad = guess
                            break
                if not scad or not scad.exists():
                    rows.append({"side": side, "case": case, "trial": trial,
                                 "judge_accepted": False, "judge_note": "scad-missing"})
                    continue
                jd = judge_dir / f"{side}-{case}-t{trial}"; jd.mkdir(parents=True, exist_ok=True)
                local_scad = jd / "model.scad"
                local_scad.write_text(scad.read_text())  # docker shim mounts one tree as /work
                stl, views, _log = compile_and_render(local_scad, jd, settings.openscad_bin)
                if stl is None:  # surface the compiler log instead of hiding it
                    (jd / "compile.log").write_text(_log)
                    print(f"JUDGE {side:7s} {case:12s} t{trial}: COMPILE-FAIL {_log[-160:]}", flush=True)
                health = mesh_health(stl) if stl else None
                ev = evaluate_candidate(
                    stl=stl, health=health, scad=scad.read_text(), views=views,
                    source=source, evidence=rubric[case]["evidence"],
                    spec=rubric[case]["spec"], target_dimension="", strict=True)
                row = {"side": side, "case": case, "trial": trial,
                       "judge_accepted": bool(ev.get("accepted")),
                       "judge_verified": bool(ev.get("verified_acceptance")),
                       "judge_score": ev.get("score"),
                       "states": ev.get("gate_states") or ev.get("gates_state") or {},
                       "failures": (ev.get("failures") or [])[:2],
                       "own_accepted": (json.loads((cell / "row.json").read_text())
                                         if (cell / "row.json").exists() else {}).get("accepted")}
                (cell / "judged.json").write_text(json.dumps(row))
                rows.append(row)
                print(f"JUDGE {side:7s} {case:12s} t{trial}: accepted={row['judge_accepted']} "
                      f"verified={row['judge_verified']} own={row['own_accepted']} "
                      f"fail={row['failures']}", flush=True)

    print("\n=== matrix (judge = main-quality evaluator, same rubric) ===")
    for case in cases:
        line = [case]
        for side in ("main", "quality"):
            n = sum(1 for r in rows if r["side"] == side and r["case"] == case)
            a = sum(1 for r in rows if r["side"] == side and r["case"] == case and r["judge_accepted"])
            v = sum(1 for r in rows if r["side"] == side and r["case"] == case and r.get("judge_verified"))
            line.append(f"{side} {a}/{n}acc {v}/{n}ver")
        print("  " + " | ".join(line))
    for side in ("main", "quality"):
        n = sum(1 for r in rows if r["side"] == side)
        a = sum(1 for r in rows if r["side"] == side and r["judge_accepted"])
        v = sum(1 for r in rows if r["side"] == side and r.get("judge_verified"))
        own = sum(1 for r in rows if r["side"] == side and r.get("own_accepted"))
        print(f"TOTAL {side}: judge-accepted {a}/{n}, judge-verified {v}/{n}, own-accepted {own}/{n}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
