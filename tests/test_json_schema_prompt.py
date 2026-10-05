from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.policy.modules import run_caller


class FakeClient:
    def __init__(self):
        self.messages = None

    def generate_json(self, messages):
        self.messages = messages
        return {"arguments": {"year": 2024}}


def _schema_text(client):
    return "\n".join(m["content"] for m in client.messages)


def test_schema_is_exposed_only_when_enabled():
    tool = {
        "name": "search",
        "description": "Search records",
        "parameters": {"year": "Year to search"},
        "parameter_schema": {
            "type": "object",
            "properties": {"year": {"type": "integer"}},
            "required": ["year"],
            "additionalProperties": False,
        },
    }

    baseline = FakeClient()
    run_caller(baseline, "caller policy", tool, "find 2024", "search", {}, False)
    assert "TOOL_PARAMETER_JSON_SCHEMA" not in _schema_text(baseline)

    treatment = FakeClient()
    args = run_caller(treatment, "caller policy", tool, "find 2024", "search", {}, True)
    assert '"type":"integer"' in _schema_text(treatment)
    assert '"required":["year"]' in _schema_text(treatment)
    assert args == {"year": 2024}


if __name__ == "__main__":
    test_schema_is_exposed_only_when_enabled()
    print("JSON Schema prompt test passed")

