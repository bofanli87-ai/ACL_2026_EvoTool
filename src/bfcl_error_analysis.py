"""Deterministic, gold-aware *offline* failure diagnosis for BFCL artifacts.

This module is reporting-only.  Its output must never be fed back into a policy or
repair path because it reads held-out gold calls.
"""

from __future__ import annotations

from collections import Counter
from itertools import permutations


def diagnose_bfcl(instance: dict, predicted_calls: list[dict],
                  caller_traces: list[dict] | None = None) -> dict:
    gold_specs = instance.get("gold_match") or []
    predicted = list(predicted_calls or [])
    traces = caller_traces or []
    details: list[dict] = []
    labels: set[str] = set()

    for idx, trace in enumerate(traces):
        if trace.get("parse_success") is False:
            labels.add("serialization")
            details.append({"category": "serialization", "call_index": idx,
                            "issue": "caller_json_parse_failed"})
        elif trace.get("arguments_is_object") is False:
            labels.add("serialization")
            details.append({"category": "serialization", "call_index": idx,
                            "issue": "caller_arguments_not_object"})

    if len(predicted) != len(gold_specs):
        labels.add("planning")
        details.append({"category": "planning", "issue": "call_count_mismatch",
                        "predicted": len(predicted), "gold": len(gold_specs)})

    gold_tools = [_gold_parts(spec)[0] for spec in gold_specs]
    pred_tools = [call.get("tool") for call in predicted]
    if Counter(pred_tools) != Counter(gold_tools):
        labels.add("selection")
        details.append({"category": "selection", "issue": "tool_multiset_mismatch",
                        "predicted": pred_tools, "gold": gold_tools})

    tools = {tool.get("name"): tool for tool in instance.get("available_tools", [])}
    for idx, call in enumerate(predicted):
        tool = tools.get(call.get("tool"))
        if tool:
            for issue in _schema_issues(call.get("args") or {},
                                        tool.get("parameter_schema") or {}, idx):
                labels.add("schema_interface")
                details.append(issue)

    # When tool multiplicities agree, find the least-error pairing for duplicate
    # calls to the same function, then separate interface from semantic failures.
    if Counter(pred_tools) == Counter(gold_tools):
        for tool_name in sorted(set(gold_tools)):
            pred_group = [(idx, call) for idx, call in enumerate(predicted)
                          if call.get("tool") == tool_name]
            gold_group = [spec for spec in gold_specs if _gold_parts(spec)[0] == tool_name]
            best: list[dict] | None = None
            for ordering in permutations(gold_group):
                issues: list[dict] = []
                for (idx, call), spec in zip(pred_group, ordering):
                    _, gold_args = _gold_parts(spec)
                    issues.extend(_gold_argument_issues(call.get("args") or {}, gold_args, idx))
                if best is None or len(issues) < len(best):
                    best = issues
            for issue in best or []:
                labels.add(issue["category"])
                details.append(issue)

    labels_order = [name for name in (
        "serialization", "planning", "selection", "schema_interface", "semantic_argument"
    ) if name in labels]
    return {
        "labels": labels_order,
        "primary_label": labels_order[0] if labels_order else "none",
        "details": _deduplicate(details),
    }


def _gold_parts(spec: dict) -> tuple[str | None, dict]:
    if not isinstance(spec, dict) or len(spec) != 1:
        return None, {}
    name, args = next(iter(spec.items()))
    return name, args or {}


def _schema_issues(args: dict, schema: dict, call_index: int) -> list[dict]:
    properties = schema.get("properties") or {}
    required = set(schema.get("required") or [])
    issues: list[dict] = []
    for name in sorted(required - set(args)):
        issues.append(_issue("schema_interface", call_index, name, "missing_required"))
    for name, value in args.items():
        if name not in properties:
            issues.append(_issue("schema_interface", call_index, name, "undeclared_argument"))
            continue
        child_schema = properties[name] if isinstance(properties[name], dict) else {}
        issues.extend(_schema_value_issues(value, child_schema, call_index, name))
    return issues


