"""Run the paired 2x2 Planner-information/history ablation on 100 BFCL tasks.

The selected samples (seed 42, shuffled positions 0:100) are disjoint from the
previous 30-sample held-out split (positions 120:150). All four conditions use
the same frozen initial policy, Caller schema, model settings, and sample IDs.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONDITIONS = [
    ("control", "bfcl_planner100_control"),
    ("planner_tools", "bfcl_planner100_tools"),
    ("history", "bfcl_planner100_history"),
    ("tools_history", "bfcl_planner100_tools_history"),
]


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _test_ids(config_path: Path) -> list[str]:
    sys.path.insert(0, str(ROOT))
    from run import build_config
    from src.benchmarks import load_instances, split_instances

    cfg = build_config(str(config_path))
    _, _, test = split_instances(load_instances("bfcl", cfg.data_path), cfg)
    return [item["id"] for item in test]


def _load_episode_ids(path: Path) -> set[str]:
    if not path.exists():
        return set()
    return {
        json.loads(line)["sample_id"]
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--outdir", default="results/planner100")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    os.chdir(ROOT)

    outdir = (ROOT / args.outdir).resolve()
    configs = [(label, ROOT / "configs" / f"{name}.yaml")
               for label, name in CONDITIONS]
    ids_by_condition = {label: _test_ids(path) for label, path in configs}
    first_ids = ids_by_condition[CONDITIONS[0][0]]
    if len(first_ids) != 100 or any(ids != first_ids for ids in ids_by_condition.values()):
        raise SystemExit("The four conditions do not resolve to the same 100 sample IDs.")

    prior_path = ROOT / "results" / "diag_schema.episodes.jsonl"
    prior_ids = _load_episode_ids(prior_path)
    overlap = sorted(set(first_ids) & prior_ids)
    if prior_ids and overlap:
        raise SystemExit(f"Expanded set overlaps the prior 30-sample test: {overlap}")

    outputs = {label: outdir / f"{label}.json" for label, _ in configs}
    existing = [str(path) for path in outputs.values() if path.exists()]
    if existing and not args.dry_run:
        raise SystemExit("Refusing to overwrite existing results: " + ", ".join(existing))

    commands = []
    for (label, config_path) in configs:
        commands.append([
            sys.executable, "run.py", "--config", str(config_path),
            "--benchmark", "bfcl", "--out", str(outputs[label]),
            "--override", f"output_path={outdir}",
        ])

    manifest = {
        "purpose": "confirmatory paired 2x2 planner-tool-context x structured-history ablation",
        "n_samples": len(first_ids),
        "seed": 42,
        "sample_ids": first_ids,
        "prior_30_path": str(prior_path.relative_to(ROOT)),
        "overlap_with_prior_30": overlap,
        "data_sha256": _sha256(ROOT / "data_schema" / "bfcl" / "samples.json"),
        "conditions": {
            label: {
                "config": str(path.relative_to(ROOT)),
                "result": str(outputs[label]),
            }
            for label, path in configs
        },
        "commands": commands,
    }
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    if args.dry_run:
        return

    outdir.mkdir(parents=True, exist_ok=True)
    (outdir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    for command in commands:
        subprocess.run(command, cwd=ROOT, check=True)

    analysis_command = [
        sys.executable, "scripts/analyze_bfcl_conditions.py", "--runs",
        *[
            f"{label}={outputs[label].with_suffix('.episodes.jsonl')}"
            for label, _ in configs
        ],
        "--baseline", "control",
        "--factorial", "control", "planner_tools", "history", "tools_history",
        "--json-out", str(outdir / "comparison.json"),
    ]
    subprocess.run(analysis_command, cwd=ROOT, check=True)


if __name__ == "__main__":
    main()
