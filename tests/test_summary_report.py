import json
import tempfile
import unittest
from pathlib import Path

from rag_security_lab.summary_report import (
    SOURCES,
    build_summary,
    read_section,
)


class SummaryReportTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.directory = Path(temporary.name)

    def write_report(self, filename, data):
        path = self.directory / filename
        path.write_text(
            json.dumps(data, ensure_ascii=False),
            encoding="utf-8",
        )
        return path

    def read_comparison(self, filename="comparison.json"):
        return read_section(
            self.directory,
            "비교 실험",
            filename,
            "system_instruction_comparison",
        )

    def test_missing_file_is_reported_as_missing(self):
        section = self.read_comparison()

        self.assertEqual(section["state"], "missing")
        self.assertNotIn("observations", section)

    def test_invalid_json_is_reported_as_unreadable(self):
        path = self.directory / "comparison.json"
        path.write_text("{invalid json", encoding="utf-8")

        section = self.read_comparison()

        self.assertEqual(section["state"], "unreadable")
        self.assertNotIn("observations", section)

    def test_wrong_scope_is_rejected(self):
        self.write_report(
            "comparison.json",
            {"scope": "unrelated_experiment"},
        )

        section = self.read_comparison()

        self.assertEqual(section["state"], "unreadable")

    def test_missing_required_results_is_rejected(self):
        self.write_report(
            "comparison.json",
            {"scope": "system_instruction_comparison"},
        )

        section = self.read_comparison()

        self.assertEqual(section["state"], "unreadable")

    def test_incomplete_run_and_api_error_are_preserved(self):
        self.write_report(
            "comparison.json",
            {
                "scope": "system_instruction_comparison",
                "complete": False,
                "completed_cases": 1,
                "results": [
                    {
                        "case_id": "basic/clean",
                        "status": "completed",
                        "marker_verdict": "marker_absent",
                    },
                    {
                        "case_id": "basic/injected",
                        "status": "api_error",
                        "http_code": 429,
                    },
                ],
            },
        )

        section = self.read_comparison()
        observations = section["observations"]

        self.assertEqual(section["state"], "loaded")
        self.assertFalse(observations["reported_complete"])
        self.assertEqual(observations["reported_completed_cases"], 1)

        failed_case = observations["cases"][1]
        self.assertEqual(failed_case["status"], "api_error")
        self.assertEqual(failed_case["http_code"], 429)
        self.assertNotIn("marker_verdict", failed_case)

    def test_answer_and_system_instruction_are_not_copied(self):
        self.write_report(
            "comparison.json",
            {
                "scope": "system_instruction_comparison",
                "complete": True,
                "completed_cases": 1,
                "planned_cases": [
                    {"system_instruction": "SYSTEM_TEXT_FOR_TEST"}
                ],
                "results": [
                    {
                        "case_id": "basic/clean",
                        "status": "completed",
                        "answer": "RAW_ANSWER_FOR_TEST",
                        "marker_verdict": "marker_absent",
                    }
                ],
            },
        )

        section = self.read_comparison()
        serialized = json.dumps(section)

        self.assertEqual(section["state"], "loaded")
        self.assertNotIn("RAW_ANSWER_FOR_TEST", serialized)
        self.assertNotIn("SYSTEM_TEXT_FOR_TEST", serialized)

    def test_collection_counts_do_not_become_security_score(self):
        comparison_file = next(
            filename
            for _, filename, scope in SOURCES
            if scope == "system_instruction_comparison"
        )
        self.write_report(
            comparison_file,
            {
                "scope": "system_instruction_comparison",
                "complete": False,
                "completed_cases": 0,
                "results": [],
            },
        )

        summary = build_summary(self.directory)

        self.assertEqual(
            summary["collection_counts"],
            {
                "loaded": 1,
                "missing": len(SOURCES) - 1,
                "unreadable": 0,
            },
        )
        self.assertIsNone(summary["security_score"])
        self.assertEqual(summary["overall_risk"], "not_assessed")


if __name__ == "__main__":
    unittest.main()