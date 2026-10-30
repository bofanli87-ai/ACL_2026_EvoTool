"""Trajectory-grounded diagnostics (the EXTRACTDIAGNOSTICS step).

Turns an episode into per-module structured events by comparing the predicted
trajectory against the gold plan and the tool index, and by reading execution
statuses. These events are ADVISORY HINTS only (paper §4.1): the Blamer LLM is
the decision-maker and reads the full trajectory itself, so it may override them.
They never decide the blamed module. `rule_blame` below is consulted ONLY as a
fallback when the Blamer's output is unparseable.

The advisory routing of an event to a module:

  - missing gold steps / wrong decomposition  -> Planner
  - invalid (hallucinated) tool selection      -> Selector
  - execution errors (e.g. missing protocol token), empty args -> Caller
  - empty / ungrounded final answer            -> Synthesizer
"""

from __future__ import annotations

from collections import Counter
from src.eval_bfcl_ast import _call_matches_gold

from src.policy.agent import Episode
from src.policy.modules import MODULES


def extract_diagnostics(episode: Episode, instance: dict) -> dict:
    gold_tools = [s.get("tool") for s in instance.get("gold_plan", [])]
    available = set(t["name"] for t in instance["available_tools"])
    pred_tools = [s.tool for s in episode.steps]

    events: dict[str, list[str]] = {m: [] for m in MODULES}

    # Planner: decomposition quality. In the selector-driven loop the plan is
    # high-level guidance (the selector drives tool choice), so the planner is
    # blamed for a missing/over-long decomposition, not for tool choice.
    if len(episode.plan) < len(gold_tools):
        events["planner"].append(
            f"under-decomposition: planned {len(episode.plan)} steps but the task needs ~{len(gold_tools)}")
    elif len(episode.plan) > len(gold_tools) + 2:
        events["planner"].append("over-decomposition: many more steps than the task needs")

    # Selector: WHICH tools got called (it drives the loop). Missing required tools
    # or hallucinated tools are selection failures.
    missing = list((Counter(gold_tools) - Counter(pred_tools)).elements())
    if missing:
        events["selector"].append(f"required tools were never selected: {missing}")
    invalid = [t for t in pred_tools if t not in available]
    if invalid:
        events["selector"].append(f"selected tools not in the index (hallucinated): {invalid}")

    # Caller: execution failures, empty arguments, and arguments that differ from
    # the expected gold values (the latter is what breaks tau-bench's DB state).
    # Maximum one-to-one matching preserves repeated calls and overlapping BFCL
    # allowed-value sets. Unmatched calls are symptoms, not causal attribution.
    gold = instance.get("gold_match")
    if gold is None:
        gold = [{s.get("tool"): {k: [v] for k, v in (s.get("args") or {}).items()}}
                for s in instance.get("gold_plan", [])]
    owners = {}

    def assign(pi, seen):
        step = episode.steps[pi]
        for gi, spec in enumerate(gold):
            if gi in seen or not _call_matches_gold({"tool": step.tool, "args": step.args}, spec):
                continue
            seen.add(gi)
            if gi not in owners or assign(owners[gi], seen):
                owners[gi] = pi
                return True
        return False

    for pi in range(len(episode.steps)):
        assign(pi, set())
    matched = set(owners.values())
    gold_names = [next(iter(spec)) for spec in gold]
    excess = list((Counter(pred_tools) - Counter(gold_names)).elements())
    if excess:
        events["planner"].append(f"extra call occurrences (check plan/selection): {excess}")
    for pi, s in enumerate(episode.steps):
        out = str(s.observation.get("output", ""))
        if s.observation.get("status") == "error" and s.tool in available:
            events["caller"].append(f"call to '{s.tool}' failed -> {out}")
        elif (pi not in matched and s.tool in gold_names
              and s.observation.get("status") != "success"):
            # Only blame the caller for an argument mismatch when the gold args are
            # non-empty AND the call did NOT succeed. The paper's Caller criterion is
            # malformed/wrong calls that *cause* failure; a successful call (or a tool
            # whose gold args are empty, e.g. RestBench, whose metric ignores args) is
            # not a caller fault, so flagging it just misroutes blame.
            events["caller"].append(
                f"step {pi + 1}: '{s.tool}' has no distinct matching reference call; "
                "check arguments or duplicate call (not proof of Caller causality)")

    # Synthesizer: grounding of the final answer.
    gold_answer = (instance.get("gold_answer") or "").lower()
    if not episode.answer.strip():
        events["synthesizer"].append("empty final answer")
    elif gold_answer and gold_answer not in episode.answer.lower():
        key = gold_answer.split()[0] if gold_answer else ""
        if key and key not in episode.answer.lower():
            events["synthesizer"].append("final answer not grounded in the gold result")

    return {
        "events": events,
        "pred_tools": pred_tools,
        "gold_tools": gold_tools,
        "reward": episode.reward,
        "statuses": [s.observation.get("status") for s in episode.steps],
        "call_matches": [{"predicted_index": pi, "gold_index": gi}
                         for gi, pi in sorted(owners.items())],
        "unmatched_predicted": [i for i in range(len(episode.steps)) if i not in matched],
        "unmatched_gold": [i for i in range(len(gold)) if i not in owners],
    }


def rule_blame(diagnostics: dict) -> str:
    """Unparseable-output fallback ONLY (the Blamer LLM is the decision-maker;
    see blame.py). Blames the earliest-in-pipeline module that has an event."""
    events = diagnostics["events"]
    for m in MODULES:  # planner -> selector -> caller -> synthesizer
        if events[m]:
            return m
    return "caller"


def render_events(diagnostics: dict) -> str:
    lines = []
    for m in MODULES:
        evs = diagnostics["events"][m]
        lines.append(f"[{m}] " + ("; ".join(evs) if evs else "no issues detected"))
    return "\n".join(lines)
