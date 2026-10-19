#!/usr/bin/env python3
"""Minimal deterministic reproducer for the usd_brep 1.0.0 tessellation crash (issue #61).

Crash signature: the isolated BRep worker (workers/brep/build.py) dies inside
usd_brep 1.0.0 tessellation with ``ModuleNotFoundError: No module named
'_omni_solid'`` while meshing an arc_pipe (torus-segment) body that has been
combined with cylinders by boolean union. The same arc_pipe alone, and the
same cylinders alone or unioned with each other, tessellate fine.

Usage:
  python scripts/repro_omni_solid.py                 # run the canonical minimal fixture once
  python scripts/repro_omni_solid.py --repeat 3      # determinism gate: must crash 3/3
  python scripts/repro_omni_solid.py --case arc_only # control: must NOT crash
  python scripts/repro_omni_solid.py --ladder LOG    # run the full shrink ladder, write JSON log
  python scripts/repro_omni_solid.py --hash          # sha256 of the canonical fixture

Exit codes: 0 = every run behaved as expected for its mode (crash for the
reproducer, success for a control, ladder executed); 1 = unexpected behaviour.
"""
import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
WORKER = REPO / "workers" / "brep" / "build.py"
FIXTURE = REPO / "scripts" / "fixtures" / "omni_solid_minimal.recipe.json"
CRASH_SIGNATURE = "No module named '_omni_solid'"


def worker_python() -> str:
    return os.getenv("DOODLE_BREP_PYTHON", str(REPO / "workers" / "brep" / ".venv" / "bin" / "python"))


def recipe_bytes(recipe: dict) -> bytes:
    return (json.dumps(recipe, indent=2, sort_keys=True) + "\n").encode()


def fixture_hash(path: Path = FIXTURE) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


# ---------------------------------------------------------------------------
# Recipe ladder. All variants are version 1 recipes (smallest legal schema)
# unless noted; v2 variants prove the crash is not a schema artefact.
# Geometry follows the failing curved_handle trials (bend R20, pipe r4,
# 180 degrees, legs r4 x 30 mm at the arch ends).
# ---------------------------------------------------------------------------
def _pipe(oid, origin, angle=180):
    return {"id": oid, "kind": "arc_pipe", "origin": list(origin),
            "bend_radius": 20, "radius": 4, "angle": angle}


def _cyl(oid, origin, height=30):
    return {"id": oid, "kind": "cylinder", "origin": list(origin),
            "radius": 4, "height": height, "axis": "z"}


def _union(oid, left, right):
    return {"id": oid, "kind": "union", "left": left, "right": right}


def v1(name, operations, output):
    return {"version": 1, "units": "mm", "name": name,
            "parameters": {}, "operations": operations, "output": output}


def full_v2():
    """Verbatim failed payload from task-17 trial-01 (5 operations)."""
    doc = json.loads((REPO / "docs" / "brep" / "task-17-comparison" / "runs" /
                      "curved_handle" / "usd-brep" / "trial-01" / "failed" /
                      "1.recipe.json").read_text())
    return doc


def slim_v2():
    """Same 5 operations, evidence/labels/constraints stripped."""
    doc = full_v2()
    doc["parameters"] = {k: {"value": p["value"], "min": p["min"], "max": p["max"]}
                         for k, p in doc["parameters"].items()}
    for op in doc["operations"]:
        op["evidence"] = []
    doc["evidence"] = {"observed": [], "inferred": [], "assumptions": [], "unresolved": []}
    doc["constraints"] = []
    return doc


CASES = {
    # --- expected to crash -------------------------------------------------
    "canonical_fixture": (lambda: json.loads(FIXTURE.read_text()), "crash"),
    "full_v2": (full_v2, "crash"),
    "slim_v2": (slim_v2, "crash"),
    "minimal_v1": (lambda: v1("arch_leg", [_pipe("arch", (0, 0, 4)), _cyl("leg", (-20, 0, 0)),
                                           _union("part", "arch", "leg")], "part"), "crash"),
    "both_legs_v1": (lambda: v1("handle", [
        _pipe("arch", (0, 0, 4)), _cyl("leg_left", (-20, 0, 0)), _cyl("leg_right", (20, 0, 0)),
        _union("u1", "arch", "leg_left"), _union("part", "u1", "leg_right")], "part"), "crash"),
    "arc_plus_box_union": (lambda: v1("arch_box", [
        _pipe("arch", (0, 0, 4)),
        {"id": "block", "kind": "box", "origin": [-24, -4, 0], "size": [8, 8, 8]},
        _union("part", "arch", "block")], "part"), "crash"),
    "arc90_union": (lambda: v1("quarter", [
        _pipe("arch", (0, 0, 4), angle=90), _cyl("leg", (20, 0, 0)),
        _union("part", "arch", "leg")], "part"), "ok"),
    "arc135_union": (lambda: v1("arc135", [
        _pipe("arch", (0, 0, 4), angle=135), _cyl("leg", (-14.142, 14.142, 0)),
        _union("part", "arch", "leg")], "part"), "unknown"),
    "arc270_union": (lambda: v1("arc270", [
        _pipe("arch", (0, 0, 4), angle=270), _cyl("leg", (0, -20, 0)),
        _union("part", "arch", "leg")], "part"), "unknown"),
    "arc_leg_disjoint": (lambda: v1("arch_leg_far", [
        _pipe("arch", (0, 0, 4)), _cyl("leg", (60, 0, 0)),
        _union("part", "arch", "leg")], "part"), "unknown"),
    "arc_leg_other_end": (lambda: v1("arch_leg_east", [
        _pipe("arch", (0, 0, 4)), _cyl("leg", (20, 0, 0)),
        _union("part", "arch", "leg")], "part"), "unknown"),
    "arc_leg_apex": (lambda: v1("arch_leg_apex", [
        _pipe("arch", (0, 0, 4)), _cyl("leg", (0, 0, 0), height=30),
        _union("part", "arch", "leg")], "part"), "unknown"),
    "arc180_difference": (lambda: v1("arch_cut", [
        _pipe("arch", (0, 0, 4)), _cyl("cutter", (-20, 0, -5), height=10),
        {"id": "part", "kind": "difference", "left": "arch", "right": "cutter"}], "part"), "unknown"),
    "arc_leg_west_stub": (lambda: v1("arch_stub", [
        _pipe("arch", (0, 0, 4)), _cyl("leg", (-20, 0, 0), height=6),
        _union("part", "arch", "leg")], "part"), "unknown"),
    "arc_leg_west_union_flip": (lambda: v1("arch_flip", [
        _pipe("arch", (0, 0, 4)), _cyl("leg", (-20, 0, 0)),
        _union("part", "leg", "arch")], "part"), "unknown"),
    "arc_leg_west_axis_y": (lambda: v1("arch_sideways", [
        _pipe("arch", (0, 0, 4)),
        {"id": "leg", "kind": "cylinder", "origin": [-20, -8, 4], "radius": 4,
         "height": 8, "axis": "y"},
        _union("part", "arch", "leg")], "part"), "unknown"),
    # --- controls: expected to build fine ---------------------------------
    "arc_only": (lambda: v1("arch", [_pipe("arch", (0, 0, 4))], "arch"), "ok"),
    "cyl_only": (lambda: v1("leg", [_cyl("leg", (-20, 0, 0))], "leg"), "ok"),
    "two_cyl_union": (lambda: v1("legs", [
        _cyl("a", (-20, 0, 0)), _cyl("b", (20, 0, 0)), _union("part", "a", "b")], "part"), "ok"),
    "box_only": (lambda: v1("block", [
        {"id": "block", "kind": "box", "origin": [0, 0, 0], "size": [10, 10, 10]}], "block"), "ok"),
}


