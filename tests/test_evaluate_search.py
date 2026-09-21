import unittest

from rag_security_lab.evaluate_search import evaluate_cases


def hit(document_id):
    return {
        "document": {"id": document_id},
        "score": 0.7,
    }


class EvaluateSearchTests(unittest.TestCase):
    def make_case(self, expected_ids):
        return {
            "id": "test-case",
            "query": "테스트 질문",
            "role": "user",
            "expected_ids": expected_ids,
        }

    def test_expected_top1_is_counted_as_hit(self):
        report = evaluate_cases(
            [self.make_case(["doc-001"])],
            lambda case: [hit("doc-001")],
        )

        self.assertEqual(report["summary"]["answerable_cases"], 1)
        self.assertEqual(report["summary"]["top1_hits"], 1)
        self.assertTrue(report["results"][0]["passed"])

    def test_correct_document_below_top1_is_not_a_hit(self):
        report = evaluate_cases(
            [self.make_case(["doc-001"])],
            lambda case: [hit("doc-002"), hit("doc-001")],
        )

        self.assertEqual(report["summary"]["top1_hits"], 0)
        self.assertFalse(report["results"][0]["passed"])

    def test_missing_answerable_result_is_failure(self):
        report = evaluate_cases(
            [self.make_case(["doc-001"])],
            lambda case: [],
        )

        self.assertEqual(report["summary"]["top1_hits"], 0)
        self.assertFalse(report["results"][0]["passed"])

    def test_empty_result_for_unanswerable_question_is_correct(self):
        report = evaluate_cases(
            [self.make_case([])],
            lambda case: [],
        )

        self.assertEqual(report["summary"]["unanswerable_cases"], 1)
        self.assertEqual(report["summary"]["correct_empty_results"], 1)
        self.assertTrue(report["results"][0]["passed"])

    def test_irrelevant_result_for_unanswerable_question_is_failure(self):
        report = evaluate_cases(
            [self.make_case([])],
            lambda case: [hit("doc-002")],
        )

        self.assertEqual(report["summary"]["correct_empty_results"], 0)
        self.assertFalse(report["results"][0]["passed"])


if __name__ == "__main__":
    unittest.main()