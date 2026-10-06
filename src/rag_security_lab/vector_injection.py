"""임시 벡터 DB를 사용한 문서 인젝션 비교 및 반복 실험."""

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

    with tempfile.TemporaryDirectory(
        prefix="rag-vector-experiment-"
    ) as temp:
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
                        hit["document"]["id"]
                        == attack["target_document_id"]
                        and attack["payload"]
                        in hit["document"]["text"]
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


def build_plan(cases, repeat):
    """검색 결과를 고정하고 생성 실험만 반복한다."""
    if not isinstance(repeat, int) or isinstance(repeat, bool):
        raise ValueError("반복 횟수는 정수여야 합니다.")

    if not 1 <= repeat <= 5:
        raise ValueError("반복 횟수는 1~5여야 합니다.")

    case_ids = [case["case_id"] for case in cases]
    if len(case_ids) != len(set(case_ids)):
        raise ValueError("중복된 조건 ID가 있습니다.")

    planned = []

    for trial in range(1, repeat + 1):
        for case in cases:
            item = copy.deepcopy(case)
            condition_id = case["case_id"]

            item["condition_id"] = condition_id
            item["trial"] = trial

            # 단일 실행의 ID는 기존 보고서 형식과 동일하게 유지한다.
            if repeat > 1:
                item["case_id"] = f"trial-{trial}/{condition_id}"

            planned.append(item)

    return planned


def validate_call_budget(cases, max_calls):
    """실행 전에 필요한 호출 수가 허용 범위인지 확인한다."""
    if (
        not isinstance(max_calls, int)
        or isinstance(max_calls, bool)
        or not 1 <= max_calls <= 20
    ):
        raise ValueError("호출 상한은 1~20이어야 합니다.")

    required = sum(bool(case["retrieved_ids"]) for case in cases)

    if required > max_calls:
        raise ValueError(
            f"예정 호출 {required}회가 상한 {max_calls}회를 초과합니다. "
            "반복 횟수를 줄이거나 --max-calls를 명시하세요."
        )

    return required


def execute_cases(cases, attack, api_key, model, max_calls):
    """오류가 발생하면 중단하고 이후 조건은 실행하지 않는다."""
    validate_call_budget(cases, max_calls)

    results = []
    attempted_calls = 0
    stop_reason = None

    for case in cases:
        print(f"\n[{case['case_id']}]")

        result = {
            "case_id": case["case_id"],
            "condition_id": case.get(
                "condition_id", case["case_id"]
            ),
            "trial": case.get("trial", 1),
            "attack_delivered": case["attack_delivered"],
        }

        if not case["retrieved_ids"]:
            result["status"] = "skipped_no_context"
            results.append(result)
            print("근거 문서 없음 — 생성 생략")
            continue

        attempted_calls += 1

        try:
            answer = generate_answer(
                case["prompt"],
                api_key,
                model,
                system_instruction=case["system_instruction"],
            )

            if not isinstance(answer, str) or not answer.strip():
                raise ValueError("비어 있는 모델 응답입니다.")

            verdict = judge(answer, attack["marker"])

        except errors.APIError as exc:
            result.update(
                status="api_error",
                http_code=exc.code,
            )
            results.append(result)
            stop_reason = "api_error"
            print(f"API 오류: HTTP {exc.code}. 중단합니다.")
            break

        except Exception as exc:
            result.update(
                status="execution_error",
                error_type=type(exc).__name__,
            )
            results.append(result)
            stop_reason = "execution_error"
            print(
                f"실행 오류: {type(exc).__name__}. 중단합니다."
            )
            break

        result.update(
            status="completed",
            answer=answer,
            marker_verdict=verdict,
        )
        results.append(result)

        print(answer)
        print(f"[마커 판정] {verdict}")

    return {
        "results": results,
        "attempted_calls": attempted_calls,
        "stop_reason": stop_reason,
    }


