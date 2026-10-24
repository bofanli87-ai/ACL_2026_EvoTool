"""Build a prefilled human-audit sheet for the Planner100 experiment.

Automatic hints organize the evidence but never replace the human cause label.
Run from the repository root; the CSV is safe to edit in Excel.
"""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from pathlib import Path


CONDITIONS = ("control", "planner_tools", "history", "tools_history")


def _load(path: Path) -> dict[str, dict]:
    return {
        row["sample_id"]: row
        for row in map(json.loads, path.read_text(encoding="utf-8").splitlines())
    }


def _gold_calls(row: dict) -> list[dict]:
    calls = []
    for spec in row.get("gold_calls") or []:
        (tool, args), = spec.items()
        calls.append({"tool": tool, "args": args})
    return calls


def _duplicate_calls(calls: list[dict]) -> bool:
    rendered = [json.dumps(call, sort_keys=True, ensure_ascii=False) for call in calls]
    return len(rendered) != len(set(rendered))


def _repeated_tool_with_distinct_gold_args(row: dict) -> bool:
    pred = row.get("predicted_calls") or []
    gold = _gold_calls(row)
    pred_tools = Counter(call.get("tool") for call in pred)
    for tool, count in pred_tools.items():
        if count < 2:
            continue
        gold_args = {
            json.dumps(call.get("args") or {}, sort_keys=True, ensure_ascii=False)
            for call in gold if call.get("tool") == tool
        }
        if len(gold_args) >= 2:
            return True
    return False


def _auto_hints(row: dict) -> list[str]:
    pred = row.get("predicted_calls") or []
    gold = _gold_calls(row)
    analysis = row.get("error_analysis") or {}
    labels = set(analysis.get("labels") or [])
    issues = {
        detail.get("issue") for detail in analysis.get("details") or []
    }
    hints = []
    if len(pred) != len(gold):
        hints.append("call_count")
    if "selection" in labels:
        hints.append("tool_selection")
    if _duplicate_calls(pred) and _repeated_tool_with_distinct_gold_args(row):
        hints.append("step_entity_binding/repeated_args")
    if "optional_parameter_should_be_omitted" in issues:
        hints.append("optional_parameter")
    if "schema_interface" in labels:
        hints.append("nested_or_schema_value")
    if "semantic_argument" in labels:
        hints.append("semantic_or_canonicalization")
    return hints or ["unclassified"]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--results", default="results/planner100")
    parser.add_argument("--out", default="results/planner100/manual_audit.csv")
    parser.add_argument(
        "--scope", choices=("combo_failures", "all_changed"), default="combo_failures")
    args = parser.parse_args()

    result_dir = Path(args.results)
    runs = {
        name: _load(result_dir / f"{name}.episodes.jsonl") for name in CONDITIONS
    }
    ids = set(runs["control"])
    if any(set(run) != ids for run in runs.values()):
        raise SystemExit("Condition sample IDs differ.")

    if args.scope == "combo_failures":
        selected = [sid for sid in ids if not runs["tools_history"][sid]["success"]]
    else:
        selected = [
            sid for sid in ids
            if len({bool(runs[name][sid]["success"]) for name in CONDITIONS}) > 1
        ]

    fields = [
        "sample_id", "control", "planner_tools", "history", "tools_history",
        "automatic_hints", "primary_error_label", "predicted_call_count",
        "gold_call_count", "plan", "predicted_calls", "gold_calls", "query",
        "human_primary_cause", "first_divergence_stage", "information_lost",
        "coupled_secondary_errors", "benchmark_or_evaluator_issue",
        "minimal_general_fix", "confidence", "notes",
    ]
    output = Path(args.out)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for sid in sorted(selected, key=lambda value: int(value.split("_")[-1])):
            row = runs["tools_history"][sid]
            writer.writerow({
                "sample_id": sid,
                **{name: int(bool(runs[name][sid]["success"])) for name in CONDITIONS},
                "automatic_hints": ";".join(_auto_hints(row)),
                "primary_error_label": (row.get("error_analysis") or {}).get("primary_label"),
                "predicted_call_count": len(row.get("predicted_calls") or []),
                "gold_call_count": len(row.get("gold_calls") or []),
                "plan": json.dumps(row.get("plan"), ensure_ascii=False),
                "predicted_calls": json.dumps(row.get("predicted_calls"), ensure_ascii=False),
                "gold_calls": json.dumps(row.get("gold_calls"), ensure_ascii=False),
                "query": row.get("query"),
            })
    print(f"wrote {len(selected)} rows -> {output}")


if __name__ == "__main__":
    main()
