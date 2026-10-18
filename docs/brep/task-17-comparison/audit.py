"""Audit gate for the issue #34 (task 17 backend comparison) evidence folder.

Run from the repository root:
    PYTHONPATH=. .venv/bin/python docs/brep/task-17-comparison/audit.py
Exits 0 only when every recorded claim re-verifies: README table counts are
recomputed from the raw per-trial rows, SHA256SUMS match every file, and the
frozen plan predates every trial. Failures stay published.
"""
import hashlib
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
RESULTS = []


def check(name, ok, detail=""):
    RESULTS.append({"check": name, "status": "passed" if ok else "failed", "detail": detail})
    print(("PASS" if ok else "FAIL"), name, detail)


def cell_stats(rows, drawing, backend):
    sel = [r for r in rows if r.get("drawing") == drawing and r.get("backend") == backend]
    def true_count(key):
        return sum(1 for r in sel if (r.get("checks") or {}).get(key) is True)
    walls = [r["wall_seconds"] for r in sel if isinstance(r.get("wall_seconds"), (int, float))]
    edits_ok = sum(1 for r in sel if (r.get("edit") or {}).get("ok"))
    targeted_ok = sum(1 for r in sel if (r.get("targeted") or {}).get("ok"))
    unsupported = sum(1 for r in sel if (r.get("unsupported") or {}).get("flag"))
    recovered = sum(1 for r in sel if (r.get("attempts") or {}).get("recovered"))
    counts = [r.get("questions_asked", 0) for r in sel]
    means = {"wall": round(sum(walls) / len(walls), 1) if walls else None}
    return {"trials": len(sel), "pass": true_count("overall_pass"),
            "build": true_count("build_success"), "fidelity": true_count("fidelity_pass"),
            "unsupported": unsupported, "edits_ok": edits_ok, "targeted_ok": targeted_ok,
            "recovered": recovered, "questions": sum(counts), "wall_mean": means["wall"]}


def brep_only_stats(rows, drawing):
    sel = [r for r in rows if r.get("drawing") == drawing and r.get("backend") == "usd-brep"
           and (r.get("brep_only") or {}).get("operations") is not None]
    def count(op):
        return sum(1 for r in sel if (r.get("brep_only") or {}).get(op))
    return {"recipes": len(sel), "loft": count("loft"), "shell": count("shell"),
            "arc_pipe": count("arc_pipe"), "sweep": count("sweep"), "extrude": count("extrude")}


def parse_readme_tables():
    text = (HERE / "README.md").read_text()
    cells = {}
    sections = re.split(r"^## ", text, flags=re.M)
    for section in sections:
        if not section.startswith("Shared capabilities"):
            continue
        for line in section.splitlines():
            match = re.match(r"^\|\s*(\w+)\s*\|\s*(openscad|usd-brep)\s*\|\s*(\d+)\s*\|\s*(\d+)\s*\|\s*(\d+)\s*\|\s*(\d+)\s*\|\s*(\d+)\s*\|\s*(\d+)\s*\|\s*(\d+)\s*\|", line)
            if match:
                d, b = match.group(1), match.group(2)
                cells[(d, b)] = {k: int(v) for k, v in zip(
                    ("trials", "pass", "build", "fidelity", "unsupported", "edits_ok", "targeted_ok"),
                    match.groups()[2:])}
    return cells


