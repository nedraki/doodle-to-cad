# Issue #67 rerunnable audit: verifies every measured claim in README.md.
# Usage: cd <repo root> && .venv/bin/python docs/brep/issue-67-registration/audit.py
# Exits non-zero on any failed claim. Only stdlib + repo code + subprocesses.
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
DOSSIER = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))

CHECKS: list[tuple[str, bool, str]] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    CHECKS.append((name, bool(ok), detail))
    print(f"{'PASS' if ok else 'FAIL'}  {name}" + (f"  [{detail}]" if detail else ""))


def main() -> int:
    import cv2
    import numpy as np

    from doodle_to_cad.evaluation import _crop_internal_profile_count, assign_view_groups
    from doodle_to_cad.geometry import analyze_image
    import test_view_registration as tvr

    # ---- 1. motor-103 sheet-level registration -----------------------------
    drawing = (ROOT / "benchmarks/cases/103_y_motor_holder/source/drawing.png").read_bytes()
    evidence, _ = analyze_image(drawing)
    check("case-103 sheet registers 4 internal profiles",
          evidence["closed_internal_profile_count"] == 4,
          f"got {evidence['closed_internal_profile_count']}")
    orphans = [s for s in evidence["closed_internal_profiles"] if s.get("orphan_opening_ring")]
    check("case-103 has exactly 2 orphan rings (the hook-elevation pair)",
          len(orphans) == 4 - 2 and all(s["hierarchy_depth"] == 0 for s in orphans),
          f"{len(orphans)} orphans")
    check("pre-fix sheet rule would have counted only 2",
          tvr._old_sheet_count(evidence) == 2, f"old rule -> {tvr._old_sheet_count(evidence)}")

    # ---- 2. registered crop counts ------------------------------------------
    image = cv2.imdecode(np.frombuffer(drawing, np.uint8), cv2.IMREAD_COLOR)
    h, w = image.shape[:2]
    groups = assign_view_groups(evidence, "front", "third-angle")
    crops, old_crops = {}, {}
    for direction, group in groups.items():
        x, y, gw, gh = group["bbox_normalized"]
        crop = image[int(y * h):int((y + gh) * h), int(x * w):int((x + gw) * w)]
        crops[direction] = _crop_internal_profile_count(crop)
        old_crops[direction] = tvr._old_crop_count(crop)
    check("crop counts front=0 top=2 right=2", crops == {"front": 0, "top": 2, "right": 2}, str(crops))
    check("sum of registered crop counts == sheet total (4 == 4)",
          sum(crops.values()) == evidence["closed_internal_profile_count"] == 4, str(crops))
    check("pre-fix crop rule summed to 2 (hook pair lost)",
          sum(old_crops.values()) == 2, str(old_crops))

    # ---- 3. planted synthetic fixture fails without the fix ------------------
    sheet, _ = analyze_image(tvr._hook_sheet())
    check("planted fixture: old sheet rule counts 2 of 4", tvr._old_sheet_count(sheet) == 2)
    check("planted fixture: fixed sheet rule counts 4", sheet["closed_internal_profile_count"] == 4)
    hook = assign_view_groups(sheet, "front", "third-angle")["front"]
    img = cv2.imdecode(np.frombuffer(tvr._hook_sheet(), np.uint8), cv2.IMREAD_COLOR)
    x, y, gw, gh = hook["bbox_normalized"]
    hook_crop = img[int(y * 768):int((y + gh) * 768), int(x * 1024):int((x + gw) * 1024)]
    check("planted fixture: hook view old crop rule = 0 (planted error present)",
          tvr._old_crop_count(hook_crop) == 0)
    check("planted fixture: hook view fixed crop rule = 2",
          _crop_internal_profile_count(hook_crop) == 2)

    # ---- 4. offline acceptance: motor-103 live re-score ----------------------
    live_rows = [json.loads(l) for l in
                 (ROOT / "docs/brep/issue-62-gate/data/runs-live-newgate.jsonl").read_text().splitlines()]
    motor = next(r for r in live_rows if r["drawing"] == "motor-103-accepted")
    check("motor-103 demanded_openings.total == 4 (field path: row['demanded_openings']['total'])",
          motor["demanded_openings"]["total"] == 4, str(motor["demanded_openings"]))
    check("motor-103 demanded per_view == {front:0, top:2, right:2}",
          motor["demanded_openings"]["per_view"] == {"front": 0, "top": 2, "right": 2},
          str(motor["demanded_openings"]["per_view"]))
    check("motor-103 registration gap closed (gap == 0, sheet_total == 4)",
          motor["demanded_openings"]["registration_gap"] == 0
          and motor["demanded_openings"]["sheet_total"] == 4)
    check("motor-103 now REJECTED with 2 of 4 bores (was accepted at 95.8)",
          motor["old_accepted"] is False and motor["through_holes"] == 2,
          f"accepted={motor['old_accepted']} score={motor['old_score']}")
    check("motor-103 openings_through and features gates both fire",
          motor["gates"]["openings_through"] is False and motor["gates"]["features"] is False)
    baseline = next(json.loads(l) for l in
                    (DOSSIER / "data/runs-live-baseline.jsonl").read_text().splitlines()
                    if "motor-103-accepted" in l)
    check("baseline (pre-fix) motor crop counts summed to 2 (right=0)",
          sum(t["crop"] for t in baseline["profile_topology"].values()) == 2
          and baseline["profile_topology"]["right"]["crop"] == 0,
          str(baseline["profile_topology"]))
    check("baseline motor was accepted", baseline["old_accepted"] is True)

    # ---- 5. frozen 80-row corpus: no regressions -----------------------------
    base_rows = [json.loads(l) for l in
                 (DOSSIER / "data/runs-newgate-base-24946c7.jsonl").read_text().splitlines()]
    new_rows = [json.loads(l) for l in
                (ROOT / "docs/brep/issue-62-gate/data/runs-newgate.jsonl").read_text().splitlines()]
    check("frozen corpus has 80 rows in both runs", len(base_rows) == len(new_rows) == 80)
    flips, crop_changes, demand_changes = [], [], []
    for b, n in zip(base_rows, new_rows):
        key = (b["drawing"], b["backend"], b["trial"])
        if b.get("old_accepted") != n.get("old_accepted"):
            flips.append(key)
        bc = {d: t["crop"] for d, t in (b.get("profile_topology") or {}).items()}
        nc = {d: t["crop"] for d, t in (n.get("profile_topology") or {}).items()}
        if bc != nc:
            crop_changes.append((key, bc, nc))
        if b.get("profile_topology"):
            old_demand = max((t["crop"] for t in (b["profile_topology"]).values()), default=0)
            new_demand = (n.get("demanded_openings") or {}).get("total")
            if new_demand != old_demand:
                demand_changes.append((key, old_demand, new_demand))
    trusted_base = {(r["drawing"], r["backend"], r["trial"]): r["old_accepted"]
                    for r in base_rows if r.get("trusted")}
    trusted_new = {(r["drawing"], r["backend"], r["trial"]): r["old_accepted"]
                   for r in new_rows if r.get("trusted")}
    check("frozen: zero verdict flips on all 80 rows", not flips, str(flips))
    check("frozen: zero crop-count changes on all 80 rows", not crop_changes, str(crop_changes[:3]))
    check("frozen: zero demanded-count changes (new total == old best-view max)",
          not demand_changes, str(demand_changes[:3]))
    check("frozen: 26 trusted rows, identical verdicts",
          len(trusted_base) == 26 and trusted_base == trusted_new)

    # ---- 6. tests -------------------------------------------------------------
    unit = subprocess.run([sys.executable, "-m", "pytest", "-q", "tests/test_view_registration.py"],
                          capture_output=True, text=True, cwd=ROOT,
                          env={**__import__("os").environ, "PYTHONPATH": "."})
    check("tests/test_view_registration.py: 12 passed",
          "12 passed" in unit.stdout, unit.stdout.splitlines()[-1] if unit.stdout else unit.stderr[-200:])
    suite = subprocess.run([sys.executable, "-m", "pytest", "-q"],
                           capture_output=True, text=True, cwd=ROOT,
                           env={**__import__("os").environ, "PYTHONPATH": ".",
                                "DOODLE_BREP_PYTHON": str(ROOT / "workers/brep/.venv/bin/python")})
    check("full suite: 304 passed, 2 warnings",
          "304 passed" in suite.stdout and "2 warnings" in suite.stdout,
          suite.stdout.splitlines()[-1] if suite.stdout else suite.stderr[-200:])

    # ---- 7. environment -------------------------------------------------------
    env = json.loads((DOSSIER / "environment.json").read_text())
    check("environment.json records worker usd-brep version (no __version__ attr)",
          env["worker"]["usd-brep"] == "1.0.0" and env["worker"]["usd_brep_has_dunder_version"] is False)
    check("environment.json records base commit", env.get("base_commit") == "24946c7")

    failed = [name for name, ok, _ in CHECKS if not ok]
    print(f"\naudit: {len(CHECKS) - len(failed)}/{len(CHECKS)} checks passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
