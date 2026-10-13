from __future__ import annotations

import os
import re
import shlex
import shutil
import subprocess
from pathlib import Path
from typing import Any

from .build_contract import BuildInput, BuildResult, Diagnostic, CAMERAS


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


class _FailureLog(str):
    def __new__(cls, message: str, code: str):
        value = super().__new__(cls, message)
        value.code = code
        return value


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
        job_label = ["--label", "doodle-to-cad.job=" + os.environ["DOODLE_JOB_ID"]] if os.getenv("DOODLE_JOB_ID") else []
        cmd = docker_prefix + job_label + ["-v", f"{mount_root}:/work", "-w", "/work", os.getenv("DOODLE_OPENSCAD_DOCKER", "").strip(), "bash", "-c", shell_cmd]
    else:
        cmd = raw_args
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, cwd=cwd)
        return proc.returncode == 0, (proc.stderr or proc.stdout).strip()[-4000:]
    except subprocess.TimeoutExpired as exc:
        return False, _FailureLog(str(exc), "timeout")
    except OSError as exc:
        return False, _FailureLog(str(exc), "backend_unavailable")


def run(args: list[str], timeout: int = 180, cwd: Path | None = None) -> tuple[bool, str]:
    docker_prefix = None
    if shutil.which(args[0]) is None:
        try:
            docker_prefix = _docker_prefix(args[0])
        except subprocess.TimeoutExpired as exc:
            return False, _FailureLog(str(exc), "timeout")
        except OSError as exc:
            return False, _FailureLog(str(exc), "backend_unavailable")
        if docker_prefix is None:
            return False, _FailureLog(f"{args[0]} not found (no host binary and no Docker fallback; set DOODLE_OPENSCAD_DOCKER or install openscad)", "backend_unavailable")
    return _run(args, timeout, cwd, docker_prefix)


def render_views(source: Path, output_dir: Path, binary: str) -> tuple[dict[str, Path], str]:
    views: dict[str, Path] = {}
    logs = []
    for name, camera in CAMERAS.items():
        target = output_dir / f"view-{name}.png"
        target.unlink(missing_ok=True)
        rendered, log = run([binary, "--imgsize=720,540", "--projection=ortho", "--viewall", "--autocenter", f"--camera={camera}", "-o", target.name, source.name], cwd=output_dir)
        if rendered and target.exists():
            views[name] = target
        else:
            logs.append(f"{name}: {log or 'No image produced'}")
    return views, "\n".join(logs)


def build_scad(request: BuildInput, binary: str) -> BuildResult:
    output_dir = request.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    source = output_dir / request.source.name
    result = BuildResult("openscad", source)
    try:
        if source.resolve() != request.source.resolve():
            shutil.copy2(request.source, source)
        elif not source.is_file():
            raise ValueError("OpenSCAD source does not exist")
    except (OSError, ValueError) as exc:
        result.log = str(exc)
        result.diagnostics.append(Diagnostic("invalid_input", result.log))
        return result
    stl = output_dir / "model.stl"
    stl.unlink(missing_ok=True)
    ok, result.log = run([binary, "-o", stl.name, source.name], cwd=output_dir)
    if not ok or not stl.exists():
        stl.unlink(missing_ok=True)
        result.diagnostics.append(Diagnostic(getattr(result.log, "code", "build_failed"), result.log or "No STL produced"))
        return result
    try:
        result.measurements = mesh_health(stl)
        if not result.measurements["triangles"]:
            raise ValueError("STL contains no triangles")
    except Exception as exc:
        stl.unlink(missing_ok=True)
        result.log += "\n" + str(exc)
        result.diagnostics.append(Diagnostic("invalid_output", str(exc)))
        return result
    result.stl = stl
    if request.render:
        result.views, render_log = render_views(source, output_dir, binary)
        if render_log:
            result.log += "\n" + render_log
            result.diagnostics.append(Diagnostic("render_failed", render_log, "warning"))
    return result


def compile_and_render(scad: Path, output_dir: Path, binary: str) -> tuple[Path | None, dict[str, Path], str]:
    result = build_scad(BuildInput("openscad", scad, output_dir), binary)
    return result.stl, result.views, result.log


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
