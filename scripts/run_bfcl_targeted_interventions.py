"""Causal interventions for the five final 3-epoch BFCL failures.

This is a post-hoc diagnostic runner, not a held-out benchmark runner.  It keeps
Caller experiments paired by freezing the recorded plan and selected tools, and
reruns Planner only for Planner interventions.  Oracle information is labelled in
every output row so it cannot be confused with a general repair result.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from run import build_config
from src.benchmarks import load_instances
from src.bfcl_error_analysis import diagnose_bfcl
from src.eval_bfcl_ast import bfcl_ast_success
from src.env import registry
from src.llm.client import LLMClient
from src.policy import modules
from src.prompts import INITIAL_CALLER, INITIAL_PLANNER, INITIAL_SELECTOR


CASE_IDS = ("bfcl_55", "bfcl_109", "bfcl_149", "bfcl_29", "bfcl_56")
G15_CALLER = (
    INITIAL_CALLER
    + " Ensure that each tool call is unique and distinct based on its arguments "
      "to prevent duplicate calls."
)

ORACLE_CALLS = {
    "bfcl_55": [
        {"tool": "BattleReignGameAPI.update_player_equipment",
         "args": {"attribute": "armor", "level": 5, "playerID": 123}},
        {"tool": "GameGuideAPI.search_guide",
         "args": {"game": "Battle Reign", "condition": "snowy weather"}},
        {"tool": "GameGuideAPI.search_guide",
         "args": {"game": "Shadow Fall", "type": "strategy"}},
    ],
    "bfcl_109": [
        {"tool": "financials.calculate_future_value",
         "args": {"present_value": 1000, "annual_interest_rate": 0.05,
                  "number_of_years": 1}},
        {"tool": "financials.calculate_future_value",
         "args": {"present_value": 1000, "annual_interest_rate": 0.05,
                  "number_of_years": 5}},
        {"tool": "financials.calculate_future_value",
         "args": {"present_value": 1000, "annual_interest_rate": 0.05,
                  "number_of_years": 10}},
    ],
    "bfcl_149": [
        {"tool": "Events_3_FindEvents",
         "args": {"event_type": "Music", "city": "San Diego, CA",
                  "date": "2023-03-01"}},
        {"tool": "Events_3_FindEvents",
         "args": {"event_type": "Theater", "city": "San Diego, CA",
                  "date": "2023-03-01"}},
    ],
    "bfcl_29": [
        {"tool": "criminal_record.get_status",
         "args": {"criminal_name": "John Doe", "region": "New York"}},
        {"tool": "criminal_record.get_offense_nature",
         "args": {"criminal_name": "John Doe"}},
    ],
    "bfcl_56": [
        {"tool": "recipe_search",
         "args": {"ingredient": "spaghetti", "dietary_requirements": ["gluten_free"],
                  "isHomemade": True}},
        {"tool": "recipe_prep_time", "args": {"recipe": "spaghetti"}},
        {"tool": "recipe_nutrition_info", "args": {"recipe": "spaghetti"}},
    ],
}

ORACLE_PLANS = {
    "bfcl_55": [
        "Call BattleReignGameAPI.update_player_equipment with attribute=armor and level=5.",
        "Call GameGuideAPI.search_guide for game=Battle Reign with condition=snowy weather; do not add a guide type not requested for this intent.",
        "Call GameGuideAPI.search_guide for game=Shadow Fall with type=strategy; do not carry the Battle Reign weather condition into this intent.",
    ],
    "bfcl_109": [
        "Call financials.calculate_future_value with present_value=1000, annual_interest_rate=0.05, number_of_years=1.",
        "Call financials.calculate_future_value with present_value=1000, annual_interest_rate=0.05, number_of_years=5.",
        "Call financials.calculate_future_value with present_value=1000, annual_interest_rate=0.05, number_of_years=10.",
    ],
    "bfcl_149": [
        "Call Events_3_FindEvents with event_type=Music, city=San Diego, CA, date=2023-03-01.",
        "Call Events_3_FindEvents with event_type=Theater, city=San Diego, CA, date=2023-03-01.",
    ],
    "bfcl_29": [
        "Call criminal_record.get_status for John Doe in New York.",
        "Call criminal_record.get_offense_nature for John Doe; the user did not request additional details, so omit optional_param and use the documented default.",
    ],
    # Dependency-only on purpose: it does not leak an accepted BFCL alias.
    "bfcl_56": [
        "Call recipe_search for a homemade gluten-free spaghetti recipe.",
        "Call recipe_prep_time for the recipe returned by the first step.",
        "Call recipe_nutrition_info for the same recipe returned by the first step.",
    ],
}

QUERY_ANCHOR_PLAN_56 = [
    "Call recipe_search with ingredient=spaghetti, dietary_requirements=[gluten_free], isHomemade=true.",
    "Because this benchmark provides no search result, call recipe_prep_time with the exact query entity recipe=spaghetti.",
    "Call recipe_nutrition_info with the same exact query entity recipe=spaghetti.",
]

PLANNER_RULES = {
    "bfcl_55": "When the same tool is needed more than once, each subgoal must state the distinct entity and constraints assigned to that call. Keep sibling intents separate and state which optional constraints must not be carried into the current call.",
    "bfcl_109": "For repeated calls, include every explicit argument value in its own current subgoal and preserve the user's requested sequence.",
    "bfcl_149": "For repeated calls, include all shared argument values verbatim in every subgoal and state the one field that differs.",
    "bfcl_29": "When a tool has optional behavior not requested by the user, state in the subgoal that the optional parameter should be omitted and its documented default retained.",
    "bfcl_56": "Represent dependencies explicitly. If an earlier tool is not executed and returns no object identifier, state that downstream calls should use the exact minimal entity span from the user query as the fallback reference.",
}

CALLER_RULES = {
    "bfcl_55": "Treat CURRENT_SUBGOAL as the authoritative scope for the current call. For repeated uses of the same tool, use only the entity and constraints assigned to this subgoal; never merge constraints from sibling intents or copy the previous call wholesale.",
    "bfcl_109": "If CURRENT_SUBGOAL explicitly contains argument values, copy them exactly into the current call. Before returning, compare every argument against CURRENT_SUBGOAL. Values from earlier or later repeated calls must not replace the current value.",
    "bfcl_149": "Preserve user-provided named-entity spans verbatim, including qualifiers such as state abbreviations and country names, unless the tool schema explicitly requires a different normalization. Across repeated calls, keep shared fields unchanged.",
    "bfcl_29": "For a non-required parameter, include it only when the user explicitly requests the capability represented by that parameter or an earlier observation provides its value. Otherwise omit it; if the interface requires it, use the documented default. Never turn an optional boolean on merely because it is available.",
    "bfcl_56": "For a downstream object reference, first copy the stable ID or exact name from a previous tool output. If the environment explicitly provides no output, fall back to the exact minimal entity span from the user query; do not synthesize a new descriptive label by combining constraints.",
}


class TracingClient:
    def __init__(self, inner: LLMClient):
        self.inner = inner
        self.calls: list[dict] = []

    def generate(self, messages, *args, **kwargs):
        output = self.inner.generate(messages, *args, **kwargs)
        self.calls.append({"method": "generate", "messages": messages, "raw_output": output})
        return output

    def generate_json(self, messages):
        before = len(self.calls)
        parsed = self.inner.generate_json(messages)
        # LLMClient.generate_json does not expose raw text. Keep parsed output and
        # full messages; Caller uses generate_json_with_trace below for raw output.
        if len(self.calls) == before:
            self.calls.append({"method": "generate_json", "messages": messages,
                               "parsed_output": parsed})
        return parsed

    def generate_json_with_trace(self, messages):
        parsed, trace = self.inner.generate_json_with_trace(messages)
        self.calls.append({"method": "generate_json_with_trace", "messages": messages,
                           "raw_output": trace.get("raw_output"),
                           "parse_success": trace.get("parse_success"),
                           "parsed_output": parsed})
        return parsed, trace


def _load_rows(path: Path) -> dict[str, dict]:
    rows = {}
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                row = json.loads(line)
                rows[row["sample_id"]] = row
    return rows


def _state_step(subgoal: str, tool: str, args: dict, output=None, status="no_execution"):
    return {"subgoal": subgoal, "tool": tool, "arguments": args,
            "status": status, "output": output}


def _field_diff(predicted: list[dict], oracle: list[dict]) -> list[dict]:
    diffs = []
    for idx in range(max(len(predicted), len(oracle))):
        p = predicted[idx] if idx < len(predicted) else None
        o = oracle[idx] if idx < len(oracle) else None
        if p == o:
            continue
        diffs.append({"call_index": idx, "expected": o, "actual": p})
    return diffs


def _caller_hint(case_id: str, idx: int) -> str:
    call = ORACLE_CALLS[case_id][idx]
    return (
        "\n\nAUTHORITATIVE_BINDINGS_FOR_CURRENT_CALL:\n"
        + json.dumps(call["args"], ensure_ascii=False, separators=(",", ":"))
        + "\nCopy these bindings exactly. Do not import values from sibling calls."
    )


def _run_frozen_caller(client, instance, baseline, caller_spec: str,
                       hint: bool = False, simulated_state: bool = False):
    plan = list(baseline["plan"])
    baseline_calls = baseline["predicted_calls"]
    state = {}
    predicted = []
    traces = []
    for idx, subgoal in enumerate(plan):
        if idx >= len(baseline_calls):
            break
        tool_name = baseline_calls[idx]["tool"]
        card = registry.find_tool(instance["available_tools"], tool_name)
        caller_subgoal = subgoal + (_caller_hint(instance["id"], idx) if hint else "")
        trace = {}
        args = modules.run_caller(client, caller_spec, card, instance["query"],
                                  caller_subgoal, state, use_schema=True,
                                  trace_out=trace)
        trace["arguments_before_repair"] = args
        trace["repair_edits"] = []
        trace["arguments_after_repair"] = args
        predicted.append({"tool": tool_name, "args": args, "status": "no_execution"})
        output = None
        status = "no_execution"
        if simulated_state and instance["id"] == "bfcl_56" and idx == 0:
            output = {"name": "spaghetti"}
            status = "simulated_success"
        state[f"step_{idx + 1}"] = _state_step(subgoal, tool_name, args, output, status)
        traces.append(trace)
    return plan, predicted, traces


def _run_from_plan(client, instance, plan: list[str], caller_spec: str):
    state = {}
    predicted = []
    traces = []
    for idx, subgoal in enumerate(plan):
        tool_name = modules.run_selector(client, INITIAL_SELECTOR, instance["query"],
                                         subgoal, state, instance["available_tools"])
        card = registry.find_tool(instance["available_tools"], tool_name)
        trace = {}
        args = modules.run_caller(client, caller_spec, card, instance["query"],
                                  subgoal, state, use_schema=True, trace_out=trace) if card else {}
        trace["arguments_before_repair"] = args
        trace["repair_edits"] = []
        trace["arguments_after_repair"] = args
        predicted.append({"tool": tool_name, "args": args, "status": "no_execution"})
        state[f"step_{idx + 1}"] = _state_step(subgoal, tool_name, args)
        traces.append(trace)
    return predicted, traces


def run_condition(client, instance, baseline, condition: str):
    case_id = instance["id"]
    changed_module = "none"
    oracle_used = False
    frozen_plan = False

    if condition == "baseline_recorded":
        plan = baseline["plan"]
        predicted = baseline["predicted_calls"]
        traces = baseline.get("caller_traces") or []
    elif condition == "oracle_args":
        plan = baseline["plan"]
        predicted = [{**c, "status": "no_execution"} for c in ORACLE_CALLS[case_id]]
        traces = []
        oracle_used = True
        frozen_plan = True
        changed_module = "caller_output_override"
    elif condition == "caller_hint":
        plan, predicted, traces = _run_frozen_caller(
            client, instance, baseline, G15_CALLER, hint=True)
        oracle_used = True
        frozen_plan = True
        changed_module = "caller_input"
    elif condition == "caller_prompt":
        plan, predicted, traces = _run_frozen_caller(
            client, instance, baseline, G15_CALLER + " " + CALLER_RULES[case_id])
        frozen_plan = True
        changed_module = "caller_prompt"
    elif condition == "caller_rollback":
        plan, predicted, traces = _run_frozen_caller(
            client, instance, baseline, INITIAL_CALLER)
        frozen_plan = True
        changed_module = "caller_prompt"
    elif condition == "simulated_state":
        if case_id != "bfcl_56":
            return None
        plan, predicted, traces = _run_frozen_caller(
            client, instance, baseline, G15_CALLER, simulated_state=True)
        frozen_plan = True
        changed_module = "state"
    elif condition in ("oracle_plan", "oracle_plan_query_anchor"):
        if condition == "oracle_plan_query_anchor" and case_id != "bfcl_56":
            return None
        plan = (QUERY_ANCHOR_PLAN_56 if condition == "oracle_plan_query_anchor"
                else ORACLE_PLANS[case_id])
        predicted, traces = _run_from_plan(client, instance, plan, G15_CALLER)
        oracle_used = True
        changed_module = "planner_output_override"
    elif condition in ("planner_prompt", "combined_prompt"):
        planner_spec = INITIAL_PLANNER + " " + PLANNER_RULES[case_id]
        plan = modules.run_planner(client, planner_spec, instance["query"],
                                   instance["available_tools"], use_tool_context=True)
        caller_spec = (G15_CALLER + " " + CALLER_RULES[case_id]
                       if condition == "combined_prompt" else G15_CALLER)
        predicted, traces = _run_from_plan(client, instance, plan, caller_spec)
        changed_module = "planner_prompt+caller_prompt" if condition == "combined_prompt" else "planner_prompt"
    else:
        raise ValueError(f"unknown condition: {condition}")

    success = bfcl_ast_success(instance, predicted)
    return {
        "sample_id": case_id,
        "condition": condition,
        "changed_module": changed_module,
        "oracle_information_used": oracle_used,
        "frozen_plan": frozen_plan,
        "plan": plan,
        "predicted_calls": predicted,
        "gold_calls": instance.get("gold_match"),
        "success": success,
        "field_diff_from_oracle": _field_diff(predicted, ORACLE_CALLS[case_id]),
        "caller_traces": traces,
        "error_analysis": diagnose_bfcl(instance, predicted, traces),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="configs/bfcl_aligned_evolution.yaml")
    parser.add_argument("--episodes", default="results/aligned_comparison_3ep/evolution.episodes.jsonl")
    parser.add_argument("--cases", nargs="+", default=list(CASE_IDS))
    parser.add_argument("--conditions", nargs="+", default=[
        "baseline_recorded", "oracle_args", "caller_hint", "oracle_plan",
        "caller_prompt", "caller_rollback", "planner_prompt", "combined_prompt",
        "oracle_plan_query_anchor", "simulated_state",
    ])
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    out = Path(args.out)
    if out.exists():
        raise SystemExit(f"refusing to overwrite existing output: {out}")

    cfg = build_config(str(ROOT / args.config))
    inner = LLMClient(cfg.llm)
    client = TracingClient(inner)
    instances = {x["id"]: x for x in load_instances("bfcl", cfg.data_path)}
    baseline_rows = _load_rows(ROOT / args.episodes)

    records = []
    for case_id in args.cases:
        if case_id not in CASE_IDS:
            raise SystemExit(f"unsupported case: {case_id}")
        for condition in args.conditions:
            start = len(client.calls)
            print(f"RUN {case_id} {condition}", flush=True)
            record = run_condition(client, instances[case_id], baseline_rows[case_id], condition)
            if record is None:
                continue
            record["llm_calls"] = client.calls[start:]
            records.append(record)
            print(f"  success={record['success']} calls={len(record['predicted_calls'])}", flush=True)

    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")

    summary = {
        "post_hoc_diagnostic": True,
        "model": cfg.llm.model_name,
        "temperature": cfg.llm.temperature,
        "cases": args.cases,
        "conditions": args.conditions,
        "total_tokens": inner.total_tokens,
        "results": {
            case_id: {
                condition: next((r["success"] for r in records
                                 if r["sample_id"] == case_id
                                 and r["condition"] == condition), None)
                for condition in args.conditions
            }
            for case_id in args.cases
        },
    }
    summary_path = out.with_suffix(".summary.json")
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2), flush=True)
    print(f"saved -> {out}", flush=True)
    print(f"summary -> {summary_path}", flush=True)


if __name__ == "__main__":
    main()
