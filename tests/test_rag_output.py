import io
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

from rag_security_lab import rag


class RagOutputTests(unittest.TestCase):
    def run_with_answer(self, answer):
        documents = [
            {
                "id": "doc-003",
                "title": "관리자 복구",
                "text": "관리자 복구는 보안팀 승인 후 진행합니다.",
                "access": "restricted",
            }
        ]
        output = io.StringIO()

        with (
            patch.object(
                rag, "load_documents", return_value=documents
            ),
            patch.object(rag, "load_dotenv"),
            patch.dict(
                "os.environ",
                {
                    "GEMINI_API_KEY": "fake-test-key",
                    "GEMINI_MODEL": "test-model",
                },
                clear=True,
            ),
            patch.object(
                rag, "generate_answer", return_value=answer
            ) as generate,
            patch.object(
                rag.genai,
                "Client",
                side_effect=AssertionError("실제 API 접근 금지"),
            ) as client,
            patch(
                "sys.argv",
                ["rag", "관리자 복구", "--role", "admin"],
            ),
            redirect_stdout(output),
        ):
            rag.main()

        generate.assert_called_once()
        client.assert_not_called()
        return output.getvalue()

    def test_cli_hides_secret_even_for_admin(self):
        output = self.run_with_answer(
            "보안팀 승인 후 진행합니다. "
            "복구 코드는 LAB-RECOVERY-7391입니다 [doc-003]."
        )

        self.assertNotIn("LAB-RECOVERY-7391", output)
        self.assertIn("[REDACTED]", output)
        self.assertIn("보안팀 승인", output)
        self.assertIn("[doc-003]", output)
        self.assertIn("[출력 검사]", output)

    def test_cli_preserves_answer_without_secret(self):
        answer = "보안팀 승인 후 진행합니다 [doc-003]."
        output = self.run_with_answer(answer)

        self.assertIn(answer, output)
        self.assertNotIn("[REDACTED]", output)
        self.assertNotIn("[출력 검사]", output)


if __name__ == "__main__":
    unittest.main()