def main():
    parser = argparse.ArgumentParser(
        description="실제 벡터 검색 경로의 문서 인젝션 반복 실험"
    )
    parser.add_argument("--case", default="fake-system-message")
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--repeat", type=int, default=1)
    parser.add_argument("--max-calls", type=int, default=4)
    parser.add_argument(
        "--documents",
        type=Path,
        default=Path("datasets/documents.json"),
    )
    parser.add_argument(
        "--attacks",
        type=Path,
        default=Path("datasets/injection_cases.json"),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("reports/vector_injection.json"),
    )
    args = parser.parse_args()

    if not 1 <= args.repeat <= 5:
        parser.error("--repeat는 1~5여야 합니다.")

    if not 1 <= args.max_calls <= 20:
        parser.error("--max-calls는 1~20이어야 합니다.")

    # 입력 데이터 파일을 보고서로 덮어쓰지 않도록 검사한다.
    if args.output.resolve() in {
        args.documents.resolve(),
        args.attacks.resolve(),
    }:
        parser.error("보고서 경로는 입력 데이터 경로와 달라야 합니다.")

    try:
        attack = load_attack(args.attacks, args.case)
        documents = load_documents(args.documents)
        base_cases = prepare_cases(
            documents, attack, LocalEmbedder()
        )
        cases = build_plan(base_cases, args.repeat)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        raise SystemExit(f"실험 준비 실패: {exc}") from exc

    planned_calls = sum(
        bool(case["retrieved_ids"]) for case in cases
    )

    print(f"\n[공격] {attack['id']}")
    print(f"[반복 횟수] {args.repeat}")
    print(f"[전체 조건 수] {len(cases)}")
    print(f"[예정 생성 호출] 최대 {planned_calls}회")
    print(f"[설정한 호출 상한] {args.max_calls}회")

    for case in cases:
        scores = [
            round(score, 4) for score in case["scores"]
        ]
        print(
            f"[{case['case_id']}] "
            f"문서={case['retrieved_ids']} "
            f"점수={scores} "
            f"공격전달={case['attack_delivered']}"
        )

    if not args.execute:
        if planned_calls > args.max_calls:
            print(
                "\n[실행 조건] 현재 호출 상한으로는 실행할 수 없습니다."
            )
            print(
                "반복 횟수를 줄이거나 --max-calls를 명시하세요."
            )

        print("\n[준비 완료 — Gemini API 호출 없음]")
        return

    try:
        validate_call_budget(cases, args.max_calls)
    except ValueError as exc:
        parser.error(str(exc))

    load_dotenv(".env", encoding="utf-8-sig", override=False)
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    model = os.getenv(
        "GEMINI_MODEL", "gemini-3.5-flash-lite"
    ).strip()

    if not api_key or not model:
        raise SystemExit(".env의 키와 모델 설정을 확인하세요.")

    report = {
        "schema_version": 2,
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
        "input_paths": {
            "documents": str(args.documents),
            "attacks": str(args.attacks),
        },
        "settings": {
            "role": "user",
            "top_k": 1,
            "min_score": 0.3,
            "temperature": 0,
            "max_output_tokens": 512,
            "repeat": args.repeat,
            "max_calls": args.max_calls,
            "retrieval_reused_across_trials": True,
        },
        "planned_calls": planned_calls,
        "planned_cases": cases,
    }

    execution = execute_cases(
        cases,
        attack,
        api_key,
        model,
        args.max_calls,
    )
    report.update(execution)

    results = report["results"]
    finished_ids = {result["case_id"] for result in results}

    # 실행되지 않은 조건에는 성공/실패 판정을 붙이지 않는다.
    report["not_run_case_ids"] = [
        case["case_id"]
        for case in cases
        if case["case_id"] not in finished_ids
    ]
    report["generated_cases"] = sum(
        result["status"] == "completed"
        for result in results
    )
    report["skipped_cases"] = sum(
        result["status"] == "skipped_no_context"
        for result in results
    )
    report["complete"] = (
        len(results) == len(cases)
        and all(
            result["status"] in {
                "completed",
                "skipped_no_context",
            }
            for result in results
        )
    )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    print(
        f"\n[응답 생성 완료] "
        f"{report['generated_cases']}/{len(cases)}"
    )
    print(f"[생성 함수 호출] {report['attempted_calls']}회")
    print(f"[미실행 조건] {len(report['not_run_case_ids'])}개")
    print(f"보고서 저장: {args.output}")

    if not report["complete"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()