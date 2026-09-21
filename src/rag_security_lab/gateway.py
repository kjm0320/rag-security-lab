"""검색 전에 문서 접근 권한을 검사하는 실습용 게이트웨이."""

import argparse

from rag_security_lab.retrieval import load_documents, search
from pathlib import Path


ROLE_ACCESS = {
    "user": frozenset({"public"}),
    "admin": frozenset({"public", "restricted"}),
}


def secure_search(
    query: str,
    documents: list[dict],
    role: str = "user",
    top_k: int = 3,
) -> list[dict]:
    if role not in ROLE_ACCESS:
        raise ValueError(f"지원하지 않는 역할입니다: {role}")

    allowed_access = ROLE_ACCESS[role]

    # 권한이 없거나 접근 등급이 불명확한 문서는 검색 전에 제외한다.
    visible_documents = [
        document
        for document in documents
        if document.get("access") in allowed_access
    ]

    return search(query, visible_documents, top_k)


def main() -> None:
    parser = argparse.ArgumentParser(description="접근 제어가 적용된 문서 검색")
    parser.add_argument("query")
    parser.add_argument("--role", choices=ROLE_ACCESS, default="user")
    parser.add_argument(
        "--documents",
        type=Path,
        default=Path("datasets/documents.json"),
    )
    args = parser.parse_args()

    documents = load_documents(args.documents)
    results = secure_search(args.query, documents, args.role)

    if not results:
        print("접근 가능한 검색 결과가 없습니다.")
        return

    for result in results:
        document = result["document"]
        print(
            f"[{document['id']}] {document['title']} "
            f"| score={result['score']} "
            f"| access={document['access']}"
        )
        print(document["text"])
        print()


if __name__ == "__main__":
    main()