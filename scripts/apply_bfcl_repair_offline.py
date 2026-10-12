"""Apply deterministic schema repair to one fixed BFCL episode artifact.

This paired counterfactual avoids attributing model rerun variance to Repair.
The script reads schemas from benchmark inputs but never uses gold values to edit a
prediction; gold is consulted only afterward for evaluation and reporting.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.bfcl_error_analysis import diagnose_bfcl
from src.eval_bfcl_ast import bfcl_ast_success
from src.metrics import progress
from src.schema_repair import repair_arguments


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--episodes", required=True)
    parser.add_argument("--data", default="data_schema/bfcl/samples.json")
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    with Path(args.data).open("r", encoding="utf-8") as handle:
        instances = {item["id"]: item for item in json.load(handle)}

    rows = []
    with Path(args.episodes).open("r", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                rows.append(json.loads(line))

    total_edits = 0
    changed_samples = 0
    before_success = sum(bool(row.get("success")) for row in rows)
    after_success = 0
    output = Path(args.out)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8") as handle:
        for row in rows:
            instance = instances[row["sample_id"]]
            tools = {tool["name"]: tool for tool in instance.get("available_tools", [])}
            repaired_calls = []
            traces = []
            sample_edits = 0
            for idx, call in enumerate(row.get("predicted_calls") or []):
                tool = tools.get(call.get("tool"))
                before = call.get("args") or {}
                after, edits = repair_arguments(
                    before, tool.get("parameter_schema") if tool else None)
                repaired_calls.append({**call, "args": after})
                original_trace = ((row.get("caller_traces") or []) + [{}] * (idx + 1))[idx]
                traces.append({**original_trace, "offline_arguments_before_repair": before,
                               "offline_arguments_after_repair": after,
                               "offline_repair_edits": edits})
                sample_edits += len(edits)
            success = bfcl_ast_success(instance, repaired_calls)
            reward = 0.7 * float(success) + 0.3 * progress(repaired_calls, instance)
            diagnosis = diagnose_bfcl(instance, repaired_calls, traces)
            record = {**row, "predicted_calls": repaired_calls, "success": success,
                      "reward": reward, "caller_repair": True, "caller_traces": traces,
                      "error_analysis": diagnosis, "offline_repair_source": args.episodes,
                      "offline_repair_edit_count": sample_edits}
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
            total_edits += sample_edits
            changed_samples += int(sample_edits > 0)
            after_success += int(success)
    print(f"samples={len(rows)} before_success={before_success} after_success={after_success} "
          f"changed_samples={changed_samples} edits={total_edits}")
    print(f"saved -> {output}")


if __name__ == "__main__":
    main()
