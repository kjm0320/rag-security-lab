"""실습용 키워드 검색 모듈. 현재 버전에는 접근 권한 검사가 없다."""

import argparse
import json
import re
from pathlib import Path


def tokenize(text: str) -> set[str]:
    return set(re.findall(r"[가-힣a-z0-9]+", text.lower()))


def load_documents(path: Path) -> list[dict]:
    with path.open(encoding="utf-8-sig") as file:
        return json.load(file)


def search(
    query: str,
    documents: list[dict],
    top_k: int = 3,
) -> list[dict]:
    if top_k < 1:
        raise ValueError("top_k는 1 이상이어야 합니다.")

    query_tokens = tokenize(query)
    results = []

    for document in documents:
        content = f"{document['title']} {document['text']}"
        score = len(query_tokens & tokenize(content))

        if score > 0:
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
    parser = argparse.ArgumentParser(description="실습 문서 키워드 검색")
    parser.add_argument("query", help="검색할 질문 또는 키워드")
    parser.add_argument(
        "--documents",
        type=Path,
        default=Path("datasets/documents.json"),
    )
    parser.add_argument("--top-k", type=int, default=3)
    args = parser.parse_args()

    if args.top_k < 1:
        parser.error("--top-k는 1 이상이어야 합니다.")

    documents = load_documents(args.documents)
    results = search(args.query, documents, args.top_k)

    if not results:
        print("검색 결과가 없습니다.")
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