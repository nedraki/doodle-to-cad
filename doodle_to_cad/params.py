"""Parametric handles for a generated model.

The SCAD prompt mandates top-level parameters (`name = value;` before any
module). Those become the live-edit surface: parse them out of the accepted
model, expose numeric ones as sliders, and recompile on demand by rewriting
the assignments. Everything happens on the selected attempt only — the
benchmark loop and attempt history are untouched.
"""
from __future__ import annotations

import json
import math
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
    group: str | None = None
    label: str | None = None
    feature: dict | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "label": self.label, "feature": self.feature,
            "name": self.name, "value": self.value, "unit": self.unit,
            "group": self.group, "description": self.description, "low": self.low, "high": self.high, "step": self.step,
        }


def _unit_for(name: str, value: float, comment: str) -> str:
    text = f"{name} {comment}".lower()
    # Count first: "hole_count"/"num_bolts" read as sizes otherwise.
    if any(k in text for k in ("count", "number", "qty", "sides", "teeth", "num_")):
        return "count"
    if re.search(r"\b(deg|degrees?|angle)\b", text.replace("_", " ")):
        return "°"
    if re.search(r"\b(ratio|scale|factor)\b", text.replace("_", " ")):
        return "unitless"
    return "mm"


def _bounds(name: str, value: float, unit: str) -> tuple[float, float, float]:
    if unit == "count":
        low, high = 0, max(2, round(value * 2))
        return float(low), float(high), 1
    span = max(abs(value), 1.0)
    low = value - span if value < 0 else max(0.0, value - span)
    high = value + span
    return low, high, 0.01


def extract_params(scad_text: str, max_params: int = 14) -> list[Param]:
    """Top-level numeric parameters, in declaration order, deduplicated."""
    # Cut everything after the first module/function definition so parameter
    # blocks are the only scan surface (mirrors the generator contract).
    source = re.sub(r"/\*.*?\*/", lambda m: "\n" * m.group().count("\n") if "doodle-meta" in m.group() else m.group(), scad_text, flags=re.S)
    head = re.split(r"^\s*(?:module|function)\s", source, maxsplit=1, flags=re.M)[0]
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
        if not math.isfinite(value):
            continue
        unit = _unit_for(name, value, comment)
        low, high, step = _bounds(name, value, unit)
        # OpenSCAD Customizer section headers are explicit author metadata.
        groups = re.findall(r"^\s*/\*\s*\[([^]\n]+)\]\s*\*/\s*$", head[:match.start()], re.M)
        group = groups[-1].strip() if groups else None
        seen[name] = Param(name=name, value=value, unit=unit,
                           description=comment or name.replace("_", " "),
                           low=low, high=high, step=step, group=group)
    metadata = read_metadata(scad_text)
    if metadata is not None:
        selected = []
        for name, entry in metadata["parameters"].items():
            if name not in seen or not isinstance(entry, dict):
                continue
            if not all(isinstance(entry.get(k), str) and entry[k].strip() for k in ("label", "description", "unit")):
                continue
            if entry["unit"] not in {"mm", "°", "count", "unitless"}:
                continue
            p = seen[name]
            p.label, p.description, p.unit = entry["label"], entry["description"], entry["unit"]
            p.low, p.high, p.step = _bounds(name, p.value, p.unit)
            feature_id = entry.get("feature")
            if isinstance(feature_id, str):
                p.feature = resolve_feature(metadata.get("features", {}).get(feature_id), {k: v.value for k, v in seen.items()})
            selected.append(p)
        return selected[:max_params]
    return list(seen.values())[:max_params]


def rewrite_params(scad_text: str, updates: dict[str, float]) -> tuple[str, list[str]]:
    """Return (new_text, applied_names). Unknown names are skipped, never fatal."""
    applied: list[str] = []
    for name, value in updates.items():
        if not re.fullmatch(r"[A-Za-z_]\w*", name) or isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
            continue
        numeric = repr(float(value)) if float(value) != int(value) else str(int(value))
        pattern = re.compile(rf"^({re.escape(name)}\s*=\s*)[-\d.eE+]+(\s*;)", re.M)
        new_text, count = pattern.subn(lambda m: m.group(1) + numeric + m.group(2), scad_text, count=1)
        if count:
            scad_text = new_text
            applied.append(name)
    return scad_text, applied


def validate_updates(scad_text: str, updates: dict) -> None:
    """Reject invalid edits before invoking OpenSCAD; use the same bounds as the UI."""
    params = {p.name: p for p in extract_params(scad_text)}
    for name, value in updates.items():
        p = params.get(name)
        if p is None:
            raise ValueError(f"Unknown editable parameter: {name}")
        if (isinstance(value, bool) or not isinstance(value, (int, float))
                or not math.isfinite(value) or not p.low <= value <= p.high
                or (p.unit == "count" and not float(value).is_integer())):
            kind = "a whole number" if p.unit == "count" else "a finite number"
            raise ValueError(f"{name}: enter {kind} from {p.low} to {p.high} {p.unit}")


def read_metadata(scad_text: str) -> dict | None:
    """Versioned JSON in a SCAD comment; never execute model-authored expressions."""
    match = re.search(r"/\*\s*doodle-meta\s*(.*?)\*/", scad_text, re.S)
    if not match:
        return None
    try:
        data = json.loads(match.group(1))
        if (isinstance(data, dict) and data.get("version") == 1
                and isinstance(data.get("parameters"), dict)
                and isinstance(data.get("features", {}), dict)):
            return data
    except (ValueError, TypeError):
        pass
    return None


def resolve_feature(feature: Any, values: dict[str, float]) -> dict | None:
    """Resolve an explicit dimension or axis-aligned feature region in CAD mm.

    Coordinates are literals or {parameter, scale?, offset?}; no eval or inferred
    name associations. Missing/unsupported references invalidate the overlay.
    """
    if not isinstance(feature, dict) or not isinstance(feature.get("label"), str):
        return None
    if feature.get("kind") == "dimension" and feature.get("axis") in ("x", "y", "z"):
        return {"kind": "dimension", "axis": feature["axis"], "label": feature["label"]}
    if feature.get("kind") != "region":
        return None
    def scalar(v):
        if isinstance(v, dict):
            v = values[v["parameter"]] * finite(v.get("scale", 1)) + finite(v.get("offset", 0))
        return finite(v)
    def finite(v):
        if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v):
            raise ValueError("Invalid coordinate")
        return v
    try:
        low = [scalar(v) for v in feature["min"]]
        high = [scalar(v) for v in feature["max"]]
        if len(low) != 3 or len(high) != 3 or any(a >= b for a, b in zip(low, high)):
            return None
        return {"kind": "region", "label": feature["label"], "min": low, "max": high}
    except (KeyError, TypeError, ValueError, OverflowError):
        return None
