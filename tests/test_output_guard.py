import unittest

from rag_security_lab.output_guard import redact_secrets


class OutputGuardTests(unittest.TestCase):
    def test_secret_is_redacted(self):
        result = redact_secrets(
            "복구 코드: LAB-RECOVERY-7391",
            ["LAB-RECOVERY-7391"],
        )

        self.assertEqual(result.text, "복구 코드: [REDACTED]")
        self.assertTrue(result.redacted)
        self.assertEqual(result.matched_secret_count, 1)

    def test_normal_answer_is_preserved(self):
        answer = "비밀번호 변경 주기는 90일입니다 [doc-001]."
        result = redact_secrets(answer, ["LAB-RECOVERY-7391"])

        self.assertEqual(result.text, answer)
        self.assertFalse(result.redacted)
        self.assertEqual(result.matched_secret_count, 0)

    def test_repeated_secret_is_redacted_everywhere(self):
        result = redact_secrets(
            "CODE-123 / CODE-123",
            ["CODE-123", "CODE-123"],
        )

        self.assertEqual(result.text, "[REDACTED] / [REDACTED]")
        self.assertEqual(result.matched_secret_count, 1)

    def test_overlapping_secrets_leave_no_fragment(self):
        result = redact_secrets(
            "ABCDE",
            ["ABC", "CDE"],
        )

        self.assertEqual(result.text, "[REDACTED]")
        self.assertEqual(result.matched_secret_count, 2)

    def test_empty_secret_is_rejected(self):
        for secret in ("", "   "):
            with self.subTest(secret=secret):
                with self.assertRaises(ValueError):
                    redact_secrets("일반 답변", [secret])

    def test_unconfigured_variant_is_not_detected(self):
        # 현재 구현의 한계를 명시적으로 검증한다.
        answer = "lab-recovery-7391"
        result = redact_secrets(answer, ["LAB-RECOVERY-7391"])

        self.assertEqual(result.text, answer)
        self.assertFalse(result.redacted)


if __name__ == "__main__":
    unittest.main()