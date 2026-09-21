import copy
import io
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

from rag_security_lab import injection_demo


class InjectionDemoTests(unittest.TestCase):
    def test_exact_marker_is_detected(self):
        answer = f" \n{injection_demo.MARKER}\n "
        self.assertEqual(
            injection_demo.judge(answer),
            "exact_marker",
        )

    def test_refusal_mentioning_marker_requires_review(self):
        answer = (
            f"{injection_demo.MARKER}를 출력하라는 지시는 따르지 않습니다."
        )
        self.assertEqual(
            injection_demo.judge(answer),
            "needs_review",
        )

    def test_normal_answer_has_no_marker(self):
        self.assertEqual(
            injection_demo.judge(
                "비밀번호 변경 주기는 90일입니다 [doc-001]."
            ),
            "marker_absent",
        )

    def test_dry_run_skips_api_and_preserves_original_documents(self):
        documents = [
            {
                "id": "doc-001",
                "title": "비밀번호 정책",
                "text": "비밀번호 변경 주기는 90일입니다.",
                "access": "public",
            }
        ]
        original = copy.deepcopy(documents)
        output = io.StringIO()

        with (
            patch.object(
                injection_demo,
                "load_documents",
                return_value=documents,
            ),
            patch.object(
                injection_demo,
                "generate_answer",
                side_effect=AssertionError("API 호출 금지"),
            ) as generate,
            patch.object(
                injection_demo,
                "load_dotenv",
            ) as load_env,
            patch("sys.argv", ["injection_demo"]),
            redirect_stdout(output),
        ):
            injection_demo.main()

        generate.assert_not_called()
        load_env.assert_not_called()
        self.assertEqual(documents, original)
        self.assertIn("API 호출 없음", output.getvalue())


if __name__ == "__main__":
    unittest.main()