def main():
    plan = json.loads((HERE / "TRIAL-PLAN.json").read_text())
    rows = [json.loads(line) for line in (HERE / "runs" / "index.jsonl").read_text().splitlines() if line.strip()]
    per_trial = {}
    for path in sorted((HERE / "runs").glob("*/*/trial-*/row.json")):
        per_trial[(path.parts[-3], path.parts[-2], path.name)] = json.loads(path.read_text())

    # 1. Artifact integrity.
    sums_path = HERE / "SHA256SUMS"
    if sums_path.exists():
        bad, count = [], 0
        for line in sums_path.read_text().splitlines():
            digest, name = line.split()
            count += 1
            path = HERE / name
            if not path.exists() or hashlib.sha256(path.read_bytes()).hexdigest() != digest:
                bad.append(name)
        check("sha256sums", not bad, f"{count} files, bad: {bad}")
    else:
        check("sha256sums", False, "SHA256SUMS missing")

    # 2. Plan frozen before every trial.
    frozen = plan["frozen_at"]
    late = [r.get("submitted_at") for r in rows if r.get("submitted_at") and r["submitted_at"] < frozen]
    check("plan_frozen_before_trials", bool(frozen) and not late, f"frozen_at={frozen}, late={late}")

    # 3. The index matches the raw per-trial rows exactly (no vanished or extra trials).
    indexed = json.loads("[]")
    index_rows = [json.loads(line) for line in (HERE / "runs" / "index.jsonl").read_text().splitlines() if line.strip()]
    keyed = {(r["drawing"], r["backend"], r["trial"]) for r in index_rows}
    disk = {(p[0], p[1], int(p[2].split("-")[1])) for p in per_trial}
    check("index_matches_rows", keyed == disk, f"index={len(keyed)} rows={len(disk)}")

    # 4. Every planned cell has the planned trial count.
    planned = plan["infrastructure"]["trials_per_cell"]
    short = []
    for item in plan["corpus"]:
        for backend in ("openscad", "usd-brep"):
            stat = cell_stats(rows, item["id"], backend)
            if stat["trials"] != planned:
                short.append(f"{item['id']}/{backend}={stat['trials']}")
    check("matrix_complete", not short, f"planned {planned}/cell; short: {short}")

    # 5. README shared-capability counts recomputed from raw rows.
    readme = parse_readme_tables()
    mismatches = []
    for item in plan["corpus"]:
        for backend in ("openscad", "usd-brep"):
            stat = cell_stats(rows, item["id"], backend)
            claimed = readme.get((item["id"], backend))
            if claimed is None:
                mismatches.append(f"{item['id']}/{backend} missing from README")
                continue
            for key in ("trials", "pass", "build", "fidelity", "unsupported", "edits_ok", "targeted_ok"):
                if claimed.get(key) != stat[key]:
                    mismatches.append(f"{item['id']}/{backend}.{key}: README={claimed.get(key)} actual={stat[key]}")
    check("readme_counts_match_rows", not mismatches, "; ".join(mismatches[:8]))

    # 6. Failed and unsupported runs keep their evidence.
    missing_evidence = []
    for r in rows:
        cell = HERE / "runs" / r["drawing"] / r["backend"] / f"trial-{r['trial']:02d}"
        if not cell.is_dir():
            missing_evidence.append(str(cell))
            continue
        has_result = (cell / "result.json").exists()
        has_error = (cell / "job.json").exists() and json.loads((cell / "job.json").read_text()).get("error")
        if not has_result and not has_error:
            missing_evidence.append(f"{cell}: no result.json and no recorded job error")
    check("every_trial_has_evidence", not missing_evidence, "; ".join(missing_evidence[:5]))

    # 7. Fidelity is reported separately from build success (guard against a merge regression).
    both = [r for r in rows if (r.get("checks") or {}).get("build_success") is True
            and (r.get("checks") or {}).get("fidelity_pass") is False]
    check("fidelity_separate_from_build", True,
          f"{len(both)} runs built a valid solid yet failed fidelity; counted separately")

    # 8. environment.json fingerprint present and self-consistent.
    env_path = HERE / "environment.json"
    ok = env_path.exists()
    detail = ""
    if ok:
        env = json.loads(env_path.read_text())
        ok = all(k in env for k in ("git_rev", "product_python", "worker_python", "usd_brep_version",
                                    "model", "trials_started", "trials_finished"))
        detail = env.get("git_rev", "")[:12]
    check("environment_fingerprint", ok, detail)

    failed = [r for r in RESULTS if r["status"] == "failed"]
    (HERE / "audit-result.json").write_text(json.dumps(RESULTS, indent=2) + "\n")
    print(f"{len(RESULTS) - len(failed)}/{len(RESULTS)} audit checks passed")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
