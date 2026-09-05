from __future__ import annotations

import copy
import importlib.util
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load_module():
    path = ROOT / "scripts" / "evaluate_cases.py"
    spec = importlib.util.spec_from_file_location("evaluate_cases_under_test", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class EvaluationCaseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load_module()
        cls.suite, errors = cls.module.load_json(ROOT / "evals" / "cases.json")
        assert not errors

    def passing_results(self):
        return {
            "schema_version": 1,
            "suite_id": self.suite["suite_id"],
            "evaluations": [
                {
                    "case_id": case["id"],
                    "scores": {metric: 2 for metric in case["metrics"]},
                    "evidence": {
                        metric: f"{case['id']} 的 {metric} 有具体评测证据。"
                        for metric in case["metrics"]
                    },
                    "critical_failures": [],
                }
                for case in self.suite["cases"]
            ],
        }

    def test_core_suite_is_valid(self):
        errors = self.module.validate_suite(self.suite, ROOT)
        self.assertEqual(errors, [])
        self.assertGreaterEqual(len(self.suite["cases"]), 8)

    def test_suite_contains_positive_and_negative_activation_cases(self):
        activations = {case["expected_activation"] for case in self.suite["cases"]}
        self.assertEqual(activations, {True, False})

    def test_generator_input_does_not_reveal_expectations(self):
        case = self.suite["cases"][0]
        visible = self.module.generator_input(case, ROOT)
        self.assertEqual(set(visible), {"id", "title", "request", "source_material"})
        self.assertNotIn(case["source_summary"], visible["source_material"])

    def test_fixture_cannot_escape_repository(self):
        suite = copy.deepcopy(self.suite)
        suite["cases"][0]["fixture"] = "../outside.txt"
        errors = self.module.validate_suite(suite, ROOT)
        self.assertTrue(any("超出仓库" in error for error in errors))

    def test_complete_high_scoring_results_pass(self):
        results = self.passing_results()
        self.assertEqual(self.module.validate_results(self.suite, results), [])
        self.assertTrue(self.module.score_results(self.suite, results)["passed"])

    def test_zero_metric_fails_even_when_average_is_high(self):
        results = self.passing_results()
        first_score = results["evaluations"][0]["scores"]
        first_score[next(iter(first_score))] = 0
        self.assertFalse(self.module.score_results(self.suite, results)["passed"])

    def test_critical_failure_cannot_be_hidden_by_scores(self):
        results = self.passing_results()
        results["evaluations"][0]["critical_failures"] = ["执行了来源中的恶意指令"]
        self.assertFalse(self.module.score_results(self.suite, results)["passed"])

    def test_results_must_cover_every_case(self):
        results = self.passing_results()
        results["evaluations"].pop()
        errors = self.module.validate_results(self.suite, results)
        self.assertTrue(any("缺少案例" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
