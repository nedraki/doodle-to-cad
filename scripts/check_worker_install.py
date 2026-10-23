"""Issue #33: verify a clean worker installation from scratch, the way a tester would.

Creates a throwaway venv OUTSIDE the repository, installs ONLY the pinned
requirements with uv, then builds one part through the documented boundary.
Prints a JSON report and exits 0 only if every step passes. Keeps its log.

Usage: PYTHONPATH=. .venv/bin/python scripts/check_worker_install.py [report.json]
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
UV = shutil.which("uv") or str(Path.home() / ".local" / "bin" / "uv")
STEPS = []


def step(name, ok, detail=""):
    STEPS.append({"step": name, "status": "passed" if ok else "failed", "detail": str(detail)[:400]})
    print(f"{'PASS' if ok else 'FAIL'} {name} {str(detail)[:120]}")
    return ok


def main():
    report_path = Path(sys.argv[1]) if len(sys.argv) > 1 else None
    if not Path(UV).is_file():
        step("uv_available", False, f"uv not found at {UV}")
        return finish(report_path)
    step("uv_available", True, UV)
    workspace = Path(tempfile.mkdtemp(prefix="brep-clean-install-"))
    try:
        venv = workspace / "venv"
        proc = subprocess.run([UV, "venv", "--python", "3.12", str(venv)], capture_output=True, text=True)
        if not step("create_venv_3.12", proc.returncode == 0, proc.stderr or proc.stdout):
            return finish(report_path)
        python = venv / "bin" / "python"
        proc = subprocess.run([UV, "pip", "install", "--python", str(python), "-r",
                               str(ROOT / "workers" / "brep" / "requirements.txt")],
                              capture_output=True, text=True)
        if not step("install_pinned_requirements", proc.returncode == 0, proc.stderr or proc.stdout):
            return finish(report_path)
        probe = subprocess.run([str(python), "-c",
                                "import sys, usd_brep, numpy, trimesh, networkx, importlib.metadata as m;"
                                "print(m.version('usd-brep'), sys.version.split()[0])"],
                               capture_output=True, text=True)
        if not step("import_pinned_packages", probe.returncode == 0 and probe.stdout.startswith("1.0.0"),
                    probe.stdout or probe.stderr):
            return finish(report_path)
        step("import_pinned_packages_versions", True, probe.stdout.strip())
        # One real part through the documented boundary, fresh interpreter only.
        out = workspace / "run"
        out.mkdir()
        source = out / "box.json"
        source.write_text(json.dumps({
            "version": 1, "units": "mm", "parameters": {}, "output": "block",
            "operations": [{"id": "block", "kind": "box", "origin": [0, 0, 0], "size": [20, 20, 10]}]}))
        env = {k: v for k, v in os.environ.items() if k not in {"PYTHONPATH", "PYTHONHOME"}}
        proc = subprocess.run([str(python), str(ROOT / "workers" / "brep" / "build.py"),
                               str(source), str(out)], capture_output=True, text=True,
                              timeout=120, cwd=ROOT, env=env)
        if not step("clean_worker_build", proc.returncode == 0, proc.stderr[-400:]):
            return finish(report_path)
        diagnostics = json.loads((out / "diagnostics.json").read_text())
        stl = (out / "model.stl")
        ok_files = diagnostics.get("watertight") and stl.stat().st_size > 0 and (out / "model.usda").stat().st_size > 0
        step("clean_build_artifacts", bool(ok_files),
             json.dumps({"stl_bytes": stl.stat().st_size, "watertight": diagnostics.get("watertight")}))
        # Documented startup error path: unset worker must fail with an actionable hint.
        sys.path.insert(0, str(ROOT))
        os.environ["DOODLE_BREP_PYTHON"] = str(workspace / "definitely-missing-python")
        from doodle_to_cad import brep as product_brep
        product_brep._HEALTH_CACHE.clear()
        health = product_brep.worker_health()
        step("missing_worker_gives_actionable_error",
             health["available"] is False and "DOODLE_BREP_PYTHON" in health["reason"], health["reason"])
    finally:
        shutil.rmtree(workspace, ignore_errors=True)
    return finish(report_path)


def finish(report_path):
    failed = [s for s in STEPS if s["status"] == "failed"]
    report = {"passed": not failed, "steps": STEPS}
    if report_path:
        report_path.write_text(json.dumps(report, indent=1))
    print("INSTALL CHECK", "PASSED" if not failed else "FAILED", f"({len(STEPS) - len(failed)}/{len(STEPS)})")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