def _schema_value_issues(value, schema: dict, call_index: int, path: str) -> list[dict]:
    expected = schema.get("type")
    if expected and not _matches_schema_type(value, expected):
        return [_issue("schema_interface", call_index, path, "type_mismatch",
                       expected=expected, actual=_type_family(value))]
    normalized = "object" if expected == "dict" else expected
    issues: list[dict] = []
    if normalized == "array" and isinstance(value, list) and isinstance(schema.get("items"), dict):
        for idx, item in enumerate(value):
            issues.extend(_schema_value_issues(item, schema["items"], call_index,
                                               f"{path}[{idx}]"))
    elif normalized == "object" and isinstance(value, dict):
        properties = schema.get("properties") or {}
        for key, item in value.items():
            if key in properties and isinstance(properties[key], dict):
                issues.extend(_schema_value_issues(item, properties[key], call_index,
                                                   f"{path}.{key}"))
    return issues


def _gold_argument_issues(args: dict, gold_args: dict, call_index: int) -> list[dict]:
    issues: list[dict] = []
    for name in args.keys() - gold_args.keys():
        issues.append(_issue("schema_interface", call_index, name, "unexpected_argument"))
    for name, allowed in gold_args.items():
        allowed = allowed if isinstance(allowed, list) else [allowed]
        optional = any(isinstance(value, str) and value == "" for value in allowed)
        concrete = [value for value in allowed if not (isinstance(value, str) and value == "")]
        if name not in args:
            if not optional:
                issues.append(_issue("schema_interface", call_index, name, "missing_required"))
            continue
        value = args[name]
        allowed_types = sorted({_gold_type_family(item) for item in concrete})
        if not concrete:
            issues.append(_issue("semantic_argument", call_index, name,
                                 "optional_parameter_should_be_omitted"))
        elif not any(_same_type_structure(value, item) for item in concrete):
            issues.append(_issue("schema_interface", call_index, name, "type_mismatch",
                                 expected=allowed_types, actual=_gold_type_family(value)))
        elif value not in concrete:
            issues.append(_issue("semantic_argument", call_index, name, "wrong_value"))
    return issues


def _matches_schema_type(value, expected) -> bool:
    if isinstance(expected, list):
        return any(_matches_schema_type(value, item) for item in expected)
    expected = {"dict": "object", "float": "number", "tuple": "array"}.get(expected, expected)
    if expected == "any":
        return True
    actual = _type_family(value)
    return actual == expected or (expected == "number" and actual == "integer")


def _type_family(value) -> str:
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, int):
        return "integer"
    if isinstance(value, float):
        return "number"
    if isinstance(value, str):
        return "string"
    if isinstance(value, list):
        return "array"
    if isinstance(value, dict):
        return "object"
    if value is None:
        return "null"
    return type(value).__name__


def _gold_type_family(value) -> str:
    # BFCL's AST checker treats int and float as one numeric family.
    family = _type_family(value)
    return "number" if family in ("integer", "number") else family


def _same_type_structure(left, right) -> bool:
    if _gold_type_family(left) != _gold_type_family(right):
        return False
    if isinstance(left, list) and isinstance(right, list):
        return len(left) == len(right) and all(
            _same_type_structure(a, b) for a, b in zip(left, right))
    if isinstance(left, dict) and isinstance(right, dict):
        return set(left) == set(right) and all(
            _same_type_structure(left[key], right[key]) for key in left)
    return True


def _issue(category: str, call_index: int, argument: str, issue: str, **extra) -> dict:
    return {"category": category, "call_index": call_index, "argument": argument,
            "issue": issue, **extra}


def _deduplicate(items: list[dict]) -> list[dict]:
    seen: set[str] = set()
    out: list[dict] = []
    for item in items:
        key = repr(sorted(item.items()))
        if key not in seen:
            seen.add(key)
            out.append(item)
    return out
