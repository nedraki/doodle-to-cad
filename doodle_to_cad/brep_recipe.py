"""Bounded, data-only modeling recipes. No generated Python is executed."""
from __future__ import annotations

import ast
import copy
import math
import re

NAME = re.compile(r"^[A-Za-z][A-Za-z0-9_]{0,63}$")
FIELDS = {
    "box": {"origin", "size"},
    "cylinder": {"origin", "radius", "height", "axis"},
    "union": {"left", "right"},
    "difference": {"left", "right"},
    "fillet": {"body", "radius", "selector"},
    "chamfer": {"body", "radius"},
    "rotate": {"body", "origin", "axis", "angle"},
    "arc_pipe": {"origin", "bend_radius", "radius", "angle"},
}


def number(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or abs(value) > 10000 or not math.isfinite(value):
        raise ValueError("Expected a finite number within ±10000")
    return float(value)


def scalar(value, parameters):
    if not isinstance(value, str):
        return number(value)
    if len(value) > 160:
        raise ValueError("Expression too long")
    try:
        tree = ast.parse(value, mode="eval")
    except SyntaxError as exc:
        raise ValueError("Invalid dimension expression") from exc
    if len(list(ast.walk(tree))) > 64:
        raise ValueError("Expression too complex")

    def visit(node):
        if isinstance(node, ast.Constant):
            return number(node.value)
        if isinstance(node, ast.Name) and node.id in parameters:
            return parameters[node.id]
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.UAdd, ast.USub)):
            return number(visit(node.operand) * (-1 if isinstance(node.op, ast.USub) else 1))
        if isinstance(node, ast.BinOp) and isinstance(node.op, (ast.Add, ast.Sub, ast.Mult, ast.Div)):
            a, b = visit(node.left), visit(node.right)
            try:
                result = {ast.Add: lambda: a+b, ast.Sub: lambda: a-b,
                          ast.Mult: lambda: a*b, ast.Div: lambda: a/b}[type(node.op)]()
            except ZeroDivisionError as exc:
                raise ValueError("Division by zero") from exc
            return number(result)
        raise ValueError("Dimensions allow only numbers, parameter names and + - * /")
    return visit(tree.body)


def validate_recipe(recipe, updates=None):
    """Validate everything before launching a kernel process; resolve dimensions."""
    if isinstance(recipe, dict) and type(recipe.get("version")) is int and recipe["version"] == 2:
        from .construction_recipe import validate_v2
        return validate_v2(recipe, updates)
    if not isinstance(recipe, dict) or set(recipe) - {"version", "units", "parameters", "operations", "output", "name"}:
        raise ValueError("Invalid recipe fields")
    if type(recipe.get("version")) is not int or recipe.get("version") != 1 or recipe.get("units") != "mm":
        raise ValueError("Expected recipe version 1 and units mm")
    if "name" in recipe and (not isinstance(recipe["name"], str) or len(recipe["name"]) > 240):
        raise ValueError("Invalid recipe name")
    params = recipe.get("parameters")
    operations = recipe.get("operations")
    if not isinstance(params, dict) or len(params) > 64:
        raise ValueError("Expected at most 64 parameters")
    if not isinstance(operations, list) or not 1 <= len(operations) <= 128:
        raise ValueError("Expected 1–128 operations")
    updates = {} if updates is None else updates
    if not isinstance(updates, dict) or set(updates) - set(params):
        raise ValueError("Unknown parameter update")
    edited = copy.deepcopy(recipe)
    values = {}
    for name, entry in params.items():
        if not isinstance(name, str) or not NAME.fullmatch(name) or not isinstance(entry, dict):
            raise ValueError("Invalid parameter")
        if set(entry) - {"value", "min", "max", "label", "description", "unit", "group"}:
            raise ValueError(f"Unknown fields on parameter {name}")
        for field in ("label", "description", "unit", "group"):
            if field in entry and (not isinstance(entry[field], str) or len(entry[field]) > 240):
                raise ValueError(f"Invalid {field}")
        low, high = number(entry.get("min")), number(entry.get("max"))
        original = number(entry.get("value"))
        value = number(updates.get(name, original))
        if not low <= original <= high or not low <= value <= high:
            raise ValueError(f"{name} must be between {low} and {high}")
        if entry.get("unit") == "count" and (not value.is_integer() or not original.is_integer()):
            raise ValueError(f"{name} requires an integer count")
        values[name] = value
        edited["parameters"][name]["value"] = value
    resolved, seen = [], set()
    for op in operations:
        if not isinstance(op, dict) or not isinstance(op.get("id"), str) or not NAME.fullmatch(op["id"]):
            raise ValueError("Every operation needs a feature ID")
        kind = op.get("kind")
        if not isinstance(kind, str) or kind not in FIELDS or set(op) != FIELDS[kind] | {"id", "kind"} or op["id"] in seen:
            raise ValueError("Unsupported operation, duplicate ID or invalid fields")
        item = dict(op)
        for field in ("left", "right", "body"):
            if field in op and (not isinstance(op[field], str) or op[field] not in seen):
                raise ValueError("Body references must name earlier operations")
        for field in ("origin", "size"):
            if field in op:
                if not isinstance(op[field], list) or len(op[field]) != 3:
                    raise ValueError(f"{field} needs three coordinates")
                item[field] = [scalar(v, values) for v in op[field]]
        for field in ("radius", "height", "bend_radius", "angle"):
            if field in op:
                item[field] = scalar(op[field], values)
                if item[field] <= 0:
                    raise ValueError(f"{field} must be positive")
        if "size" in item and min(item["size"]) <= 0:
            raise ValueError("Box sizes must be positive")
        if kind in ("cylinder", "rotate") and op["axis"] not in ("x", "y", "z"):
            raise ValueError("Axis must be x, y or z")
        if kind == "rotate" and item["angle"] > 360:
            raise ValueError("Rotation angle must be positive and at most 360 degrees")
        if kind == "arc_pipe" and (item["radius"] >= item["bend_radius"] or item["angle"] > 270):
            raise ValueError("Pipe requires radius < bend_radius and angle ≤ 270°")
        if kind == "fillet" and op["selector"] not in ("all", "parallel_x", "parallel_y", "parallel_z"):
            raise ValueError("Fillet selector must be all or parallel_x/y/z")
        resolved.append(item)
        seen.add(op["id"])
    if not isinstance(recipe.get("output"), str) or recipe["output"] not in seen:
        raise ValueError("Top-level output must name a constructed operation ID; include output at the recipe root")
    return edited, resolved


def recipe_params(recipe):
    validate_recipe(recipe)
    return [dict(name=name, value=p["value"], low=p["min"], high=p["max"], step=1 if p.get("unit") == "count" else 0.01,
                 label=p.get("label", name.replace("_", " ")), unit=p.get("unit", "mm"),
                 description=p.get("description", "Rebuilds the saved construction recipe"),
                 group=p.get("group", "Details"), feature=None)
            for name, p in recipe["parameters"].items()]
