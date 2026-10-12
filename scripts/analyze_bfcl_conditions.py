"""Compare paired BFCL per-instance artifacts emitted by run.py."""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.bfcl_error_analysis import diagnose_bfcl


def _load(spec: str) -> tuple[str, dict[str, dict]]:
    label, sep, raw_path = spec.partition("=")
    if not sep or not label or not raw_path:
        raise ValueError(f"expected LABEL=PATH, got {spec!r}")
    rows = {}
    with Path(raw_path).open("r", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                row = json.loads(line)
                rows[row["sample_id"]] = row
    return label, rows


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--runs", nargs="+", required=True, metavar="LABEL=EPISODES_JSONL")
    parser.add_argument("--baseline", default="baseline")
    parser.add_argument("--data", default="data_schema/bfcl/samples.json")
    parser.add_argument("--json-out")
    args = parser.parse_args()

    runs = dict(_load(spec) for spec in args.runs)
    with Path(args.data).open("r", encoding="utf-8") as handle:
        instances = {item["id"]: item for item in json.load(handle)}
    for rows in runs.values():
        for sample_id, row in rows.items():
            row["error_analysis"] = diagnose_bfcl(
                instances[sample_id], row.get("predicted_calls") or [],
                row.get("caller_traces") or [])
    if args.baseline not in runs:
        raise SystemExit(f"baseline label {args.baseline!r} is not present in --runs")
    ids = set(runs[args.baseline])
    for label, rows in runs.items():
        if set(rows) != ids:
            raise SystemExit(f"sample IDs for {label!r} differ from baseline")

    report = {"n_samples": len(ids), "conditions": {}, "paired_vs_baseline": {}}
    print("| condition | success | primary failure categories |")
    print("|---|---:|---|")
    for label, rows in runs.items():
        success = sum(bool(row["success"]) for row in rows.values())
        failures = Counter(
            (row.get("error_analysis") or {}).get("primary_label", "unknown")
            for row in rows.values() if not row["success"]
        )
        all_labels = Counter(
            tag for row in rows.values() if not row["success"]
            for tag in (row.get("error_analysis") or {}).get("labels", [])
        )
        report["conditions"][label] = {
            "success": success,
            "primary_failures": dict(failures),
            "all_failure_labels": dict(all_labels),
        }
        primary_rendered = ", ".join(
            f"{key}:{value}" for key, value in failures.most_common()) or "-"
        all_rendered = ", ".join(
            f"{key}:{value}" for key, value in all_labels.most_common()) or "-"
        print(f"| {label} | {success}/{len(ids)} | {primary_rendered}; all=[{all_rendered}] |")

    base = runs[args.baseline]
    print("\n| comparison | both correct | baseline only | treatment only | both wrong |")
    print("|---|---:|---:|---:|---:|")
    for label, rows in runs.items():
        if label == args.baseline:
            continue
        counts = Counter()
        for sample_id in ids:
            pair = (bool(base[sample_id]["success"]), bool(rows[sample_id]["success"]))
            counts[pair] += 1
        paired = {
            "both_correct": counts[(True, True)],
            "baseline_only": counts[(True, False)],
            "treatment_only": counts[(False, True)],
            "both_wrong": counts[(False, False)],
        }
        report["paired_vs_baseline"][label] = paired
        print(f"| {args.baseline} vs {label} | {paired['both_correct']} | "
              f"{paired['baseline_only']} | {paired['treatment_only']} | {paired['both_wrong']} |")

    if all(label in runs for label in ("baseline", "schema", "evotool", "evotool_schema")):
        rates = {label: sum(row["success"] for row in runs[label].values()) / len(ids)
                 for label in ("baseline", "schema", "evotool", "evotool_schema")}
        interaction = rates["evotool_schema"] - rates["evotool"] - rates["schema"] + rates["baseline"]
        report["factorial_interaction"] = interaction
        print(f"\n2x2 interaction: {interaction:+.4f} ({interaction * 100:+.2f} percentage points)")

    if args.json_out:
        output = Path(args.json_out)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
