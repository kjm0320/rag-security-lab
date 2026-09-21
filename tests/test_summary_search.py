import copy
import json
import tempfile
import unittest
from pathlib import Path

from rag_security_lab.summary_report import (
    SOURCES,
    build_summary,
    read_section,
)


class SummarySearchTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.directory = Path(temporary.name)

        self.report = {
            "scope": "exploratory_search_quality",
            "embedding_model": "test-model",
            "settings": {
                "top_k": 1,
                "vector_min_score": 0.3,
            },
            "document_fingerprints": {
                "doc-001": "test-hash",
            },
            "methods": {
                "keyword": {
                    "summary": {
                        "answerable_cases": 1,
                        "top1_hits": 0,
                        "unanswerable_cases": 0,
                        "correct_empty_results": 0,
                    },
                    "results": [
                        {
                            "case_id": "example",
                            "passed": False,
                            "retrieved_ids": [],
                        }
                    ],
                },
                "vector": {
                    "summary": {
                        "answerable_cases": 1,
                        "top1_hits": 1,
                        "unanswerable_cases": 0,
                        "correct_empty_results": 0,
                    },
                    "results": [
                        {
                            "case_id": "example",
                            "passed": True,
                            "retrieved_ids": ["doc-001"],
                        }
                    ],
                },
            },
        }

    def write_report(self, filename, report):
        (self.directory / filename).write_text(
            json.dumps(report),
            encoding="utf-8",
        )

    def test_search_metrics_and_threshold_are_preserved(self):
        self.write_report("search.json", self.report)

        section = read_section(
            self.directory,
            "검색 품질",
            "search.json",
            "exploratory_search_quality",
        )

        self.assertEqual(section["state"], "loaded")
        observations = section["observations"]

        self.assertEqual(
            observations["settings"]["vector_min_score"],
            0.3,
        )

        for method in ("keyword", "vector"):
            self.assertEqual(
                observations["methods"][method]["summary"],
                self.report["methods"][method]["summary"],
            )
            self.assertEqual(
                observations["methods"][method]["cases"],
                self.report["methods"][method]["results"],
            )

        self.assertEqual(
            observations["document_fingerprints"],
            {"doc-001": "test-hash"},
        )

    def test_missing_search_method_is_unreadable(self):
        report = copy.deepcopy(self.report)
        del report["methods"]["vector"]
        self.write_report("search.json", report)

        section = read_section(
            self.directory,
            "검색 품질",
            "search.json",
            "exploratory_search_quality",
        )

        self.assertEqual(section["state"], "unreadable")

    def test_both_search_reports_are_collected_separately(self):
        search_sources = [
            item
            for item in SOURCES
            if item[2] == "exploratory_search_quality"
        ]
        self.assertEqual(len(search_sources), 2)

        for index, (_, filename, _) in enumerate(search_sources):
            report = copy.deepcopy(self.report)
            report["settings"]["vector_min_score"] = (
                0.0 if index == 0 else 0.3
            )
            self.write_report(filename, report)

        summary = build_summary(self.directory)
        loaded = [
            section
            for section in summary["sections"]
            if section["state"] == "loaded"
        ]

        self.assertEqual(len(loaded), 2)
        self.assertEqual(
            [
                section["observations"]["settings"]["vector_min_score"]
                for section in loaded
            ],
            [0.0, 0.3],
        )
        self.assertIsNone(summary["security_score"])
        self.assertEqual(summary["overall_risk"], "not_assessed")


if __name__ == "__main__":
    unittest.main()