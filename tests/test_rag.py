import io
import json
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

from rag_security_lab import rag


class RagTests(unittest.TestCase):
    def setUp(self):
        self.documents = [
            {
                "id": "public-doc",
                "title": "복구 안내",
                "text": "복구 요청은 지원팀에 문의합니다.",
                "access": "public",
            },
            {
                "id": "secret-doc",
                "title": "관리자 복구",
                "text": "실습용 비밀값: LAB-SECRET-1234",
                "access": "restricted",
            },
        ]

        # 테스트에서는 실제 파일과 .env를 읽지 않는다.
        documents_patch = patch.object(
            rag, "load_documents", return_value=self.documents
        )
        dotenv_patch = patch.object(rag, "load_dotenv")
        environment_patch = patch.dict(
            "os.environ",
            {
                "GEMINI_API_KEY": "fake-test-key",
                "GEMINI_MODEL": "test-model",
            },
            clear=True,
        )

        # 답변 생성 함수를 대체하고 실제 SDK 접근도 차단한다.
        generator_patch = patch.object(
            rag,
            "generate_answer",
            return_value="지원팀에 문의하세요 [public-doc]",
        )
        client_patch = patch.object(
            rag.genai,
            "Client",
            side_effect=AssertionError("실제 API 접근 금지"),
        )

        for patcher in (
            documents_patch,
            dotenv_patch,
            environment_patch,
            generator_patch,
            client_patch,
        ):
            self.addCleanup(patcher.stop)

        documents_patch.start()
        dotenv_patch.start()
        environment_patch.start()
        self.generate = generator_patch.start()
        self.client = client_patch.start()

    def run_cli(self, query, role="user"):
        output = io.StringIO()
        with patch(
            "sys.argv",
            ["rag", query, "--role", role],
        ), redirect_stdout(output):
            rag.main()
        return output.getvalue()

    def test_no_accessible_documents_skips_generation(self):
        output = self.run_cli("관리자")

        self.generate.assert_not_called()
        self.client.assert_not_called()
        self.assertIn("[API 호출 없음]", output)

    def test_user_prompt_contains_only_public_documents(self):
        output = self.run_cli("복구")

        self.generate.assert_called_once()
        prompt, api_key, model = self.generate.call_args.args
        payload = json.loads(prompt)

        self.assertEqual(
            [doc["id"] for doc in payload["reference_documents"]],
            ["public-doc"],
        )
        self.assertNotIn("LAB-SECRET-1234", prompt)
        self.assertNotIn("fake-test-key", prompt)
        self.assertEqual(api_key, "fake-test-key")
        self.assertEqual(model, "test-model")
        self.assertIn("지원팀에 문의하세요", output)
        self.client.assert_not_called()

    def test_admin_can_pass_restricted_document(self):
        self.run_cli("관리자", role="admin")

        prompt = self.generate.call_args.args[0]
        payload = json.loads(prompt)

        self.assertEqual(
            [doc["id"] for doc in payload["reference_documents"]],
            ["secret-doc"],
        )
        self.assertIn("LAB-SECRET-1234", prompt)

    def test_missing_key_stops_before_generation(self):
        with patch.dict(
            "os.environ",
            {"GEMINI_MODEL": "test-model"},
            clear=True,
        ):
            with self.assertRaises(SystemExit) as caught:
                self.run_cli("복구")

        self.assertIn("API 키", str(caught.exception))
        self.generate.assert_not_called()

    def test_empty_query_stops_before_generation(self):
        with redirect_stdout(io.StringIO()), patch(
            "sys.stderr", new_callable=io.StringIO
        ):
            with self.assertRaises(SystemExit) as caught:
                self.run_cli("   ")

        self.assertEqual(caught.exception.code, 2)
        self.generate.assert_not_called()


if __name__ == "__main__":
    unittest.main()