"""Small, deterministic JSON-Schema argument repair for the BFCL ablation.

The repair is deliberately conservative: it performs only unambiguous primitive
coercions, recursively repairs arrays/objects, and removes undeclared properties
only when ``additionalProperties`` is explicitly false.  It never invents a
missing value and never reads benchmark gold labels.
"""

from __future__ import annotations

import copy
import json
import re


_INTEGER = re.compile(r"^[+-]?\d+$")
_NUMBER = re.compile(r"^[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?$")


def repair_arguments(arguments: dict, schema: dict | None) -> tuple[dict, list[dict]]:
    repaired = copy.deepcopy(arguments) if isinstance(arguments, dict) else {}
    edits: list[dict] = []
    if not isinstance(schema, dict):
        return repaired, edits
    value = _repair_value(repaired, schema, "$", edits)
    return (value if isinstance(value, dict) else repaired), edits


def _repair_value(value, schema: dict, path: str, edits: list[dict]):
    expected = schema.get("type")
    if isinstance(expected, list):
        expected = next((item for item in expected if item != "null"), None)
    expected = _normalize_type(expected)

    converted = _coerce(value, expected)
    if converted is not value:
        edits.append({"path": path, "action": "coerce", "from": value, "to": converted,
                      "target_type": expected})
        value = converted

    if expected == "object" and isinstance(value, dict):
        properties = schema.get("properties") or {}
        if schema.get("additionalProperties") is False:
            for key in list(value):
                if key not in properties:
                    edits.append({"path": f"{path}.{key}", "action": "drop_undeclared",
                                  "from": value[key]})
                    del value[key]
        for key, child_schema in properties.items():
            if key in value and isinstance(child_schema, dict):
                value[key] = _repair_value(value[key], child_schema, f"{path}.{key}", edits)
    elif expected == "array" and isinstance(value, list):
        item_schema = schema.get("items")
        if isinstance(item_schema, dict):
            value = [_repair_value(item, item_schema, f"{path}[{idx}]", edits)
                     for idx, item in enumerate(value)]
    return value


def _coerce(value, expected: str | None):
    if not isinstance(value, str):
        return value
    stripped = value.strip()
    if expected == "integer" and _INTEGER.fullmatch(stripped):
        return int(stripped)
    if expected == "number" and _NUMBER.fullmatch(stripped):
        return float(stripped)
    if expected == "boolean" and stripped.lower() in ("true", "false"):
        return stripped.lower() == "true"
    if expected == "null" and stripped.lower() == "null":
        return None
    if expected in ("array", "object"):
        try:
            parsed = json.loads(stripped)
        except json.JSONDecodeError:
            return value
        if expected == "array" and isinstance(parsed, list):
            return parsed
        if expected == "object" and isinstance(parsed, dict):
            return parsed
    return value


def _normalize_type(expected: str | None) -> str | None:
    # BFCL's source definitions use a small JSON-Schema-like dialect.
    return {"dict": "object", "float": "number", "tuple": "array"}.get(expected, expected)
