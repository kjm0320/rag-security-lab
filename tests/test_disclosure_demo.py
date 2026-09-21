import unittest

from rag_security_lab.disclosure_demo import SECRET, compare_output


class DisclosureDemoTests(unittest.TestCase):
    def test_secret_is_removed_but_useful_content_remains(self):
        answer = (
            f"보안팀 승인 후 진행합니다. "
            f"복구 코드는 {SECRET}입니다 [doc-003]."
        )

        result = compare_output(answer)

        self.assertEqual(result["raw_answer"], answer)
        self.assertTrue(result["raw_contains_exact_secret"])
        self.assertFalse(result["filtered_contains_exact_secret"])
        self.assertTrue(result["redacted"])
        self.assertEqual(result["matched_secret_count"], 1)
        self.assertIn("보안팀 승인", result["filtered_answer"])
        self.assertIn("[doc-003]", result["filtered_answer"])
        self.assertIn("[REDACTED]", result["filtered_answer"])

    def test_answer_without_secret_is_preserved(self):
        answer = "관리자 복구 절차는 보안팀 승인 후 진행합니다 [doc-003]."

        result = compare_output(answer)

        self.assertEqual(result["filtered_answer"], answer)
        self.assertFalse(result["raw_contains_exact_secret"])
        self.assertFalse(result["redacted"])

    def test_repeated_secret_is_removed_everywhere(self):
        result = compare_output(f"{SECRET} / {SECRET}")

        self.assertEqual(
            result["filtered_answer"],
            "[REDACTED] / [REDACTED]",
        )
        self.assertFalse(result["filtered_contains_exact_secret"])
        self.assertEqual(result["matched_secret_count"], 1)


if __name__ == "__main__":
    unittest.main()