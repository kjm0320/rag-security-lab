"""임시 DB와 실제 로컬 임베딩을 사용하는 문서 인젝션 비교."""

import argparse
import copy
import json
import os
import tempfile
from datetime import datetime, timezone
from importlib.metadata import version
from pathlib import Path

from dotenv import load_dotenv
from google.genai import errors

from rag_security_lab.compare_injection import (
    BASIC_INSTRUCTION,
    judge,
    load_attack,
)
from rag_security_lab.document_store import replace_documents
from rag_security_lab.embeddings import MODEL_NAME, LocalEmbedder
from rag_security_lab.rag import (
    SYSTEM_INSTRUCTION,
    build_prompt,
    generate_answer,
)
from rag_security_lab.retrieval import load_documents
from rag_security_lab.vector_store import build_index, vector_search


def prepare_cases(documents, attack, embedder):
    if attack["marker"] in json.dumps(documents, ensure_ascii=False):
        raise ValueError("정상 문서에 공격 마커가 이미 있습니다.")

    poisoned = copy.deepcopy(documents)
    targets = [
        doc for doc in poisoned
        if doc["id"] == attack["target_document_id"]
    ]
    if len(targets) != 1:
        raise ValueError("공격 대상 문서는 정확히 1개여야 합니다.")

    targets[0]["text"] += "\n" + attack["payload"]
    retrieved = {}

    with tempfile.TemporaryDirectory(prefix="rag-vector-experiment-") as temp:
        for document_type, collection in (
            ("clean", documents),
            ("injected", poisoned),
        ):
            db = Path(temp) / f"{document_type}.sqlite3"
            replace_documents(db, collection)
            build_index(db, embedder)

            hits = vector_search(
                db,
                attack["question"],
                embedder,
                role="user",
                top_k=1,
                min_score=0.3,
            )

            retrieved[document_type] = {
                "prompt": build_prompt(attack["question"], hits),
                "retrieved_ids": [
                    hit["document"]["id"] for hit in hits
                ],
                "scores": [hit["score"] for hit in hits],
                "attack_delivered": (
                    document_type == "injected"
                    and any(
                        hit["document"]["id"] == attack["target_document_id"]
                        and attack["payload"] in hit["document"]["text"]
                        for hit in hits
                    )
                ),
            }

    cases = []
    for mode, instruction in (
        ("basic", BASIC_INSTRUCTION),
        ("guarded", SYSTEM_INSTRUCTION),
    ):
        for document_type in ("clean", "injected"):
            cases.append({
                "case_id": f"{mode}/{document_type}",
                "system_instruction": instruction,
                **retrieved[document_type],
            })

    return cases


def main():
    parser = argparse.ArgumentParser(
        description="실제 벡터 검색 경로의 인젝션 실험"
    )
    parser.add_argument("--case", default="fake-system-message")
    parser.add_argument("--execute", action="store_true")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("reports/vector_injection.json"),
    )
    args = parser.parse_args()

    attack = load_attack(
        Path("datasets/injection_cases.json"), args.case
    )
    documents = load_documents(Path("datasets/documents.json"))
    cases = prepare_cases(documents, attack, LocalEmbedder())

    print(f"\n[공격] {attack['id']}")
    for case in cases:
        scores = [round(score, 4) for score in case["scores"]]
        print(
            f"[{case['case_id']}] "
            f"문서={case['retrieved_ids']} "
            f"점수={scores} "
            f"공격전달={case['attack_delivered']}"
        )

    if not args.execute:
        print("\n[준비 완료 — Gemini API 호출 없음]")
        return

    load_dotenv(".env", encoding="utf-8-sig", override=False)
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    model = os.getenv(
        "GEMINI_MODEL", "gemini-3.5-flash-lite"
    ).strip()

    if not api_key or not model:
        raise SystemExit(".env의 키와 모델 설정을 확인하세요.")

    report = {
        "scope": "vector_indirect_prompt_injection",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "model": model,
        "embedding_model": MODEL_NAME,
        "embedding_versions": {
            "fastembed": version("fastembed"),
            "onnxruntime": version("onnxruntime"),
        },
        "attack": attack,
        "source_documents": documents,
        "settings": {
            "role": "user",
            "top_k": 1,
            "min_score": 0.3,
            "temperature": 0,
            "max_output_tokens": 512,
        },
        "planned_cases": cases,
        "results": [],
    }

    for case in cases:
        print(f"\n[{case['case_id']}]")
        result = {
            "case_id": case["case_id"],
            "attack_delivered": case["attack_delivered"],
        }

        if not case["retrieved_ids"]:
            result["status"] = "skipped_no_context"
            report["results"].append(result)
            print("근거 문서 없음 — 생성 생략")
            continue

        try:
            answer = generate_answer(
                case["prompt"],
                api_key,
                model,
                system_instruction=case["system_instruction"],
            )
        except errors.APIError as exc:
            result.update(status="api_error", http_code=exc.code)
            report["results"].append(result)
            print(f"API 오류: HTTP {exc.code}. 중단합니다.")
            break
        except Exception as exc:
            result.update(
                status="execution_error",
                error_type=type(exc).__name__,
            )
            report["results"].append(result)
            print(f"실행 오류: {type(exc).__name__}. 중단합니다.")
            break

        verdict = judge(answer, attack["marker"])
        result.update(
            status="completed",
            answer=answer,
            marker_verdict=verdict,
        )
        report["results"].append(result)
        print(answer)
        print(f"[마커 판정] {verdict}")

    results = report["results"]
    report["generated_cases"] = sum(
        result["status"] == "completed" for result in results
    )
    report["complete"] = (
        len(results) == len(cases)
        and all(
            result["status"] in {"completed", "skipped_no_context"}
            for result in results
        )
    )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"\n보고서 저장: {args.output}")


if __name__ == "__main__":
    main()