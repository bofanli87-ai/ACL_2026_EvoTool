from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.bfcl_error_analysis import diagnose_bfcl
from src.schema_repair import repair_arguments


def test_conservative_schema_repair():
    schema = {
        "type": "object",
        "properties": {
            "year": {"type": "integer"},
            "scores": {"type": "array", "items": {"type": "number"}},
            "active": {"type": "boolean"},
        },
        "required": ["year", "missing_but_never_invented"],
        "additionalProperties": False,
    }
    repaired, edits = repair_arguments(
        {"year": "2020", "scores": ["1.5", 2], "active": "false", "extra": 7}, schema)
    assert repaired == {"year": 2020, "scores": [1.5, 2], "active": False}
    assert "missing_but_never_invented" not in repaired
    assert len(edits) == 4


def test_bfcl_schema_dialect_is_normalized():
    repaired, edits = repair_arguments(
        {"rate": "0.05", "point": "[1, 2]"},
        {"type": "dict", "properties": {
            "rate": {"type": "float"},
            "point": {"type": "tuple", "items": {"type": "integer"}},
        }},
    )
    assert repaired == {"rate": 0.05, "point": [1, 2]}
    assert len(edits) == 2


def _instance():
    return {
        "available_tools": [{
            "name": "lookup",
            "parameter_schema": {
                "type": "object",
                "properties": {"year": {"type": "integer"}},
                "required": ["year"],
            },
        }],
        "gold_match": [{"lookup": {"year": [2020]}}],
    }


def test_diagnoses_type_not_semantics():
    result = diagnose_bfcl(_instance(), [{"tool": "lookup", "args": {"year": "2020"}}])
    assert result["primary_label"] == "schema_interface"
    assert "semantic_argument" not in result["labels"]


def test_diagnoses_semantic_value():
    result = diagnose_bfcl(_instance(), [{"tool": "lookup", "args": {"year": 2021}}])
    assert result["labels"] == ["semantic_argument"]


def test_nested_array_type_is_interface_error():
    instance = {
        "available_tools": [{
            "name": "sum",
            "parameter_schema": {
                "type": "object",
                "properties": {"values": {"type": "array", "items": {"type": "integer"}}},
                "required": ["values"],
            },
        }],
        "gold_match": [{"sum": {"values": [[3, 5]]}}],
    }
    result = diagnose_bfcl(instance, [{"tool": "sum", "args": {"values": ["3", "5"]}}])
    assert result["primary_label"] == "schema_interface"
    assert "semantic_argument" not in result["labels"]


def test_optional_sentinel_only_must_be_omitted():
    instance = {
        "available_tools": [{
            "name": "search",
            "parameter_schema": {
                "type": "object",
                "properties": {"kind": {"type": "string"}},
            },
        }],
        "gold_match": [{"search": {"kind": [""]}}],
    }
    result = diagnose_bfcl(instance, [{"tool": "search", "args": {"kind": "strategy"}}])
    assert result["labels"] == ["semantic_argument"]


def test_diagnoses_pipeline_and_serialization():
    result = diagnose_bfcl(
        _instance(),
        [{"tool": "wrong", "args": {}} , {"tool": "lookup", "args": {}}],
        [{"parse_success": False}],
    )
    assert result["labels"][:3] == ["serialization", "planning", "selection"]


if __name__ == "__main__":
    test_conservative_schema_repair()
    test_bfcl_schema_dialect_is_normalized()
    test_diagnoses_type_not_semantics()
    test_diagnoses_semantic_value()
    test_nested_array_type_is_interface_error()
    test_optional_sentinel_only_must_be_omitted()
    test_diagnoses_pipeline_and_serialization()
    print("schema repair and BFCL diagnosis tests passed")
