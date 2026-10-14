"""Backend-neutral build boundary. Geometry success is not drawing approval."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

from .brep_recipe import FIELDS

Backend = Literal["openscad", "usd-brep"]
SourceFormat = Literal["openscad", "brep-recipe-v1", "brep-recipe-v2"]
FailureCode = Literal["invalid_input", "backend_unavailable", "build_failed", "timeout", "invalid_output", "render_failed", "unsupported_construction", "invalid_recipe", "dimension_exceeded"]

# X=width, Y=depth, Z=height; all distances are millimetres.
CAMERAS = {"isometric": "0,0,0,55,0,35,0", "front": "0,0,0,90,0,0,0",
           "top": "0,0,0,0,0,0,0", "right": "0,0,0,90,0,90,0"}
CAPABILITIES = {
    "openscad": {"source_format": "openscad", "exports": ["stl"], "isolated_process": True, "views": list(CAMERAS), "parameter_edits": True},
    "usd-brep": {"direct_generation": "experimental", "operations": sorted(FIELDS), "source_format": "brep-recipe-v1", "supported_source_formats": ["brep-recipe-v1", "brep-recipe-v2"], "exports": ["stl", "usd"], "isolated_process": True, "views": list(CAMERAS), "parameter_edits": True},
}


@dataclass(frozen=True)
class BuildInput:
    backend: Backend
    source: Path
    output_dir: Path
    render: bool = True

    @property
    def source_format(self) -> SourceFormat:
        if self.backend == "openscad":
            return "openscad"
        document = json.loads(self.source.read_text())
        version = document.get("version") if isinstance(document, dict) else None
        if type(version) is not int or version not in (1, 2):
            raise ValueError("Expected BRep recipe version 1 or 2")
        return f"brep-recipe-v{version}"


@dataclass(frozen=True)
class Diagnostic:
    code: FailureCode
    message: str
    severity: Literal["error", "warning"] = "error"


@dataclass
class BuildResult:
    backend: Backend
    source: Path
    stl: Path | None = None
    views: dict[str, Path] = field(default_factory=dict)
    exports: dict[str, Path] = field(default_factory=dict)
    diagnostics: list[Diagnostic] = field(default_factory=list)
    measurements: dict[str, Any] = field(default_factory=dict)
    backend_details: dict[str, Any] = field(default_factory=dict)
    log: str = ""

    @property
    def ok(self) -> bool:
        return self.stl is not None and not any(d.severity == "error" for d in self.diagnostics)

    def metadata(self) -> dict:
        """JSON metadata; paths are exposed by each application's URL mapping."""
        return {"version": 1, "backend": self.backend,
                "source_format": (f"brep-recipe-v{self.backend_details.get('recipe_version', 1)}"
                                  if self.backend == "usd-brep" else "openscad"),
                "ok": self.ok, "units": "mm", "axes": {"x": "width", "y": "depth", "z": "height"},
                "views": list(self.views), "measurements": self.measurements,
                "diagnostics": [vars(d) for d in self.diagnostics],
                "drawing_evaluated": False}


class BuildError(ValueError):
    def __init__(self, code: FailureCode, message: str):
        super().__init__(message)
        self.code = code


def build(request: BuildInput, binary: str = "openscad") -> BuildResult:
    """Build native source without translating between source languages."""
    if request.backend == "openscad":
        from .openscad import build_scad
        return build_scad(request, binary)
    if request.backend == "usd-brep":
        from .brep import build_brep
        return build_brep(request, binary)
    raise ValueError(f"Unknown backend: {request.backend}")
