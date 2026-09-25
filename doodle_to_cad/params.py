"""Parametric handles for a generated model.

The SCAD prompt mandates top-level parameters (`name = value;` before any
module). Those become the live-edit surface: parse them out of the accepted
model, expose numeric ones as sliders, and recompile on demand by rewriting
the assignments. Everything happens on the selected attempt only — the
benchmark loop and attempt history are untouched.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

# `  name = 12.5;` at top level. Top-level params are never indented (the
# prompt requires them before any module, at column 0); indentation means the
# assignment lives inside a module body and must not be exposed as a slider.
_PARAM_RE = re.compile(r"^([A-Za-z_]\w*)\s*=\s*([-\d.eE+]+)\s*;\s*(?://[ \t]*(.*))?$", re.M)


@dataclass
class Param:
    name: str
    value: float
    unit: str
    description: str
    low: float
    high: float
    step: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name, "value": self.value, "unit": self.unit,
            "description": self.description, "low": self.low, "high": self.high, "step": self.step,
        }


def _unit_for(name: str, value: float, comment: str) -> str:
    text = f"{name} {comment}".lower()
    # Count first: "hole_count"/"num_bolts" read as sizes otherwise.
    if any(k in text for k in ("count", "number", "qty", "sides", "teeth", "num_")):
        return "count"
    if any(k in text for k in ("hole", "bore", "radius", "dia", "fillet", "chamfer")):
        return "radius/diameter"
    return "mm"


def _bounds(name: str, value: float, unit: str) -> tuple[float, float, float]:
    if unit == "count":
        low, high = 0, max(2, round(value * 2))
        return float(low), float(high), 1
    if value <= 0:
        return 0.0, 1.0, 0.05
    low = max(0.0, value - max(2 * abs(value) * 0.5, 1.0))
    high = value + max(2 * abs(value) * 0.5, 1.0)
    step = max(round(abs(value) / 100, 3), 0.05) if abs(value) >= 2 else 0.1
    return round(low, 3), round(high, 3), step


def extract_params(scad_text: str, max_params: int = 14) -> list[Param]:
    """Top-level numeric parameters, in declaration order, deduplicated."""
    # Cut everything after the first module/function definition so parameter
    # blocks are the only scan surface (mirrors the generator contract).
    head = re.split(r"^\s*(?:module|function)\s", scad_text, maxsplit=1, flags=re.M)[0]
    # Match on the RAW head so trailing `// unit` annotations survive, then
    # reject candidates whose line carried any other comment (commented-out
    # experiments like `// old = 5;` stay invisible thanks to the line check).
    seen: dict[str, Param] = {}
    for match in _PARAM_RE.finditer(head):
        name, raw, comment = match.group(1), match.group(2), (match.group(3) or "").strip()
        line = head[:match.start()].rpartition("\n")[2] + head[match.start():match.end()]
        # A comment anywhere else on the line (leading comment-out) disqualifies.
        if "//" in line.split(f"{name}")[0] or name in seen or name.startswith("_"):
            continue
        try:
            value = float(raw)
        except ValueError:
            continue
        unit = _unit_for(name, value, comment)
        low, high, step = _bounds(name, value, unit)
        seen[name] = Param(name=name, value=value, unit=unit,
                           description=comment or name.replace("_", " "),
                           low=low, high=high, step=step)
        if len(seen) >= max_params:
            break
    return list(seen.values())


def rewrite_params(scad_text: str, updates: dict[str, float]) -> tuple[str, list[str]]:
    """Return (new_text, applied_names). Unknown names are skipped, never fatal."""
    applied: list[str] = []
    for name, value in updates.items():
        if not re.fullmatch(r"[A-Za-z_]\w*", name) or not isinstance(value, (int, float)):
            continue
        numeric = repr(float(value)) if float(value) != int(value) else str(int(value))
        pattern = re.compile(rf"^({re.escape(name)}\s*=\s*)[-\d.eE+]+(\s*;)", re.M)
        new_text, count = pattern.subn(lambda m: m.group(1) + numeric + m.group(2), scad_text, count=1)
        if count:
            scad_text = new_text
            applied.append(name)
    return scad_text, applied
