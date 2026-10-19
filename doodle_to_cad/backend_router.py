"""Deterministic backend routing for generation (issue #60).

The form default stays 'openscad'; users opt into 'auto'. Rules come from the
frozen 80-run comparison (docs/brep/task-17-comparison/) and the kernel defect
containment work (docs/brep/issue-61/). Every recommendation carries the rule
and the data citation that fired, so routing decisions are auditable.

Rules, in priority order (first match decides; all matches are recorded):
  K  same drawing already hit a usd_brep kernel failure -> openscad
  F  notes request fillet/chamfer/loft/shell operations   -> usd-brep
  V  two or more view groups (dense multi-view ink)       -> openscad
  C  circular-pattern-heavy drawing (kernel-failure class)-> openscad
  D  single view plus an explicit dimension                -> usd-brep
  -  default                                               -> openscad
"""
from __future__ import annotations

import hashlib
from typing import Any

FILLLET_WORDS = ("fillet", "chamfer", "round the edge", "rounded edge",
                 "round edge", "loft", "shell", "hollow", "transition")
KERNEL_FAILURE_CODES = {"kernel_unavailable"}
KERNEL_FAILURE_MESSAGES = ("_omni_solid", "kernel produced an invalid solid")

RULES = {
    "K": "usd_brep kernel already failed on this exact drawing; OpenSCAD is the working backend",
    "F": "notes request fillet/chamfer/loft/shell work: usd-brep passed 5/5 on the known-dimension "
         "operation rows vs 0/5 for OpenSCAD (task-17-comparison) and measured feature audit (bench-features)",
    "V": "two or more view groups: OpenSCAD won fidelity on dense multi-view ink (24/40 vs 11/40 accepted, "
         "task-17-comparison)",
    "C": "circular-pattern-heavy drawing: the frozen usd_brep kernel failures (3x '_omni_solid', "
         "2x 'kernel produced an invalid solid') all sit on curved-handle/spoke bodies (issue #61)",
    "D": "single view with an explicit dimension: usd-brep passed 5/5 vs 0/5 on the "
         "missing-thickness rows and fails loudly instead of inventing geometry (task-17-comparison)",
    "-": "no rule favored usd-brep; the incumbent OpenSCAD path stays the default",
}


def route(evidence: dict[str, Any], notes: str = "", dimension: str = "",
          kernel_history_hit: bool = False) -> dict[str, Any]:
    """Return {'backend', 'rule', 'rationale'} for one drawing. Pure function."""
    matches: list[str] = []
    text = (notes or "").lower()
    views = int(evidence.get("view_group_count") or 1)
    profiles = int(evidence.get("closed_internal_profile_count") or 0)
    circular = [s for s in (evidence.get("closed_internal_profiles") or [])
                if float(s.get("circularity") or 0) >= 0.7]

    if kernel_history_hit:
        matches.append("K")
    if any(word in text for word in FILLLET_WORDS):
        matches.append("F")
    if views >= 2:
        matches.append("V")
    if len(circular) >= 6 or profiles >= 8:
        matches.append("C")
    if views <= 1 and (dimension or "").strip():
        matches.append("D")

    rule = matches[0] if matches else "-"
    backend = "usd-brep" if rule in {"F", "D"} else "openscad"
    return {
        "backend": backend,
        "rule": rule,
        "signals": {"view_group_count": views, "closed_internal_profile_count": profiles,
                    "circular_profile_count": len(circular), "notes_keywords": "yes" if "F" in matches else "no",
                    "dimension_given": bool((dimension or "").strip()),
                    "kernel_history_hit": bool(kernel_history_hit)},
        "rationale": [{"rule": m, "text": RULES[m]} for m in (matches or ["-"])],
    }


def image_sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def scan_kernel_history(results_dir, sha: str) -> bool:
    """True if a past usd-brep job on the SAME image bytes hit a kernel failure."""
    import json
    from pathlib import Path

    root = Path(results_dir)
    if not root.is_dir():
        return False
    for out in sorted(root.iterdir()):
        job = out / "job.json"
        if not job.is_file():
            continue
        try:
            record = json.loads(job.read_text())
        except (OSError, ValueError):
            continue
        if record.get("status") != "error":
            continue
        error = record.get("error") or {}
        code = error.get("code") or ""
        message = error.get("message") or ""
        kernel_hit = code in KERNEL_FAILURE_CODES or any(
            sig in message for sig in KERNEL_FAILURE_MESSAGES)
        if not kernel_hit:
            continue
        stored = out / "input.png"
        if stored.is_file() and image_sha256(stored.read_bytes()) == sha:
            return True
    return False
