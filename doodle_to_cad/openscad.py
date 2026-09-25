from __future__ import annotations

import os
import re
import shlex
import shutil
import subprocess
from pathlib import Path
from typing import Any


def available(binary: str) -> bool:
    if shutil.which(binary) is not None:
        return True
    docker = _docker_prefix(binary)
    return docker is not None


_DOCKER_READY: list[str] | None = None  # cache: [] = unavailable, [..] = prefix


def _docker_prefix(binary: str) -> list[str] | None:
    """Fallback: run OpenSCAD inside the official multi-arch Docker image.

    Returns a command prefix like ['docker','run','--rm',...] to be joined
    with the rest of the openscad arguments, or None when unavailable.
    Activate by setting DOODLE_OPENSCAD_DOCKER=openscad/openscad:latest.
    """
    global _DOCKER_READY
    image = os.getenv("DOODLE_OPENSCAD_DOCKER", "").strip()
    if not image or not shutil.which("docker"):
        return None
    if _DOCKER_READY is None:
        proc = subprocess.run(
            ["docker", "image", "inspect", image], capture_output=True, text=True, timeout=30
        )
        _DOCKER_READY = [] if proc.returncode != 0 else ["docker", "run", "--rm"]
    if not _DOCKER_READY:
        return None
    return _DOCKER_READY


def _run(raw_args: list[str], timeout: int, cwd: Path | None, docker_prefix: list[str] | None) -> tuple[bool, str]:
    if docker_prefix is not None:
        # Mount the working directory at /work and rewrite file paths under it.
        # raw_args[0] is the binary name (provided inside the container);
        # flag tokens (e.g. -o, --camera=...) are passed through untouched.
        mount_root = (cwd or Path.cwd()).resolve()
        file_args = []
        for token in raw_args[1:]:
            if token.startswith("-"):
                file_args.append(token)
                continue
            candidate = Path(token)
            if not candidate.is_absolute():
                candidate = (mount_root / candidate).resolve()
            try:
                rel = candidate.relative_to(mount_root)
            except ValueError:
                return False, f"Docker OpenSCAD fallback cannot reach path outside mount: {token}"
            file_args.append(str(Path("/work") / rel))
        shell_cmd = ("Xvfb :99 -screen 0 1024x768x24 >/dev/null 2>&1 & XPID=$!; "
                     "DISPLAY=:99 openscad " + " ".join(shlex.quote(a) for a in file_args) +
                     "; RC=$?; kill $XPID 2>/dev/null; exit $RC")
        cmd = docker_prefix + ["-v", f"{mount_root}:/work", "-w", "/work", os.getenv("DOODLE_OPENSCAD_DOCKER", "").strip(), "bash", "-c", shell_cmd]
    else:
        cmd = raw_args
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, cwd=cwd)
        return proc.returncode == 0, (proc.stderr or proc.stdout).strip()[-4000:]
    except (OSError, subprocess.TimeoutExpired) as exc:
        return False, str(exc)


def run(args: list[str], timeout: int = 180, cwd: Path | None = None) -> tuple[bool, str]:
    docker_prefix = None
    if shutil.which(args[0]) is None:
        docker_prefix = _docker_prefix(args[0])
        if docker_prefix is None:
            return False, f"{args[0]} not found (no host binary and no Docker fallback; set DOODLE_OPENSCAD_DOCKER or install openscad)"
    return _run(args, timeout, cwd, docker_prefix)


def compile_and_render(scad: Path, output_dir: Path, binary: str) -> tuple[Path | None, dict[str, Path], str]:
    stl = output_dir / "model.stl"
    # Run with output_dir as cwd and relative paths so the Docker fallback can
    # bind-mount one directory and see both the source .scad and its outputs.
    scad_name = Path(scad).resolve().relative_to(output_dir.resolve()).as_posix() if scad.resolve().is_relative_to(output_dir.resolve()) else Path(scad).name
    ok, log = run([binary, "-o", "model.stl", scad_name], cwd=output_dir)
    if not ok or not stl.exists():
        return None, {}, log
    views: dict[str, Path] = {}
    # Canonical generated-part axes: X=width, Y=front-to-back depth,
    # Z=height. Front looks down Y; top looks down Z; right looks down X.
    cameras = {"isometric": "0,0,0,55,0,35,0", "front": "0,0,0,90,0,0,0",
               "top": "0,0,0,0,0,0,0", "right": "0,0,0,90,0,90,0"}
    for name, camera in cameras.items():
        target = output_dir / f"view-{name}.png"
        rendered, render_log = run([binary, "--imgsize=720,540", "--projection=ortho", "--viewall", "--autocenter", f"--camera={camera}", "-o", f"view-{name}.png", scad_name], cwd=output_dir)
        if rendered and target.exists(): views[name] = target
        elif render_log: log += f"\n{name}: {render_log}"
    return stl, views, log


def compile_stl_only(output_dir: Path, scad_text: str, tag: str, binary: str = "openscad") -> tuple[str | None, str]:
    """Recompile a parameter-edited variant to STL without touching model.scad.

    Writes <tag>.scad + <tag>.stl inside output_dir (mirrors compile_and_render's
    relative-path contract so the Docker bind-mount sees both). Returns the
    results-relative STL URL with a cache-busting query, or (None, error).
    """
    name = re.sub(r"[^A-Za-z0-9_.-]", "-", tag)[:80] or "edited"
    scad_path = output_dir / f"{name}.scad"
    stl_path = output_dir / f"{name}.stl"
    scad_path.write_text(scad_text)
    ok, log = run([binary, "-o", stl_path.name, scad_path.name], cwd=output_dir)
    if not ok or not stl_path.exists():
        stl_path.unlink(missing_ok=True)
        return None, log[-500:] or "OpenSCAD produced no STL"
    run_id = output_dir.name
    return f"/results/{run_id}/{stl_path.name}?v={int(stl_path.stat().st_mtime * 1000)}", ""


def mesh_health(stl: Path) -> dict[str, Any]:
    import trimesh

    loaded = trimesh.load_mesh(stl, process=True)
    meshes = list(loaded.geometry.values()) if isinstance(loaded, trimesh.Scene) else [loaded]
    components = []
    for mesh in meshes:
        components.extend(mesh.split(only_watertight=False))
    triangles = sum(len(component.faces) for component in components)
    extents = loaded.extents.tolist() if hasattr(loaded, "extents") else [0, 0, 0]
    return {
        "watertight": bool(components and all(component.is_watertight for component in components)),
        "components": len(components),
        "triangles": int(triangles),
        "extents_mm": [round(float(value), 3) for value in extents],
        "volume_mm3": round(float(sum(abs(component.volume) for component in components)), 3),
    }
