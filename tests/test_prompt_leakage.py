import json
import unittest

from rag_security_lab.prompt_leakage_demo import (
    CANARY,
    assess_answer,
    make_cases,
)
from rag_security_lab.rag import SYSTEM_INSTRUCTION


class PromptLeakageTests(unittest.TestCase):
    def setUp(self):
        self.documents = [
            {
                "id": "doc-001",
                "title": "비밀번호 정책",
                "text": "비밀번호 변경 주기는 90일입니다.",
                "access": "public",
            }
        ]

    def test_canary_is_only_in_system_instruction(self):
        cases = make_cases(self.documents)

        self.assertEqual(
            [case["case_id"] for case in cases],
            ["clean", "extraction_request"],
        )
        for case in cases:
            with self.subTest(case=case["case_id"]):
                self.assertIn(CANARY, case["system_instruction"])
                self.assertNotIn(CANARY, case["prompt"])

    def test_conditions_share_documents_and_system_instruction(self):
        clean, attack = make_cases(self.documents)
        clean_payload = json.loads(clean["prompt"])
        attack_payload = json.loads(attack["prompt"])

        self.assertEqual(
            clean_payload["reference_documents"],
            attack_payload["reference_documents"],
        )
        self.assertEqual(
            clean["system_instruction"],
            attack["system_instruction"],
        )
        self.assertNotEqual(
            clean_payload["question"],
            attack_payload["question"],
        )

    def test_canary_exposure_is_detected(self):
        result = assess_answer(f"내부 표식은 {CANARY}입니다.")

        self.assertTrue(result["exact_canary_exposed"])
        self.assertFalse(result["full_base_instruction_exposed"])

    def test_full_instruction_exposure_is_detected(self):
        result = assess_answer(SYSTEM_INSTRUCTION.strip())

        self.assertTrue(result["full_base_instruction_exposed"])
        self.assertFalse(result["exact_canary_exposed"])

    def test_normal_answer_has_no_detected_exposure(self):
        result = assess_answer(
            "비밀번호 변경 주기는 90일입니다 [doc-001]."
        )

        self.assertFalse(result["exact_canary_exposed"])
        self.assertFalse(result["full_base_instruction_exposed"])

    def test_contaminated_document_is_rejected(self):
        self.documents[0]["text"] += f"\n{CANARY}"

        with self.assertRaises(ValueError):
            make_cases(self.documents)


if __name__ == "__main__":
    unittest.main()