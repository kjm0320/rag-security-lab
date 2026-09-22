import json
import tempfile
import unittest
from pathlib import Path

from rag_security_lab.summary_report import read_section


class SummaryVectorInjectionTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.directory = Path(temporary.name)

        self.report = {
            "scope": "vector_indirect_prompt_injection",
            "model": "test-model",
            "attack": {"id": "test-attack"},
            "embedding_model": "test-embedding",
            "embedding_versions": {
                "fastembed": "test-version",
                "onnxruntime": "test-version",
            },
            "settings": {"top_k": 1, "min_score": 0.3},
            "complete": True,
            "generated_cases": 1,
            "planned_cases": [
                {
                    "case_id": "basic/injected",
                    "retrieved_ids": ["doc-001"],
                    "scores": [0.6],
                    "attack_delivered": True,
                    "prompt": "PRIVATE_PROMPT_FOR_TEST",
                    "system_instruction": "PRIVATE_SYSTEM_FOR_TEST",
                }
            ],
            "results": [
                {
                    "case_id": "basic/injected",
                    "status": "completed",
                    "attack_delivered": True,
                    "answer": "RAW_ANSWER_FOR_TEST",
                    "marker_verdict": "marker_absent",
                }
            ],
        }

    def read_report(self):
        path = self.directory / "vector.json"
        path.write_text(
            json.dumps(self.report),
            encoding="utf-8",
        )
        return read_section(
            self.directory,
            "벡터 인젝션",
            "vector.json",
            "vector_indirect_prompt_injection",
        )

    def test_delivery_and_verdict_are_preserved_without_raw_content(self):
        section = self.read_report()

        self.assertEqual(section["state"], "loaded")
        row = section["observations"]["cases"][0]
        self.assertTrue(row["attack_delivered"])
        self.assertEqual(row["marker_verdict"], "marker_absent")
        self.assertEqual(row["scores"], [0.6])

        serialized = json.dumps(section)
        self.assertNotIn("PRIVATE_PROMPT_FOR_TEST", serialized)
        self.assertNotIn("PRIVATE_SYSTEM_FOR_TEST", serialized)
        self.assertNotIn("RAW_ANSWER_FOR_TEST", serialized)

    def test_skipped_generation_has_no_marker_verdict(self):
        self.report["planned_cases"][0].update(
            retrieved_ids=[],
            scores=[],
            attack_delivered=False,
        )
        self.report["results"] = [
            {
                "case_id": "basic/injected",
                "status": "skipped_no_context",
                "attack_delivered": False,
            }
        ]
        self.report["generated_cases"] = 0

        section = self.read_report()

        self.assertEqual(section["state"], "loaded")
        row = section["observations"]["cases"][0]
        self.assertEqual(row["status"], "skipped_no_context")
        self.assertFalse(row["attack_delivered"])
        self.assertNotIn("marker_verdict", row)

    def test_api_error_and_unrun_condition_are_distinguished(self):
        self.report["planned_cases"].append({
            "case_id": "guarded/injected",
            "retrieved_ids": ["doc-001"],
            "scores": [0.6],
            "attack_delivered": True,
        })
        self.report["results"] = [
            {
                "case_id": "basic/injected",
                "status": "api_error",
                "attack_delivered": True,
                "http_code": 429,
            }
        ]
        self.report["complete"] = False
        self.report["generated_cases"] = 0

        section = self.read_report()

        self.assertEqual(section["state"], "loaded")
        observations = section["observations"]
        self.assertFalse(observations["reported_complete"])
        rows = observations["cases"]
        self.assertEqual(rows[0]["status"], "api_error")
        self.assertEqual(rows[0]["http_code"], 429)
        self.assertEqual(rows[1]["status"], "not_run")
        for row in rows:
            self.assertNotIn("marker_verdict", row)

    def test_inconsistent_delivery_is_rejected(self):
        self.report["results"][0]["attack_delivered"] = False

        section = self.read_report()

        self.assertEqual(section["state"], "unreadable")


if __name__ == "__main__":
    unittest.main()