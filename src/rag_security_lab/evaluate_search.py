"""동일한 DB 문서와 질문으로 키워드·벡터 검색을 비교한다."""

import argparse
import json
import math
from datetime import datetime, timezone
from pathlib import Path

from rag_security_lab.document_store import DEFAULT_DB, get_documents
from rag_security_lab.embeddings import MODEL_NAME, LocalEmbedder
from rag_security_lab.gateway import secure_search
from rag_security_lab.vector_store import fingerprint, vector_search


def evaluate_cases(cases: list[dict], searcher) -> dict:
    results = []

    for case in cases:
        hits = searcher(case)
        retrieved_ids = [
            hit["document"]["id"] for hit in hits
        ]
        expected_ids = case["expected_ids"]
        answerable = bool(expected_ids)

        if answerable:
            passed = bool(
                retrieved_ids and retrieved_ids[0] in expected_ids
            )
        else:
            passed = not retrieved_ids

        results.append({
            "case_id": case["id"],
            "query": case["query"],
            "role": case["role"],
            "answerable": answerable,
            "expected_ids": expected_ids,
            "retrieved_ids": retrieved_ids,
            "scores": [hit["score"] for hit in hits],
            "passed": passed,
        })

    answerable = [row for row in results if row["answerable"]]
    unanswerable = [row for row in results if not row["answerable"]]

    return {
        "summary": {
            "answerable_cases": len(answerable),
            "top1_hits": sum(row["passed"] for row in answerable),
            "unanswerable_cases": len(unanswerable),
            "correct_empty_results": sum(
                row["passed"] for row in unanswerable
            ),
        },
        "results": results,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="검색 품질 비교")
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument(
        "--cases",
        type=Path,
        default=Path("datasets/search_quality_cases.json"),
    )
    parser.add_argument("--min-score", type=float, default=0.0)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("reports/search_quality.json"),
    )
    args = parser.parse_args()

    if not math.isfinite(args.min_score) or not -1 <= args.min_score <= 1:
        parser.error("--min-score는 -1부터 1 사이여야 합니다.")

    with args.cases.open(encoding="utf-8-sig") as file:
        cases = json.load(file)

    if not cases:
        parser.error("평가 질문이 없습니다.")

    documents = get_documents(args.db, role="admin")
    known_ids = {document["id"] for document in documents}

    if len({case["id"] for case in cases}) != len(cases):
        parser.error("평가 질문 ID가 중복됐습니다.")

    for case in cases:
        if not set(case["expected_ids"]).issubset(known_ids):
            parser.error(f"존재하지 않는 기대 문서: {case['id']}")

    keyword = evaluate_cases(
        cases,
        lambda case: secure_search(
            case["query"],
            documents,
            role=case["role"],
            top_k=1,
        ),
    )

    embedder = LocalEmbedder()
    vector = evaluate_cases(
        cases,
        lambda case: vector_search(
            args.db,
            case["query"],
            embedder,
            role=case["role"],
            top_k=1,
            min_score=args.min_score,
        ),
    )

    # 평가 도중 문서가 바뀌었다면 비교 결과를 저장하지 않는다.
    before = {doc["id"]: fingerprint(doc) for doc in documents}
    after = {
        doc["id"]: fingerprint(doc)
        for doc in get_documents(args.db, role="admin")
    }
    if before != after:
        raise SystemExit("평가 도중 DB 문서가 변경됐습니다. 다시 실행하세요.")

    report = {
        "scope": "exploratory_search_quality",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "embedding_model": MODEL_NAME,
        "settings": {
            "top_k": 1,
            "vector_min_score": args.min_score,
        },
        "document_fingerprints": before,
        "cases": cases,
        "methods": {
            "keyword": keyword,
            "vector": vector,
        },
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    for name, evaluation in report["methods"].items():
        summary = evaluation["summary"]
        print(f"\n[{name}]")
        print(
            "정답 문서 1순위 검색: "
            f"{summary['top1_hits']}/{summary['answerable_cases']}"
        )
        print(
            "근거 없는 질문에서 빈 결과: "
            f"{summary['correct_empty_results']}/"
            f"{summary['unanswerable_cases']}"
        )

        for result in evaluation["results"]:
            state = "PASS" if result["passed"] else "FAIL"
            print(
                f"  {state} | {result['case_id']} "
                f"| 검색={result['retrieved_ids']}"
            )

    print(f"\n보고서 저장: {args.output}")


if __name__ == "__main__":
    main()