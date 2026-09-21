import io
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

from rag_security_lab import rag


class RagVectorTests(unittest.TestCase):
    def setUp(self):
        patchers = {
            "embedder": patch.object(rag, "LocalEmbedder"),
            "search": patch.object(rag, "vector_search", return_value=[]),
            "generate": patch.object(
                rag,
                "generate_answer",
                return_value="비밀번호 변경 주기는 90일입니다 [doc-001].",
            ),
            "load_documents": patch.object(
                rag, "load_documents", return_value=[]
            ),
            "dotenv": patch.object(rag, "load_dotenv"),
            "client": patch.object(
                rag.genai,
                "Client",
                side_effect=AssertionError("실제 API 접근 금지"),
            ),
        }

        for name, patcher in patchers.items():
            self.addCleanup(patcher.stop)
            setattr(self, name, patcher.start())

        environment = patch.dict(
            "os.environ",
            {
                "GEMINI_API_KEY": "fake-test-key",
                "GEMINI_MODEL": "test-model",
            },
            clear=True,
        )
        self.addCleanup(environment.stop)
        environment.start()

    def run_cli(self, *arguments):
        output = io.StringIO()
        with (
            patch("sys.argv", ["rag", *arguments]),
            redirect_stdout(output),
        ):
            rag.main()

        self.client.assert_not_called()
        return output.getvalue()

    def test_empty_vector_result_skips_generation(self):
        output = self.run_cli(
            "근거 없는 질문", "--retriever", "vector"
        )

        self.search.assert_called_once()
        self.generate.assert_not_called()
        self.load_documents.assert_not_called()
        self.assertIn("[API 호출 없음]", output)

    def test_vector_mode_uses_evaluated_settings(self):
        self.search.return_value = [
            {
                "document": {
                    "id": "doc-001",
                    "title": "비밀번호 정책",
                    "text": "비밀번호 변경 주기는 90일입니다.",
                    "access": "public",
                },
                "score": 0.7,
            }
        ]

        output = self.run_cli(
            "암호 변경 간격", "--retriever", "vector"
        )

        self.search.assert_called_once_with(
            rag.DEFAULT_DB,
            "암호 변경 간격",
            self.embedder.return_value,
            role="user",
            top_k=1,
            min_score=0.3,
        )
        self.generate.assert_called_once()
        self.load_documents.assert_not_called()
        self.assertIn("90일", output)

    def test_vector_mode_keeps_output_filter(self):
        self.search.return_value = [
            {
                "document": {
                    "id": "doc-003",
                    "title": "관리자 복구",
                    "text": "실습용 복구 절차",
                    "access": "restricted",
                },
                "score": 0.8,
            }
        ]
        self.generate.return_value = (
            "복구 코드는 LAB-RECOVERY-7391입니다 [doc-003]."
        )

        output = self.run_cli(
            "관리자 복구",
            "--retriever", "vector",
            "--role", "admin",
        )

        self.assertEqual(self.search.call_args.kwargs["role"], "admin")
        self.assertNotIn("LAB-RECOVERY-7391", output)
        self.assertIn("[REDACTED]", output)
        self.assertIn("[doc-003]", output)

    def test_default_keyword_mode_does_not_load_embedding_model(self):
        output = self.run_cli("비밀번호")

        self.load_documents.assert_called_once()
        self.embedder.assert_not_called()
        self.search.assert_not_called()
        self.generate.assert_not_called()
        self.assertIn("[API 호출 없음]", output)


if __name__ == "__main__":
    unittest.main()