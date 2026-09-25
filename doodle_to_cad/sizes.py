"""Deterministic physical-size solver from measured view ink spans.

Root cause this fixes (reg4/reg5/reg6 dimension lotteries): view-local
fractions are scale-blind, so when the user omits sizes each axis was scaled
independently — hand-drawn sheets are never pixel-consistent (103's doodle
draws width:height 2:1 on the sheet where truth is 2.5:1), and the LLM spec's
estimated dimensions disagree with reality often enough to poison the shape
gate. An engineer reading a scale drawing measures ink; so do we.

Each view's ink span along its own u/v axes (measured_span_pixels) is a pixel
measure of one CAD axis, taken on the shared sheet scale. Collect candidates
per CAD axis across views, take the median (absorbs per-view wobble), and map
pixels to millimetres with the authoritative scale = max_dimension / widest
axis. Axes no view constrains (e.g. depth in a single front-view sketch) are
left None for the specification's judgment to fill.
"""
from __future__ import annotations

from statistics import median
from typing import Any

# Which CAD axis each view's u/v span measures (mirrors geometry.axis_contracts).
_U_AXIS = {"front": "width", "rear": "width", "top": "width", "bottom": "width",
           "right": "depth", "left": "depth"}
_V_AXIS = {"front": "height", "rear": "height", "top": "depth", "bottom": "depth",
           "right": "height", "left": "height"}


def derive_physical_sizes(evidence: dict[str, Any], target_max_mm: Any) -> dict[str, Any] | None:
    """Return {"width_mm","depth_mm","height_mm","anchor","per_view","method"};
    an axis no view constrains is None. None when unsolvable (no dimension
    anchor, no labelled views with spans)."""
    try:
        target = float(target_max_mm)
    except (TypeError, ValueError):
        return None
    if target <= 0:
        return None
    views = [v for v in evidence.get("view_geometry", [])
             if v.get("direction") in _U_AXIS and v.get("measured_span_pixels")]
    candidates: dict[str, list[float]] = {"width": [], "depth": [], "height": []}
    per_view: dict[str, dict[str, int]] = {}
    for view in views:
        direction = view["direction"]
        spans = view["measured_span_pixels"]
        try:
            u_px, v_px = int(spans["horizontal_axis_u"]), int(spans["vertical_axis_v"])
        except (KeyError, TypeError, ValueError):
            continue
        if u_px < 4 or v_px < 4:
            continue
        per_view[direction] = {"u_px": u_px, "v_px": v_px}
        candidates[_U_AXIS[direction]].append(float(u_px))
        candidates[_V_AXIS[direction]].append(float(v_px))
    medians = {axis: (median(vals) if vals else None) for axis, vals in candidates.items()}
    known = [m for m in medians.values() if m]
    if not known:
        return None
    scale = target / max(known)  # mm per sheet pixel (shared drawing scale)
    sizes = {axis: (round(scale * m, 2) if m else None) for axis, m in medians.items()}
    return {"width_mm": sizes["width"], "depth_mm": sizes["depth"], "height_mm": sizes["height"],
            "anchor": {"authoritative_max_dimension_mm": target}, "per_view": per_view,
            "method": "median measured ink span per CAD axis x authoritative scale"}


def normalize_dimensions(raw: Any) -> dict[str, Any]:
    """Coerce spec.dimensions into the dict shape the evaluator reads.

    The LLM delivers this field as a list of {dimension_type, value} records
    about 80% of the time (measured: 218 list vs 54 dict across runs). The
    evaluator only understands the dict, so list form silently disabled the
    per-axis shape checks — and blind dict() on it raises
    'dictionary update sequence element #0 has length 5; 2 is required'.
    """
    if isinstance(raw, dict):
        return dict(raw)
    out: dict[str, Any] = {}
    if isinstance(raw, list):
        for item in raw:
            if not isinstance(item, dict):
                continue
            kind = str(item.get("dimension_type") or item.get("type") or "").strip().lower()
            value = item.get("value", item.get("mm"))
            if kind and value is not None:
                try:
                    out[kind] = float(value)
                except (TypeError, ValueError):
                    continue
    return out


# Constants that must NEVER be multiplied by a scale factor even though their
# unit parses as mm: facet counts, angles and pseudo-constants (pi, segments)
# keep their role at any size, and view-local fractions (u/v in 0..1) become
# out-of-part coordinates when scaled.
_NON_SCALABLE_KEYWORDS = ("angle", "deg", "rad", "pi", "segment", "step",
                          "slice", "layers", "fn")


def uniform_scale_scad(scad: str, scale: float) -> tuple[str, list[str]]:
    """Multiply every true-size top-level parameter by `scale` (whole-part
    uniform scaling, like OpenSCAD's scale()). Returns (text, applied_names);
    applied is empty when nothing safe was found, signalling the caller to
    keep the original source."""
    from .params import extract_params, rewrite_params

    if abs(scale - 1.0) < 1e-6:
        return scad, []
    updates = {}
    for param in extract_params(scad, max_params=10_000):
        if param.unit not in ("mm", "radius/diameter"):
            continue
        if abs(param.value) <= 1.0:  # 0..1 view-local fractions, epsilon margins
            continue
        if any(k in param.name.lower() for k in _NON_SCALABLE_KEYWORDS):
            continue
        updates[param.name] = param.value * scale
    if not updates:
        return scad, []
    return rewrite_params(scad, updates)
