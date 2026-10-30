"""Run the matched BFCL static-vs-Evolution comparison after interface alignment.

The runner verifies that the two configs are identical except for the three
Evolution treatment fields, refuses to overwrite existing outputs, and writes
a machine-readable manifest and comparison summary.
"""

from __future__ import annotations

import argparse
import copy
import json
import subprocess
import sys
from dataclasses import asdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STATIC_CONFIG = ROOT / "configs" / "bfcl_aligned_static.yaml"
EVOLUTION_CONFIG = ROOT / "configs" / "bfcl_aligned_evolution.yaml"
TREATMENT_FIELDS = ("mutation_target", "selection", "epochs", "generations")


def _load_config(path: Path) -> dict:
    sys.path.insert(0, str(ROOT))
    from run import build_config

    return asdict(build_config(str(path)))


def _matched_snapshot(config: dict) -> dict:
    snapshot = copy.deepcopy(config)
    for field in TREATMENT_FIELDS:
        snapshot["evolve"].pop(field)
    return snapshot


def _read_result(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--outdir", default="results/aligned_comparison")
    parser.add_argument(
        "--epochs",
        type=int,
        default=1,
        help="Evolution epochs (repository budget, not a claim of paper equivalence).",
    )
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--generations", type=int, default=0,
                        help="Positive value overrides the epoch-derived generation count.")
    args = parser.parse_args()
    if args.epochs < 1:
        raise SystemExit("--epochs must be at least 1")
    if args.generations < 0:
        raise SystemExit("--generations must be nonnegative")

    static_config = _load_config(STATIC_CONFIG)
    evolution_config = _load_config(EVOLUTION_CONFIG)
    if _matched_snapshot(static_config) != _matched_snapshot(evolution_config):
        raise SystemExit(
            "Matched-control check failed: configs differ outside "
            + ", ".join(f"evolve.{field}" for field in TREATMENT_FIELDS)
        )

    outdir = (ROOT / args.outdir).resolve()
    outputs = {
        "static": outdir / "static.json",
        "evolution": outdir / "evolution.json",
    }
    commands = {
        "static": [
            sys.executable,
            "-u",
            "run.py",
            "--config",
            str(STATIC_CONFIG),
            "--benchmark",
            "bfcl",
            "--out",
            str(outputs["static"]),
            "--override",
            f"output_path={outdir}",
        ],
        "evolution": [
            sys.executable,
            "-u",
            "run.py",
            "--config",
            str(EVOLUTION_CONFIG),
            "--benchmark",
            "bfcl",
            "--out",
            str(outputs["evolution"]),
            "--override",
            f"output_path={outdir}",
            f"evolve.epochs={args.epochs}",
            f"evolve.generations={args.generations}",
        ],
    }
    manifest = {
        "purpose": "matched BFCL comparison after implemented interface alignment",
        "benchmark": "bfcl",
        "evolution_epochs": args.epochs,
        "evolution_generations_override": args.generations,
        "implementation_revision": "feedback_and_call_matching_v1",
        "treatment_fields": [f"evolve.{field}" for field in TREATMENT_FIELDS],
        "matched_settings": _matched_snapshot(static_config),
        "configs": {
            "static": str(STATIC_CONFIG.relative_to(ROOT)),
            "evolution": str(EVOLUTION_CONFIG.relative_to(ROOT)),
        },
        "outputs": {name: str(path) for name, path in outputs.items()},
        "commands": commands,
    }
    print(json.dumps(manifest, ensure_ascii=False, indent=2), flush=True)
    if args.dry_run:
        return

    existing = [str(path) for path in outputs.values() if path.exists()]
    if existing:
        raise SystemExit(
            "Refusing to overwrite existing results; choose a new --outdir: "
            + ", ".join(existing)
        )

    outdir.mkdir(parents=True, exist_ok=True)
    (outdir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    for name in ("static", "evolution"):
        subprocess.run(commands[name], cwd=ROOT, check=True)

    static_result = _read_result(outputs["static"])
    evolution_result = _read_result(outputs["evolution"])
    comparison = {
        "static_success_rate": static_result["success_rate"],
        "evolution_success_rate": evolution_result["success_rate"],
        "evolution_minus_static": round(
            evolution_result["success_rate"] - static_result["success_rate"], 2
        ),
        "static_tokens": static_result["tokens"],
        "evolution_tokens": evolution_result["tokens"],
        "static_result": str(outputs["static"]),
        "evolution_result": str(outputs["evolution"]),
        "static_episodes": static_result["test_episodes"],
        "evolution_episodes": evolution_result["test_episodes"],
    }
    (outdir / "comparison.json").write_text(
        json.dumps(comparison, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(comparison, ensure_ascii=False, indent=2))
    print(f"comparison -> {outdir / 'comparison.json'}")


if __name__ == "__main__":
    main()
