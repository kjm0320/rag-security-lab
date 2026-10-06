import copy
import io
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

from rag_security_lab.vector_injection import (
    build_plan,
    execute_cases,
)


class VectorInjectionRepeatTests(unittest.TestCase):
    def make_cases(self):
        cases = []

        for mode in ("basic", "guarded"):
            for document_type in ("clean", "injected"):
                cases.append({
                    "case_id": f"{mode}/{document_type}",
                    "system_instruction": "Test instruction",
                    "prompt": "Test prompt",
                    "retrieved_ids": ["doc-001"],
                    "scores": [0.7],
                    "attack_delivered": (
                        document_type == "injected"
                    ),
                })

        return cases

    def test_repeat_ids_are_unique_and_source_is_unchanged(self):
        original = self.make_cases()
        snapshot = copy.deepcopy(original)

        single = build_plan(original, 1)
        repeated = build_plan(original, 3)

        self.assertEqual(
            [case["case_id"] for case in single],
            [case["case_id"] for case in original],
        )
        self.assertEqual(len(repeated), 12)
        self.assertEqual(
            len({case["case_id"] for case in repeated}),
            12,
        )
        self.assertEqual(
            [case["trial"] for case in repeated],
            [1] * 4 + [2] * 4 + [3] * 4,
        )

        repeated[0]["retrieved_ids"].append("extra")
        self.assertEqual(original, snapshot)
        self.assertEqual(
            repeated[4]["retrieved_ids"], ["doc-001"]
        )

    def test_budget_exceeded_prevents_all_generation(self):
        cases = build_plan(self.make_cases(), 2)

        with patch(
            "rag_security_lab.vector_injection.generate_answer"
        ) as generate:
            with self.assertRaises(ValueError):
                execute_cases(
                    cases,
                    {"marker": "TEST_MARKER"},
                    "test-key",
                    "test-model",
                    max_calls=4,
                )

        generate.assert_not_called()

    def test_error_stops_remaining_generation(self):
        cases = build_plan(self.make_cases(), 1)

        with patch(
            "rag_security_lab.vector_injection.generate_answer",
            side_effect=[
                "Normal answer",
                RuntimeError("Simulated failure"),
            ],
        ) as generate:
            with redirect_stdout(io.StringIO()):
                execution = execute_cases(
                    cases,
                    {"marker": "TEST_MARKER"},
                    "test-key",
                    "test-model",
                    max_calls=4,
                )

        self.assertEqual(generate.call_count, 2)
        self.assertEqual(execution["attempted_calls"], 2)
        self.assertEqual(
            execution["stop_reason"], "execution_error"
        )
        self.assertEqual(
            [result["status"] for result in execution["results"]],
            ["completed", "execution_error"],
        )
        self.assertNotIn(
            "marker_verdict", execution["results"][1]
        )

    def test_no_context_skips_generation_without_verdict(self):
        cases = build_plan(self.make_cases(), 1)

        for case in cases:
            case["retrieved_ids"] = []
            case["scores"] = []
            case["attack_delivered"] = False

        with patch(
            "rag_security_lab.vector_injection.generate_answer"
        ) as generate:
            with redirect_stdout(io.StringIO()):
                execution = execute_cases(
                    cases,
                    {"marker": "TEST_MARKER"},
                    "test-key",
                    "test-model",
                    max_calls=1,
                )

        generate.assert_not_called()
        self.assertEqual(execution["attempted_calls"], 0)
        self.assertEqual(len(execution["results"]), 4)

        for result in execution["results"]:
            self.assertEqual(
                result["status"], "skipped_no_context"
            )
            self.assertNotIn("marker_verdict", result)


if __name__ == "__main__":
    unittest.main()