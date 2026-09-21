import json
import unittest
from html.parser import HTMLParser

from rag_security_lab.html_report import render_report


class ReportParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.tags = []
        self.in_pre = False
        self.report_text = []

    def handle_starttag(self, tag, attrs):
        self.tags.append(tag)
        if tag == "pre":
            self.in_pre = True

    def handle_endtag(self, tag):
        if tag == "pre":
            self.in_pre = False

    def handle_data(self, data):
        if self.in_pre:
            self.report_text.append(data)


class HtmlReportTests(unittest.TestCase):
    def test_attack_strings_remain_text(self):
        payloads = [
            "<script>alert('LAB')</script>",
            '<img src=x onerror="alert(1)">',
            "</pre><script>alert(1)</script><pre>",
            '<a href="javascript:alert(1)">클릭</a>',
        ]

        for payload in payloads:
            with self.subTest(payload=payload):
                report = {"answer": payload}
                parser = ReportParser()
                parser.feed(render_report(report))

                self.assertNotIn("script", parser.tags)
                self.assertNotIn("img", parser.tags)
                self.assertNotIn("a", parser.tags)
                self.assertEqual(parser.tags.count("pre"), 1)
                self.assertEqual(
                    json.loads("".join(parser.report_text)),
                    report,
                )

    def test_dictionary_keys_are_also_escaped(self):
        report = {"<script>alert(1)</script>": "실습"}
        parser = ReportParser()
        parser.feed(render_report(report))

        self.assertNotIn("script", parser.tags)
        self.assertEqual(
            json.loads("".join(parser.report_text)),
            report,
        )

    def test_normal_text_is_preserved(self):
        report = {
            "answer": "비밀번호 변경 주기는 90일입니다 [doc-001].",
            "example": 'A & B < C, "인용문"',
        }
        parser = ReportParser()
        parser.feed(render_report(report))

        self.assertEqual(
            json.loads("".join(parser.report_text)),
            report,
        )


if __name__ == "__main__":
    unittest.main()