"""Seal every published bench-final artifact with a sha256 (issue #79).

The frozen plan's evidence_layout declared 'SHA256SUMS sealed last' and an
environment.json, but the harness never wrote them - the audit could only
check hashes that rows happened to record (inputs and reference sources had
hashes nowhere). This script seals the complete evidence set instead:

  runs/**            every trial artifact (row.json, stl/model.stl, input.png,
                     job/result/request/scad/recipe, views, index.jsonl, ...)
  references/**      reference STLs + reference-measurements.json
  images/**          montages + provenance.json
  TRIAL-PLAN.json    the frozen plan itself
  repo:<path>        reference *sources* the measurements were taken from
                     (benchmarks/cases/**/ground_truth/model.stl, derived renders)

Trust model (published, not hidden): the manifest is generated from bytes on
disk and committed to git; editing evidence requires changing the manifest in
the same commit, so the anchor of trust is the git history, and audit.py
re-verifies manifest-vs-bytes on every run. The manifest deliberately does
NOT seal the derived reports (results.json, RESULTS.md, audit-result.json):
audit.py re-derives those from the sealed rows and compares instead.

Run from repo root:  python3 docs/brep/bench-final/make_manifest.py
"""
import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
DERIVED = {"results.json", "RESULTS.md", "audit-result.json", "MANIFEST.json"}
SEALED_DIRS = ("runs", "references", "images")
SEALED_FILES = ("TRIAL-PLAN.json",)


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def rel(p):
    return os.path.relpath(p, HERE)


def resolve_recorded(src):
    """Deterministically resolve a recorded RELATIVE source: repo-relative
    first, then bench-dir-relative. Absolute recorded paths are rejected —
    the audit must never follow a pointer out of the audited checkout."""
    if Path(src).is_absolute():
        raise SystemExit(f"recorded source is an absolute author path: {src}; "
                         "normalize to a repo-relative path and disclose the "
                         "original under source_original")
    p = REPO / src
    if p.exists():
        return f"repo:{src}", p
    p = HERE / src
    if p.exists():
        return src, p
    raise SystemExit(f"recorded source not found in this checkout: {src}")


def build_manifest():
    files = {}

    def seal(path, key=None):
        r = rel(path) if not key else key
        files[r] = {"sha256": sha256(path), "bytes": Path(path).stat().st_size}

    for d in SEALED_DIRS:
        for root, _, names in os.walk(HERE / d):
            for n in sorted(names):
                if n in DERIVED:
                    continue
                seal(Path(root) / n)
    for f in SEALED_FILES:
        seal(HERE / f)

    # reference sources (repo-relative 'repo:<path>' or bench-relative)
    refs = json.loads((HERE / "references" / "reference-measurements.json").read_text())
    for drawing, v in sorted(refs.items()):
        src = v.get("source")
        if not src:
            continue
        key, p = resolve_recorded(src)
        files[key] = {"sha256": sha256(p), "bytes": p.stat().st_size}
    # montage panel sources recorded in provenance.json may use repo: or bench-
    # relative paths; seal them too so 'recorded but unverified' cannot recur.
    prov_file = HERE / "images" / "provenance.json"
    if prov_file.exists():
        prov = json.loads(prov_file.read_text())

        def walk(node):
            if isinstance(node, dict):
                if node.get("path") and node.get("sha256"):
                    p = REPO / node["path"][len("repo:"):] if node["path"].startswith("repo:") else HERE / node["path"]
                    if not p.exists():
                        raise SystemExit(f"provenance panel source missing: {node['path']}")
                    files[node["path"] if node["path"].startswith("repo:") else rel(p)] = {
                        "sha256": node["sha256"], "bytes": p.stat().st_size}
                for v in node.values():
                    walk(v)
            elif isinstance(node, list):
                for v in node:
                    walk(v)
        walk(prov)

    return {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "generated_by": "make_manifest.py (issue #79)",
        "trust_note": ("Sealed from bytes on disk; anchor of trust is git history. "
                       "audit.py recomputes every hash; editing evidence requires "
                       "rewriting this file in the same commit. Derived reports "
                       "(results.json, RESULTS.md, audit-result.json) are excluded: "
                       "audit.py re-derives and compares them instead."),
        "files": files,
    }


def main():
    m = build_manifest()
    out = HERE / "MANIFEST.json"
    tmp = out.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(m, indent=1, sort_keys=True) + "\n")
    os.replace(tmp, out)  # atomic: an interrupted seal never clobbers the last good manifest
    print(f"sealed {len(m['files'])} artifacts -> MANIFEST.json")


if __name__ == "__main__":
    main()
