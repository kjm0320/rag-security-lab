import copy
import tempfile
import unittest
from pathlib import Path

from rag_security_lab.document_store import (
    get_documents,
    replace_documents,
)


class DocumentStoreTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.db = Path(temporary.name) / "test.sqlite3"

        self.documents = [
            {
                "id": "public-doc",
                "title": "공개 안내",
                "text": "일반 사용자가 볼 수 있습니다.",
                "access": "public",
            },
            {
                "id": "restricted-doc",
                "title": "제한 안내",
                "text": "실습용 제한 문서입니다.",
                "access": "restricted",
            },
        ]
        replace_documents(self.db, self.documents)

    def test_user_only_receives_public_documents(self):
        documents = get_documents(self.db, "user")

        self.assertEqual(
            [document["id"] for document in documents],
            ["public-doc"],
        )

    def test_admin_receives_all_documents_with_content_preserved(self):
        documents = get_documents(self.db, "admin")

        self.assertEqual(documents, self.documents)

    def test_unknown_role_is_rejected(self):
        with self.assertRaises(ValueError):
            get_documents(self.db, "superuser")

    def test_invalid_replacement_preserves_existing_documents(self):
        bad_access = copy.deepcopy(self.documents)
        bad_access[0]["access"] = "unknown"

        duplicate = copy.deepcopy(self.documents)
        duplicate[1]["id"] = duplicate[0]["id"]

        for invalid in ([], bad_access, duplicate):
            with self.subTest(documents=invalid):
                with self.assertRaises(ValueError):
                    replace_documents(self.db, invalid)

                self.assertEqual(
                    get_documents(self.db, "admin"),
                    self.documents,
                )

    def test_reinitialization_removes_stale_documents(self):
        replacement = [self.documents[0]]

        replace_documents(self.db, replacement)

        self.assertEqual(
            get_documents(self.db, "admin"),
            replacement,
        )


if __name__ == "__main__":
    unittest.main()