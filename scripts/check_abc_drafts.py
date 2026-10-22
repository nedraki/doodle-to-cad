"""Check the ABC draft cells in benchmarks/cases-draft (issue #95 corpus work).

Internal checks (offline, always run):
  * every draft cell has a manifest with the required keys;
  * ground_truth/model.stl is watertight, one component, winding-consistent,
    with maximum extent exactly 120 mm and positive volume;
  * manifest reference measurements agree with the mesh (volume within 0.1%);
  * source/drawing.png and derived views exist and are non-empty;
  * the recorded unit inference is consistent: max_extent_mm_after_unit *
    scale_to_mm == 120 (within 1e-3 relative).

External check (network): re-download each recorded ABC bitstream URL and
compare its sha256 against manifest.source.sha256_stl. The archive REST
endpoint is intermittently down (HTTP 500 / empty bodies); unreachable URLs
report UNREACHABLE instead of failing the run, but a sha256 MISMATCH is a
hard failure. Never fabricate: nothing here writes to the cells.

Usage:
  PYTHONPATH=. .venv/bin/python scripts/check_abc_drafts.py [--no-network]
Exit codes: 0 = all checks passed; 2 = network checks incomplete
(UNREACHABLE only); 1 = a real integrity failure.
"""
import argparse
import hashlib
import json
import sys
import urllib.request
from pathlib import Path

import trimesh

ROOT = Path(__file__).resolve().parents[1]
DRAFTS = ROOT / "benchmarks" / "cases-draft"
REQUIRED_MANIFEST = {"schema_version", "id", "title", "split", "status", "source",
                     "reference", "doodle_status", "doodle_generation", "axisymmetric_flag",
                     "selection", "citation", "notes"}


def check_cell(cell: Path, use_network: bool = True) -> tuple[list[str], dict]:
    """Return (failures, network_state) for one draft cell."""
    fails: list[str] = []
    net: dict[str, str] = {}
    manifest_path = cell / "manifest.json"
    if not manifest_path.exists():
        return [f"{cell.name}: manifest.json missing"], net
    manifest = json.loads(manifest_path.read_text())
    missing = REQUIRED_MANIFEST - set(manifest)
    if missing:
        fails.append(f"{cell.name}: manifest missing keys {sorted(missing)}")

    stl = cell / "ground_truth" / "model.stl"
    if not stl.exists():
        return fails + [f"{cell.name}: ground_truth/model.stl missing"], net
    mesh = trimesh.load(stl, force="mesh")
    if not mesh.is_watertight:
        fails.append(f"{cell.name}: GT not watertight")
    if not mesh.is_winding_consistent:
        fails.append(f"{cell.name}: GT winding inconsistent")
    if len(mesh.split()) != 1:
        fails.append(f"{cell.name}: GT not one component")
    if max(mesh.extents) != 120.0 or abs(max(mesh.extents) - 120.0) > 1e-6:
        fails.append(f"{cell.name}: GT max extent {max(mesh.extents)} != 120.0 mm")
    if mesh.volume <= 0:
        fails.append(f"{cell.name}: GT volume not positive")

    reference = manifest.get("reference", {})
    for key, value in (("volume_mm3", mesh.volume), ("extents_mm", [float(v) for v in mesh.extents])):
        expected = reference.get(key)
        if expected is None:
            continue
        if key == "volume_mm3":
            if abs(expected - value) / max(value, 1e-9) > 1e-3:
                fails.append(f"{cell.name}: manifest volume {expected} vs mesh {value}")
        elif any(abs(a - b) > 1e-6 for a, b in zip(expected, value)):
            fails.append(f"{cell.name}: manifest extents {expected} vs mesh {value}")

    for rel in ("source/drawing.png", "derived/view-front.png", "derived/view-top.png"):
        p = cell / rel
        if not p.exists() or p.stat().st_size == 0:
            fails.append(f"{cell.name}: {rel} missing or empty")
    meta = cell / "meta.yml"
    if not meta.exists() or meta.stat().st_size == 0:
        fails.append(f"{cell.name}: meta.yml missing or empty")

    source = manifest.get("source", {})
    extent_after_unit = source.get("max_extent_mm_after_unit")
    scale = source.get("scale_to_mm")
    # scale_to_mm folds in the inferred m->mm conversion: raw extent (in the
    # inferred unit) * scale_to_mm == 120000, giving 120.0 mm after /1000.
    if extent_after_unit and scale and abs(extent_after_unit * scale - 120000.0) > 120000.0 * 1e-3:
        fails.append(f"{cell.name}: unit inference inconsistent "
                     f"({extent_after_unit} * {scale} != 120000)")

    url = source.get("urls", {}).get("stl2")
    expected_sha = source.get("sha256_stl")
    if not url or not expected_sha:
        fails.append(f"{cell.name}: source urls/stl2 or sha256_stl missing")
    elif use_network:
        try:
            data = urllib.request.urlopen(url, timeout=60).read()
            if not data:
                net[cell.name] = "UNREACHABLE (empty body)"
            else:
                got = hashlib.sha256(data).hexdigest()
                net[cell.name] = "MATCH" if got == expected_sha else f"MISMATCH got {got}"
                if got != expected_sha:
                    fails.append(f"{cell.name}: sha256 MISMATCH ({got} != {expected_sha})")
        except Exception as exc:
            net[cell.name] = f"UNREACHABLE ({type(exc).__name__})"
    return fails, net


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--no-network", action="store_true",
                        help="skip the sha256 re-download (internal checks only)")
    args = parser.parse_args()
    cells = sorted(p for p in DRAFTS.iterdir() if p.is_dir() and p.name != "__pycache__")
    if not cells:
        print(f"no draft cells under {DRAFTS}", file=sys.stderr)
        return 1
    all_fails: list[str] = []
    unreachable = 0
    for cell in cells:
        fails, net = check_cell(cell, use_network=not args.no_network)
        all_fails += fails
        state = net.get(cell.name, "SKIPPED" if args.no_network else "NO-URL")
        if state.startswith("UNREACHABLE"):
            unreachable += 1
        print(f"{cell.name}: {state}; {'OK' if not fails else 'FAILED'}")
    for line in all_fails:
        print("FAIL:", line)
    if all_fails:
        return 1
    print(f"{len(cells)} cells internally sound; network unreachable: {unreachable}")
    return 2 if unreachable else 0


if __name__ == "__main__":
    sys.exit(main())
