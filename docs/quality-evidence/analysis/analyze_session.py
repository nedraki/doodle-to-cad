"""Cross-campaign session analysis: one table from every verdict.json the
quality harness produced this session, ranked failure causes, so the next
improvement step is chosen from measured frequencies, not vibes.

Usage: python analyze_session.py <repo_root> <run_dir> [<run_dir> ...]
Outputs a JSON summary + printed matrix. Deterministic; no LLM.
"""
from __future__ import annotations
import json, sys
from collections import Counter, defaultdict
from pathlib import Path


def load_cells(run_dir: Path):
    for cd in sorted(run_dir.iterdir()):
        if not (cd / "trial-1" / "verdict.json").exists():
            continue
        for tf in sorted(cd.glob("trial-*")):
            vp = tf / "verdict.json"
            if vp.exists():
                v = json.loads(vp.read_text())
                v["_case"], v["_trial"], v["_run"] = cd.name, tf.name, run_dir.name
                yield v


def main() -> int:
    repo = Path(sys.argv[1])
    runs = [Path(p) for p in sys.argv[2:]]
    cells = [c for r in runs for c in load_cells(r)]
    # dedupe: variance run reused run-dir names; key on (case, run-dir, trial)
    uniq = {(c["_case"], c["_run"], c["_trial"]): c for c in cells}
    cells = list(uniq.values())
    gate_states = Counter()
    fail_causes = Counter()          # among rejected cells: which gates failed
    acc_check_fail = Counter()       # among accepted cells: which GT checks fail
    per_case = defaultdict(list)
    for c in cells:
        gs = c.get("gates_state") or {}
        for k, s in gs.items():
            gate_states[f"{k}:{s}"] += 1
        if c.get("accepted") is False:
            for k, s in gs.items():
                if s == "fail":
                    fail_causes[k] += 1
                elif s == "unmeasured":
                    fail_causes[k + ":unmeasured"] += 1
        if c.get("accepted") is True:
            for k, ok in (c.get("checks") or {}).items():
                if ok is False:
                    acc_check_fail[k] += 1
        per_case[(c["_run"], c["_case"])].append(bool(c.get("accepted")))
    n = len(cells)
    accepted = sum(1 for c in cells if c.get("accepted"))
    verified = sum(1 for c in cells if c.get("verified_acceptance"))
    out = {
        "cells": n, "accepted": accepted, "verified": verified,
        "gate_states": dict(gate_states.most_common()),
        "rejection_causes": dict(fail_causes.most_common()),
        "accepted_but_gt_check_failed": dict(acc_check_fail.most_common()),
        "per_case_accept_rate": {f"{r}/{c}": f"{sum(t)}/{len(t)}" for (r, c), t in sorted(per_case.items())},
    }
    print(json.dumps(out, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