# ---------------------------------------------------------------------------
# Execution
# ---------------------------------------------------------------------------
def run_once(recipe: dict):
    """Run the worker entry point once. Returns (crashed, code, message, seconds)."""
    import time
    started = time.monotonic()
    with tempfile.TemporaryDirectory(prefix="repro61-") as tmp:
        source = Path(tmp) / "model.recipe.json"
        source.write_bytes(recipe_bytes(recipe))
        out = Path(tmp) / "out"
        out.mkdir()
        proc = subprocess.run([worker_python(), str(WORKER), str(source), str(out)],
                              capture_output=True, text=True, timeout=300)
        elapsed = round(time.monotonic() - started, 2)
        error_file = out / "construction-error.json"
        failure = json.loads(error_file.read_text()) if error_file.exists() else {}
        text = proc.stdout + proc.stderr + json.dumps(failure)
        crashed = CRASH_SIGNATURE in text
        code = failure.get("code", "build_failed") if proc.returncode else "ok"
        message = failure.get("message", (proc.stderr or "").strip()[-300:])
        return crashed, code, message, elapsed


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case", default=None, help=f"ladder case name: {', '.join(CASES)}")
    parser.add_argument("--recipe", default=None, help="path to a recipe JSON to run as-is")
    parser.add_argument("--repeat", type=int, default=1)
    parser.add_argument("--ladder", default=None, help="path to write the shrink-ladder JSON log")
    parser.add_argument("--hash", action="store_true", help="print sha256 of the canonical fixture and exit")
    args = parser.parse_args(argv)

    if args.hash:
        print(fixture_hash())
        return 0

    if args.ladder:
        log = {"note": "Shrink ladder for issue #61. Each step runs workers/brep/build.py "
                       "serially once. 'expected' is the characterisation claim.", "steps": []}
        failures = 0
        for name, (builder, expected) in CASES.items():
            crashed, code, message, seconds = run_once(builder())
            behaved = True if expected == "unknown" else (
                crashed if expected == "crash" else not crashed)
            failures += 0 if behaved else 1
            log["steps"].append({"case": name, "expected": expected, "crashed": crashed,
                                 "code": code, "message": message, "seconds": seconds})
            print(f"{'OK ' if behaved else 'BAD'} {name:18s} expected={expected:5s} "
                  f"crashed={crashed} code={code} ({seconds}s) {message[:80]}")
        Path(args.ladder).parent.mkdir(parents=True, exist_ok=True)
        Path(args.ladder).write_text(json.dumps(log, indent=2) + "\n")
        print(f"ladder log: {args.ladder} ({failures} misbehaving steps)")
        return 1 if failures else 0

    if args.recipe:
        recipe = json.loads(Path(args.recipe).read_text())
        expected = "crash"
    elif args.case:
        builder, expected = CASES[args.case]
        recipe = builder()
    else:
        recipe, expected = json.loads(FIXTURE.read_text()), "crash"

    results = []
    for i in range(args.repeat):
        crashed, code, message, seconds = run_once(recipe)
        results.append({"trial": i + 1, "crashed": crashed, "code": code,
                        "message": message, "seconds": seconds})
        print(f"trial {i + 1}: crashed={crashed} code={code} ({seconds}s) {message}")
    as_expected = sum(1 for r in results if (r["crashed"] if expected == "crash" else not r["crashed"]))
    print(f"verdict: {as_expected}/{args.repeat} behaved as expected (expected={expected}, "
          f"signature={CRASH_SIGNATURE!r})")
    return 0 if as_expected == args.repeat else 1


if __name__ == "__main__":
    sys.exit(main())
