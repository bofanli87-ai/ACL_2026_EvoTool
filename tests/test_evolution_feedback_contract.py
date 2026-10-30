"""Offline regression tests for the diagnosis-to-mutation data contract."""
import unittest
from types import SimpleNamespace

from src.evolve.blame import blame
from src.evolve.diagnostics import extract_diagnostics
from src.evolve.loop import _make_child
from src.policy.agent import Episode, Step
from src.policy.modules import initial_policy, MODULES
from src.config import EvoToolConfig


class Client:
    def __init__(self, response):
        self.response = response
        self.messages = None

    def generate_json(self, messages):
        self.messages = messages
        return self.response


def episode(values=(10, 20)):
    instance = dict(query="Look up two records", available_tools=[{"name": "lookup"}],
                    gold_plan=[{"tool": "lookup", "args": {"x": v}} for v in (10, 20)],
                    gold_match=[{"lookup": {"x": [v]}} for v in (10, 20)])
    steps = [Step("lookup", "lookup", {"x": v}, {"status": "no_execution"}) for v in values]
    return Episode(instance, ["lookup"] * len(values), steps, "answer", 0.15)


class FeedbackContract(unittest.TestCase):
    def test_repeated_calls_and_reordering(self):
        ep = episode((20, 10))
        diag = extract_diagnostics(ep, ep.instance)
        self.assertEqual(diag["events"]["caller"], [])
        self.assertEqual(diag["unmatched_gold"], [])

    def test_duplicate_and_missing_calls(self):
        ep = episode((10, 10))
        diag = extract_diagnostics(ep, ep.instance)
        self.assertEqual(len(diag["unmatched_predicted"]), 1)
        self.assertEqual(len(diag["unmatched_gold"]), 1)
        ep = episode((10,))
        diag = extract_diagnostics(ep, ep.instance)
        self.assertTrue(diag["events"]["selector"])

    def test_overlapping_allowed_values_needs_reassignment(self):
        ep = episode((10, 20))
        ep.instance["gold_match"] = [{"lookup": {"x": [10, 20]}}, {"lookup": {"x": [10]}}]
        self.assertEqual(extract_diagnostics(ep, ep.instance)["unmatched_gold"], [])

    def test_score_conflict_and_invalid_scores(self):
        ep = episode()
        diag = extract_diagnostics(ep, ep.instance)
        scores = dict(planner=0.9, selector=0.1, caller=0.2, synthesizer=0.0, primary="caller")
        trace = {}
        self.assertEqual(blame(Client(scores), ep, diag, trace), "planner")
        self.assertTrue(trace["_primary_conflict"])
        for invalid in (float("nan"), True, "0.9", -1, 2):
            blame(Client({**scores, "planner": invalid}), ep, diag, trace)
            self.assertEqual(trace["_resolved_by"], "rule_fallback")

    def test_rationale_reaches_mutator_and_ablation_removes_it(self):
        ep = episode()
        cfg = EvoToolConfig()
        parent = initial_policy()
        client = Client({"target_module": "planner", "revised_spec": "A general revised rule"})
        rationale = {"diagnosis": "UNIQUE_DIAGNOSIS", "planner": 0.9}
        trace = {}
        child = _make_child(client, parent, "planner", ep, extract_diagnostics(ep, ep.instance),
                            cfg, "child", rationale, trace)
        self.assertIn("UNIQUE_DIAGNOSIS", str(client.messages))
        self.assertTrue(trace["valid"])
        for m in MODULES:
            if m != "planner":
                self.assertEqual(parent.spec(m), child.spec(m))
        cfg.evolve.use_feedback = False
        _make_child(client, parent, "planner", ep, extract_diagnostics(ep, ep.instance),
                    cfg, "child", rationale)
        self.assertNotIn("UNIQUE_DIAGNOSIS", str(client.messages))

    def test_invalid_mutations_are_noops(self):
        ep = episode()
        parent = initial_policy()
        for response in ({"target_module": "caller", "revised_spec": "rule"},
                         {"target_module": "planner", "revised_spec": {"rule": 1}},
                         {"target_module": "planner", "revised_spec": parent.planner}):
            trace = {}
            child = _make_child(Client(response), parent, "planner", ep,
                                extract_diagnostics(ep, ep.instance), EvoToolConfig(), "child",
                                {}, trace)
            self.assertIs(child, parent)
            self.assertFalse(trace["valid"])


if __name__ == "__main__":
    unittest.main()
