import unittest

from rag_security_lab.evaluate import evaluate, rate


class EvaluationTests(unittest.TestCase):
    def setUp(self):
        self.documents = [
            {
                "id": "public-doc",
                "title": "VPN",
                "text": "다중 인증 안내",
                "access": "public",
            },
            {
                "id": "secret-doc",
                "title": "관리자",
                "text": "실습용 비밀",
                "access": "restricted",
            },
        ]
        self.cases = [
            {
                "id": "normal",
                "kind": "normal",
                "query": "VPN",
                "role": "user",
                "expected_ids": ["public-doc"],
                "forbidden_ids": [],
            },
            {
                "id": "attack",
                "kind": "attack",
                "query": "관리자",
                "role": "user",
                "expected_ids": [],
                "forbidden_ids": ["secret-doc"],
            },
        ]

    def test_baseline_records_exposure_evidence(self):
        report = evaluate(self.documents, self.cases, "baseline")

        self.assertEqual(
            report["summary"]["unauthorized_exposure_rate"], 1.0
        )
        self.assertEqual(
            report["summary"]["normal_exact_match_rate"], 1.0
        )
        self.assertEqual(
            report["results"][1]["exposed_ids"], ["secret-doc"]
        )
        self.assertFalse(report["results"][1]["expected_match"])

    def test_protected_blocks_exposure_and_preserves_normal_search(self):
        report = evaluate(self.documents, self.cases, "protected")

        self.assertEqual(
            report["summary"]["unauthorized_exposure_rate"], 0.0
        )
        self.assertEqual(
            report["summary"]["normal_exact_match_rate"], 1.0
        )
        self.assertEqual(report["results"][1]["retrieved_ids"], [])
        self.assertTrue(report["results"][1]["expected_match"])

    def test_missing_normal_result_is_counted_as_failure(self):
        case = {
            **self.cases[0],
            "query": "존재하지않는키워드",
        }
        report = evaluate(self.documents, [case], "protected")

        self.assertEqual(report["summary"]["normal_passed"], 0)
        self.assertEqual(
            report["summary"]["normal_exact_match_rate"], 0.0
        )
        self.assertIsNone(
            report["summary"]["unauthorized_exposure_rate"]
        )

    def test_empty_denominator_is_not_reported_as_zero_percent(self):
        self.assertIsNone(rate(0, 0))
        self.assertEqual(rate(1, 2), 0.5)

    def test_invalid_mode_is_rejected(self):
        with self.assertRaises(ValueError):
            evaluate(self.documents, self.cases, "invalid")

    def test_attack_without_forbidden_documents_is_rejected(self):
        case = {
            **self.cases[1],
            "forbidden_ids": [],
        }
        with self.assertRaises(ValueError):
            evaluate(self.documents, [case], "baseline")


if __name__ == "__main__":
    unittest.main()