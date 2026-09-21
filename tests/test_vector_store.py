import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock

from rag_security_lab.document_store import replace_documents
from rag_security_lab.embeddings import DIMENSION
from rag_security_lab.vector_store import build_index, vector_search


class FakeEmbedder:
    """순위와 접근 제어 검증을 위한 고정 벡터."""

    def encode(self, texts):
        known = {
            "공개 안내\n공개 본문": [0.0, 1.0],
            "관리자 복구\n제한 본문": [1.0, 0.0],
            "복구": [1.0, 0.0],
        }
        return [
            known[text] + [0.0] * (DIMENSION - 2)
            for text in texts
        ]


class VectorStoreTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.db = Path(temporary.name) / "test.sqlite3"
        self.embedder = FakeEmbedder()

        self.documents = [
            {
                "id": "public-doc",
                "title": "공개 안내",
                "text": "공개 본문",
                "access": "public",
            },
            {
                "id": "restricted-doc",
                "title": "관리자 복구",
                "text": "제한 본문",
                "access": "restricted",
            },
        ]
        replace_documents(self.db, self.documents)
        build_index(self.db, self.embedder)

    def test_admin_receives_highest_similarity_first(self):
        results = vector_search(
            self.db, "복구", self.embedder, role="admin"
        )

        self.assertEqual(
            [result["document"]["id"] for result in results],
            ["restricted-doc", "public-doc"],
        )
        self.assertAlmostEqual(results[0]["score"], 1.0)
        self.assertAlmostEqual(results[1]["score"], 0.0)

    def test_access_filter_is_applied_before_top_k(self):
        results = vector_search(
            self.db,
            "복구",
            self.embedder,
            role="user",
            top_k=1,
        )

        self.assertEqual(
            [result["document"]["id"] for result in results],
            ["public-doc"],
        )

    def test_threshold_can_return_no_results(self):
        results = vector_search(
            self.db,
            "복구",
            self.embedder,
            role="user",
            min_score=0.5,
        )

        self.assertEqual(results, [])

    def test_changed_document_rejects_stale_vector(self):
        self.documents[0]["text"] = "변경된 공개 본문"
        replace_documents(self.db, self.documents)

        with self.assertRaisesRegex(ValueError, "문서가 변경"):
            vector_search(
                self.db, "복구", self.embedder, role="user"
            )

    def test_wrong_model_is_rejected(self):
        connection = sqlite3.connect(self.db)
        try:
            with connection:
                connection.execute(
                    "UPDATE document_vectors SET model_name = ?",
                    ("different-model",),
                )
        finally:
            connection.close()

        with self.assertRaisesRegex(ValueError, "인덱스 모델"):
            vector_search(
                self.db, "복구", self.embedder, role="user"
            )

    def test_invalid_rebuild_preserves_existing_index(self):
        invalid_embedder = Mock()
        invalid_embedder.encode.return_value = [
            [1.0, 0.0],
            [0.0, 1.0],
        ]

        with self.assertRaisesRegex(ValueError, "벡터 차원"):
            build_index(self.db, invalid_embedder)

        results = vector_search(
            self.db,
            "복구",
            self.embedder,
            role="admin",
            top_k=1,
        )
        self.assertEqual(
            results[0]["document"]["id"],
            "restricted-doc",
        )

    def test_unknown_role_is_rejected_before_embedding(self):
        embedder = Mock()

        with self.assertRaisesRegex(ValueError, "지원하지 않는 역할"):
            vector_search(
                self.db, "복구", embedder, role="superuser"
            )

        embedder.encode.assert_not_called()


if __name__ == "__main__":
    unittest.main()