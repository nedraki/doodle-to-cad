from __future__ import annotations

import hashlib
import json
from pathlib import Path

import trimesh


ROOT = Path(__file__).resolve().parent


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate_case(case_dir: Path) -> list[str]:
    errors: list[str] = []
    manifest = json.loads((case_dir / "manifest.json").read_text())
    paths = {
        "drawing.png": case_dir / "source" / "drawing.png",
        "model.scad": case_dir / "ground_truth" / "model.scad",
        "model.stl": case_dir / "ground_truth" / "model.stl",
    }
    for name, path in paths.items():
        if not path.exists(): errors.append(f"{manifest['id']}: missing {name}"); continue
        expected = manifest["provenance"]["sha256"][name]
        if sha256(path) != expected: errors.append(f"{manifest['id']}: checksum mismatch for {name}")
    if paths["model.stl"].exists():
        mesh = trimesh.load_mesh(paths["model.stl"], process=True)
        topology = manifest["reference"]["topology"]
        if bool(mesh.is_watertight) != topology["watertight"]: errors.append(f"{manifest['id']}: watertight label mismatch")
        if len(mesh.split(only_watertight=False)) != topology["components"]: errors.append(f"{manifest['id']}: component label mismatch")
    return errors


def main() -> int:
    errors = []
    for manifest in sorted((ROOT / "cases").glob("*/manifest.json")):
        errors.extend(validate_case(manifest.parent))
    if errors:
        print("\n".join(errors)); return 1
    print(f"Validated {len(list((ROOT/'cases').glob('*/manifest.json')))} benchmark case(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
