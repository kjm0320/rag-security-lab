"""검색 단계의 방어 전후 비교. LLM 응답 평가는 포함하지 않는다."""

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from rag_security_lab.gateway import secure_search
from rag_security_lab.retrieval import load_documents, search


def rate(count: int, total: int) -> float | None:
    return round(count / total, 4) if total else None


def evaluate(
    documents: list[dict],
    cases: list[dict],
    mode: str,
) -> dict:
    if mode not in {"baseline", "protected"}:
        raise ValueError(f"지원하지 않는 모드: {mode}")

    results = []

    for case in cases:
        if case["kind"] not in {"attack", "normal"}:
            raise ValueError(f"잘못된 테스트 유형: {case['id']}")

        if case["kind"] == "attack" and not case["forbidden_ids"]:
            raise ValueError(f"금지 문서가 없는 공격 테스트: {case['id']}")

        if mode == "baseline":
            hits = search(case["query"], documents, top_k=3)
        else:
            hits = secure_search(
                case["query"],
                documents,
                role=case["role"],
                top_k=3,
            )

        retrieved_ids = [
            hit["document"]["id"] for hit in hits
        ]
        exposed_ids = sorted(
            set(retrieved_ids) & set(case["forbidden_ids"])
        )
        expected_match = (
            set(retrieved_ids) == set(case["expected_ids"])
        )

        results.append({
            "case_id": case["id"],
            "kind": case["kind"],
            "query": case["query"],
            "role": case["role"],
            "expected_ids": case["expected_ids"],
            "forbidden_ids": case["forbidden_ids"],
            "retrieved_ids": retrieved_ids,
            "exposed_ids": exposed_ids,
            "expected_match": expected_match,
            "unauthorized_exposure": bool(exposed_ids),
        })

    attacks = [r for r in results if r["kind"] == "attack"]
    normal = [r for r in results if r["kind"] == "normal"]

    exposed_count = sum(r["unauthorized_exposure"] for r in attacks)
    normal_passed = sum(r["expected_match"] for r in normal)

    return {
        "summary": {
            "attack_cases": len(attacks),
            "exposed_attack_cases": exposed_count,
            "unauthorized_exposure_rate": rate(exposed_count, len(attacks)),
            "normal_cases": len(normal),
            "normal_passed": normal_passed,
            "normal_exact_match_rate": rate(normal_passed, len(normal)),
        },
        "results": results,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="검색 보안 비교 평가")
    parser.add_argument(
        "--documents",
        type=Path,
        default=Path("datasets/documents.json"),
    )
    parser.add_argument(
        "--cases",
        type=Path,
        default=Path("datasets/retrieval_cases.json"),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("reports/retrieval_comparison.json"),
    )
    args = parser.parse_args()

    documents = load_documents(args.documents)
    with args.cases.open(encoding="utf-8-sig") as file:
        cases = json.load(file)

    if not cases:
        raise ValueError("테스트셋이 비어 있습니다.")

    modes = {
        mode: evaluate(documents, cases, mode)
        for mode in ("baseline", "protected")
    }

    report = {
        "schema_version": 1,
        "scope": "retrieval_access_control",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "settings": {
            "retriever": "token_overlap",
            "top_k": 3,
        },
        "inputs": {
            "documents_path": str(args.documents),
            "cases_path": str(args.cases),
            "documents": documents,
            "cases": cases,
        },
        "modes": modes,
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    for mode, result in modes.items():
        summary = result["summary"]
        print(f"[{mode}]")
        print(
            "  비인가 문서 노출: "
            f"{summary['exposed_attack_cases']}/{summary['attack_cases']}"
        )
        print(
            "  정상 검색 통과: "
            f"{summary['normal_passed']}/{summary['normal_cases']}"
        )

    print(f"\n보고서 저장: {args.output}")


if __name__ == "__main__":
    main()