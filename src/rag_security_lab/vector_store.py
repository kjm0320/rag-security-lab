"""SQLite에 임베딩을 저장하고 권한 필터 후 코사인 검색한다."""

import argparse
import hashlib
import json
import math
import sqlite3
from contextlib import closing
from pathlib import Path

from rag_security_lab.document_store import DEFAULT_DB, get_documents
from rag_security_lab.embeddings import DIMENSION, MODEL_NAME, LocalEmbedder


def fingerprint(document: dict) -> str:
    content = json.dumps(
        {
            key: document[key]
            for key in ("id", "title", "text", "access")
        },
        ensure_ascii=False,
        sort_keys=True,
    )
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def normalize(vector) -> list[float]:
    values = [float(value) for value in vector]

    if len(values) != DIMENSION:
        raise ValueError("벡터 차원이 맞지 않습니다.")

    if not all(math.isfinite(value) for value in values):
        raise ValueError("벡터에 유효하지 않은 숫자가 있습니다.")

    norm = math.sqrt(sum(value * value for value in values))
    if norm == 0:
        raise ValueError("길이가 0인 벡터입니다.")

    return [value / norm for value in values]


def build_index(db: Path, embedder) -> int:
    # 인덱스 생성은 모든 문서를 처리하는 로컬 관리 작업이다.
    documents = get_documents(db, role="admin")
    if not documents:
        raise ValueError("인덱싱할 문서가 없습니다.")

    texts = [
        f"{document['title']}\n{document['text']}"
        for document in documents
    ]
    vectors = list(embedder.encode(texts))

    if len(vectors) != len(documents):
        raise ValueError("문서와 벡터 개수가 다릅니다.")

    # 검증을 마친 후 기존 인덱스를 교체한다.
    rows = [
        (
            document["id"],
            MODEL_NAME,
            fingerprint(document),
            json.dumps(normalize(vector)),
        )
        for document, vector in zip(documents, vectors)
    ]

    with closing(sqlite3.connect(db)) as connection:
        with connection:
            connection.execute("""
                CREATE TABLE IF NOT EXISTS document_vectors (
                    document_id TEXT PRIMARY KEY,
                    model_name TEXT NOT NULL,
                    content_hash TEXT NOT NULL,
                    vector_json TEXT NOT NULL
                )
            """)
            connection.execute("DELETE FROM document_vectors")
            connection.executemany(
                """
                INSERT INTO document_vectors
                    (document_id, model_name, content_hash, vector_json)
                VALUES (?, ?, ?, ?)
                """,
                rows,
            )

    return len(rows)


def vector_search(
    db: Path,
    query: str,
    embedder,
    role: str = "user",
    top_k: int = 3,
    min_score: float = 0.0,
) -> list[dict]:
    if not query.strip():
        raise ValueError("질문이 비어 있습니다.")
    if top_k < 1:
        raise ValueError("top_k는 1 이상이어야 합니다.")
    if not math.isfinite(min_score) or not -1 <= min_score <= 1:
        raise ValueError("min_score는 -1부터 1 사이여야 합니다.")

    # 현재 DB의 권한 정보로 먼저 후보를 제한한다.
    documents = get_documents(db, role=role)
    if not documents:
        return []

    candidates = []
    uri = db.resolve().as_uri() + "?mode=ro"

    with closing(sqlite3.connect(uri, uri=True)) as connection:
        table = connection.execute(
            """
            SELECT name FROM sqlite_master
            WHERE type = 'table' AND name = 'document_vectors'
            """
        ).fetchone()
        if table is None:
            raise ValueError("벡터 인덱스가 없습니다. build를 실행하세요.")

        for document in documents:
            row = connection.execute(
                """
                SELECT model_name, content_hash, vector_json
                FROM document_vectors
                WHERE document_id = ?
                """,
                (document["id"],),
            ).fetchone()

            if row is None:
                raise ValueError("누락된 벡터가 있습니다. build를 다시 실행하세요.")

            model_name, content_hash, vector_json = row

            if model_name != MODEL_NAME:
                raise ValueError("인덱스 모델이 다릅니다. build를 다시 실행하세요.")

            if content_hash != fingerprint(document):
                raise ValueError("문서가 변경됐습니다. build를 다시 실행하세요.")

            candidates.append(
                (document, normalize(json.loads(vector_json)))
            )

    query_vectors = list(embedder.encode([query]))
    if len(query_vectors) != 1:
        raise ValueError("질문 벡터 개수가 맞지 않습니다.")
    query_vector = normalize(query_vectors[0])

    results = []
    for document, vector in candidates:
        score = sum(
            left * right
            for left, right in zip(query_vector, vector)
        )
        score = max(-1.0, min(1.0, score))

        if score >= min_score:
            results.append({
                "document": document,
                "score": score,
            })

    results.sort(
        key=lambda result: (
            -result["score"],
            result["document"]["id"],
        )
    )
    return results[:top_k]


def main() -> None:
    parser = argparse.ArgumentParser(description="로컬 벡터 인덱스")
    parser.add_argument("action", choices=["build", "search"])
    parser.add_argument("query", nargs="?")
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--role", choices=["user", "admin"], default="user")
    parser.add_argument("--top-k", type=int, default=3)
    parser.add_argument("--min-score", type=float, default=0.0)
    args = parser.parse_args()

    if args.action == "search" and not args.query:
        parser.error("search에는 질문이 필요합니다.")

    # DB와 역할을 먼저 확인한다.
    get_documents(
        args.db,
        role="admin" if args.action == "build" else args.role,
    )
    embedder = LocalEmbedder()

    if args.action == "build":
        count = build_index(args.db, embedder)
        print(f"[인덱스 저장 완료] {count}개 문서")
        print(f"[모델] {MODEL_NAME}")
        print(f"[차원] {DIMENSION}")
        return

    results = vector_search(
        args.db,
        args.query,
        embedder,
        role=args.role,
        top_k=args.top_k,
        min_score=args.min_score,
    )

    print(f"[역할] {args.role}")
    if not results:
        print("조건에 맞는 검색 결과가 없습니다.")
        return

    for result in results:
        document = result["document"]
        print(
            f"[{document['id']}] {document['title']} "
            f"| score={result['score']:.4f} "
            f"| access={document['access']}"
        )
        print(document["text"])
        print()


if __name__ == "__main__":
    main()