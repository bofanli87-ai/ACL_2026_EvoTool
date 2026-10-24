from __future__ import annotations

from src.policy.agent import _structured_step
from src.policy.modules import _state_brief, run_planner


class FakeClient:
    def __init__(self):
        self.messages = None

    def generate_json(self, messages):
        self.messages = messages
        return {"plan": ["call search once"]}


TOOL = {
    "name": "search",
    "description": "Search records in one call.",
    "parameter_schema": {
        "type": "object",
        "properties": {"fields": {"type": "array", "items": {"type": "string"}}},
        "required": ["fields"],
    },
}


def _prompt(client):
    return "\n".join(message["content"] for message in client.messages)


def test_planner_tool_context_is_opt_in_and_complete():
    control = FakeClient()
    run_planner(control, "planner", "find records", [TOOL], False)
    assert "AVAILABLE_TOOLS_WITH_FULL_PARAMETER_SCHEMA" not in _prompt(control)

    treatment = FakeClient()
    run_planner(treatment, "planner", "find records", [TOOL], True)
    text = _prompt(treatment)
    assert "AVAILABLE_TOOLS_WITH_FULL_PARAMETER_SCHEMA" in text
    assert '"name":"search"' in text
    assert '"description":"Search records in one call."' in text
    assert '"required":["fields"]' in text
    assert "combine them in one subgoal" in text


def test_structured_history_retains_arguments_and_status():
    record = _structured_step(
        "find both fields", "search",
        {"args": {"fields": ["price", "volume"]}, "status": "ok", "output": [1, 2]},
    )
    rendered = _state_brief({"step_1": record})
    assert '"arguments":{"fields":["price","volume"]}' in rendered
    assert '"status":"ok"' in rendered
    assert '"output":[1,2]' in rendered
