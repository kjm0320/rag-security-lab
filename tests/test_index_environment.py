import json
import sqlite3
import tempfile
import unittest
from contextlib import closing
from pathlib import Path
from unittest.mock import patch

from rag_security_lab.embeddings import DIMENSION
from rag_security_lab.vector_store import build_index, vector_search


class FakeEmbedder:
    def __init__(self):
        self.calls = 0
        self.vector = [1.0] + [0.0] * (DIMENSION - 1)

    def encode(self, texts):
        self.calls += 1
        return [list(self.vector) for _ in texts]


class IndexEnvironmentTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.db = Path(temp.name) / "test.sqlite3"
        self.db.touch()
        self.embedder = FakeEmbedder()
        documents = [{
            "id": "doc-001",
            "title": "Test document",
            "text": "Test content",
            "access": "public",
        }]
        mocked = patch(
            "rag_security_lab.vector_store.get_documents",
            return_value=documents,
        )
        mocked.start()
        self.addCleanup(mocked.stop)
        build_index(self.db, self.embedder)
        self.embedder.calls = 0

    def snapshot(self):
        with closing(sqlite3.connect(self.db)) as connection:
            vectors = connection.execute(
                "SELECT * FROM document_vectors ORDER BY document_id"
            ).fetchall()
            metadata = connection.execute(
                "SELECT * FROM vector_index_metadata"
            ).fetchall()
        return vectors, metadata

    def test_same_environment_can_search(self):
        hits = vector_search(self.db, "query", self.embedder)
        self.assertEqual(hits[0]["document"]["id"], "doc-001")
        self.assertAlmostEqual(hits[0]["score"], 1.0)

    def test_changed_version_is_rejected_before_query_embedding(self):
        with patch(
            "rag_security_lab.vector_store.version",
            return_value="changed-version",
        ):
            with self.assertRaisesRegex(ValueError, "현재 환경"):
                vector_search(self.db, "query", self.embedder)
        self.assertEqual(self.embedder.calls, 0)

    def test_legacy_index_requires_rebuild(self):
        with closing(sqlite3.connect(self.db)) as connection:
            with connection:
                connection.execute("DROP TABLE vector_index_metadata")
        with self.assertRaisesRegex(ValueError, "환경 기록이 없습니다"):
            vector_search(self.db, "query", self.embedder)
        self.assertEqual(self.embedder.calls, 0)

    def test_rebuild_records_new_environment(self):
        with patch(
            "rag_security_lab.vector_store.version",
            return_value="new-version",
        ):
            build_index(self.db, self.embedder)
            hits = vector_search(self.db, "query", self.embedder)
        self.assertEqual(len(hits), 1)
        signature = json.loads(self.snapshot()[1][0][1])
        self.assertEqual(
            signature["package_versions"]["fastembed"], "new-version"
        )

    def test_invalid_vectors_preserve_index_and_metadata(self):
        before = self.snapshot()
        self.embedder.vector = [1.0, 0.0]
        with self.assertRaisesRegex(ValueError, "벡터 차원"):
            build_index(self.db, self.embedder)
        self.assertEqual(self.snapshot(), before)

    def test_metadata_write_failure_rolls_back_vector_replacement(self):
        before = self.snapshot()
        with closing(sqlite3.connect(self.db)) as connection:
            with connection:
                connection.execute("""
                    CREATE TRIGGER reject_metadata
                    BEFORE INSERT ON vector_index_metadata
                    BEGIN
                        SELECT RAISE(ABORT, 'simulated write failure');
                    END
                """)
        self.embedder.vector = [0.0, 1.0] + [0.0] * (DIMENSION - 2)
        with self.assertRaises(sqlite3.IntegrityError):
            build_index(self.db, self.embedder)
        self.assertEqual(self.snapshot(), before)


if __name__ == "__main__":
    unittest.main()
