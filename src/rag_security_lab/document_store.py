"""SQLite 문서 저장소와 역할별 조회."""

import argparse
import sqlite3
from contextlib import closing
from pathlib import Path

from rag_security_lab.retrieval import load_documents


DEFAULT_DB = Path(".local/rag.sqlite3")

ROLE_ACCESS = {
    "user": ("public",),
    "admin": ("public", "restricted"),
}


def validate_documents(documents: list[dict]) -> None:
    if not documents:
        raise ValueError("빈 문서 목록으로 DB를 교체할 수 없습니다.")

    seen = set()

    for document in documents:
        for field in ("id", "title", "text", "access"):
            value = document.get(field)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"문서 항목이 잘못되었습니다: {field}")

        if document["access"] not in {"public", "restricted"}:
            raise ValueError("지원하지 않는 문서 접근 등급입니다.")

        if document["id"] in seen:
            raise ValueError(f"중복 문서 ID: {document['id']}")

        seen.add(document["id"])


def replace_documents(path: Path, documents: list[dict]) -> int:
    # 검증 실패 시 기존 문서를 변경하지 않는다.
    validate_documents(documents)
    path.parent.mkdir(parents=True, exist_ok=True)

    with closing(sqlite3.connect(path)) as connection:
        with connection:
            connection.execute("""
                CREATE TABLE IF NOT EXISTS documents (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    text TEXT NOT NULL,
                    access TEXT NOT NULL
                        CHECK (access IN ('public', 'restricted'))
                )
            """)
            connection.execute("""
                CREATE INDEX IF NOT EXISTS idx_documents_access
                ON documents(access)
            """)

            # 이 저장소의 문서 스냅샷을 한 트랜잭션으로 교체한다.
            connection.execute("DELETE FROM documents")
            connection.executemany(
                """
                INSERT INTO documents (id, title, text, access)
                VALUES (?, ?, ?, ?)
                """,
                [
                    (
                        document["id"],
                        document["title"],
                        document["text"],
                        document["access"],
                    )
                    for document in documents
                ],
            )

    return len(documents)


def get_documents(path: Path, role: str = "user") -> list[dict]:
    if role not in ROLE_ACCESS:
        raise ValueError(f"지원하지 않는 역할: {role}")

    if not path.is_file():
        raise FileNotFoundError("문서 DB가 없습니다. init을 먼저 실행하세요.")

    allowed = ROLE_ACCESS[role]
    placeholders = ", ".join("?" for _ in allowed)

    # 조회에서는 읽기 전용 연결을 사용한다.
    uri = path.resolve().as_uri() + "?mode=ro"
    with closing(sqlite3.connect(uri, uri=True)) as connection:
        connection.row_factory = sqlite3.Row
        rows = connection.execute(
            f"""
            SELECT id, title, text, access
            FROM documents
            WHERE access IN ({placeholders})
            ORDER BY id
            """,
            allowed,
        ).fetchall()

    return [dict(row) for row in rows]


def main() -> None:
    parser = argparse.ArgumentParser(description="SQLite 문서 저장소")
    parser.add_argument("action", choices=["init", "list"])
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--role", choices=ROLE_ACCESS, default="user")
    parser.add_argument(
        "--documents",
        type=Path,
        default=Path("datasets/documents.json"),
    )
    args = parser.parse_args()

    if args.action == "init":
        documents = load_documents(args.documents)
        count = replace_documents(args.db, documents)
        print(f"[저장 완료] {count}개 문서")
        print(f"[DB] {args.db}")
        return

    documents = get_documents(args.db, args.role)
    print(f"[역할] {args.role}")
    print(f"[접근 가능한 문서] {len(documents)}개")

    for document in documents:
        print(
            f"{document['id']} | {document['title']} "
            f"| {document['access']}"
        )


if __name__ == "__main__":
    main()