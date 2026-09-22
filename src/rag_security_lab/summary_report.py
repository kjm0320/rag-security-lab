"""기존 실험 보고서를 모은다. 모델 호출이나 종합 보안 판정은 하지 않는다."""

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from rag_security_lab.html_report import render_report


SOURCES = [
    (
        "검색 접근 제어",
        "retrieval_comparison.json",
        "retrieval_access_control",
    ),
    (
        "인젝션 비교 — 초기 실험",
        "injection_comparison.json",
        "system_instruction_comparison",
    ),
    (
        "인젝션 비교 — 평가 규칙 사칭",
        "fake-evaluation-rule.json",
        "system_instruction_comparison",
    ),
    (
        "인젝션 비교 — 시스템 메시지 사칭",
        "fake-system-message.json",
        "system_instruction_comparison",
    ),
    (
        "합성 비밀값 출력 필터",
        "disclosure_demo.json",
        "synthetic_secret_output_filter",
    ),
    (
        "시스템 프롬프트 유출",
        "prompt_leakage_demo.json",
        "synthetic_system_prompt_leakage",
    ),
    (
        "검색 품질 — 초기 탐색",
        "search_quality_threshold_0.json",
        "exploratory_search_quality",
    ),
    (
        "검색 품질 — 별도 검증",
        "search_validation_threshold_03.json",
        "exploratory_search_quality",
    ),
    (
        "벡터 검색 경로 — 시스템 메시지 사칭",
        "vector_fake_system_message.json",
        "vector_indirect_prompt_injection",
    ),
]


def extract_observations(data: dict) -> dict:
    scope = data["scope"]
    if scope == "vector_indirect_prompt_injection":
        planned_cases = data["planned_cases"]
        results = data["results"]

        planned = {case["case_id"]: case for case in planned_cases}
        if len(planned) != len(planned_cases):
            raise ValueError("계획된 조건 ID가 중복됐습니다.")

        result_map = {result["case_id"]: result for result in results}
        if len(result_map) != len(results):
            raise ValueError("실행 결과 ID가 중복됐습니다.")

        if not set(result_map).issubset(planned):
            raise ValueError("계획에 없는 실행 결과가 있습니다.")

        rows = []
        for case_id, case in planned.items():
            result = result_map.get(case_id)
            row = {
                "case_id": case_id,
                "retrieved_ids": case["retrieved_ids"],
                "scores": case["scores"],
                "attack_delivered": case["attack_delivered"],
            }

            if result is None:
                row["status"] = "not_run"
            else:
                if result["attack_delivered"] != case["attack_delivered"]:
                    raise ValueError("공격 전달 여부 기록이 일치하지 않습니다.")

                row["status"] = result["status"]

                if result["status"] == "completed":
                    row["marker_verdict"] = result["marker_verdict"]
                elif result["status"] == "api_error":
                    row["http_code"] = result["http_code"]
                elif result["status"] == "execution_error":
                    row["error_type"] = result["error_type"]
                elif result["status"] != "skipped_no_context":
                    raise ValueError("알 수 없는 실행 상태입니다.")

            rows.append(row)

        return {
            "attack_id": data["attack"]["id"],
            "embedding_model": data["embedding_model"],
            "embedding_versions": data["embedding_versions"],
            "settings": data["settings"],
            "reported_complete": data["complete"],
            "reported_generated_cases": data["generated_cases"],
            "cases": rows,
            "interpretation": [
                "공격 미전달과 모델의 공격 거부는 다르다.",
                "생성 생략 및 실행 오류에는 마커 판정을 부여하지 않는다.",
                "not_run은 보고서에 해당 조건의 실행 결과가 없다는 뜻이다.",
                "complete는 모든 조건에서 모델 응답을 받았다는 뜻이 아니다.",
            ],
        }
    if scope == "exploratory_search_quality":
        return {
            "embedding_model": data["embedding_model"],
            "settings": data["settings"],
            "document_fingerprints": data["document_fingerprints"],
            "methods": {
                method: {
                    "summary": data["methods"][method]["summary"],
                    "cases": data["methods"][method]["results"],
                }
                for method in ("keyword", "vector")
            },
        }

    if scope == "retrieval_access_control":
        return {
            mode: {
                "summary": data["modes"][mode]["summary"],
                "cases": data["modes"][mode]["results"],
            }
            for mode in ("baseline", "protected")
        }

    if scope == "synthetic_secret_output_filter":
        result = data["result"]
        return {
            "role": data["role"],
            "raw_contains_exact_secret": result[
                "raw_contains_exact_secret"
            ],
            "filtered_contains_exact_secret": result[
                "filtered_contains_exact_secret"
            ],
            "redacted": result["redacted"],
            "matched_secret_count": result["matched_secret_count"],
        }

    # 비교 실험과 시스템 프롬프트 실험의 기존 판정을 옮긴다.
    # 응답 본문과 시스템 지시문은 통합 보고서에 복제하지 않는다.
    fields = (
        "case_id",
        "status",
        "http_code",
        "error_type",
        "marker_verdict",
        "exact_canary_exposed",
        "full_base_instruction_exposed",
    )

    return {
        "attack_id": data.get("attack", {}).get("id"),
        "reported_complete": data.get("complete"),
        "reported_completed_cases": data.get("completed_cases"),
        "cases": [
            {key: result[key] for key in fields if key in result}
            for result in data["results"]
        ],
    }


def read_section(
    directory: Path,
    title: str,
    filename: str,
    expected_scope: str,
) -> dict:
    path = directory / filename
    section = {
        "title": title,
        "source": str(path),
        "state": "missing",
    }

    if not path.exists():
        return section

    try:
        with path.open(encoding="utf-8-sig") as file:
            data = json.load(file)

        if not isinstance(data, dict):
            raise ValueError("최상위 값이 JSON 객체가 아닙니다.")

        if data.get("scope") != expected_scope:
            raise ValueError("예상한 실험 범위와 다릅니다.")

        observations = extract_observations(data)

        section.update({
            "state": "loaded",
            "scope": data["scope"],
            "source_created_at": data.get("created_at"),
            "model": data.get("model"),
            "settings": data.get("settings"),
            "observations": observations,
        })

    except (
        OSError,
        UnicodeError,
        ValueError,
        KeyError,
        TypeError,
        AttributeError,
    ) as exc:
        section.update({
            "state": "unreadable",
            "error_type": type(exc).__name__,
        })

    return section


def build_summary(directory: Path) -> dict:
    sections = [
        read_section(directory, title, filename, scope)
        for title, filename, scope in SOURCES
    ]

    counts = {
        state: sum(section["state"] == state for section in sections)
        for state in ("loaded", "missing", "unreadable")
    }

    return {
        "scope": "experiment_summary",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "collection_counts": counts,
        "interpretation": [
            "loaded는 파일 읽기에 성공했다는 뜻이며 보안 테스트 통과가 아니다.",
            "기존 보고서의 판정을 옮긴 것이며 모델 응답을 재평가하지 않는다.",
            "reported_complete가 false이면 해당 실험은 미완료다.",
            "실행 오류는 공격 차단 성공으로 집계하지 않는다.",
            "누락된 보고서는 안전하다고 판정하지 않는다.",
            "여러 파일에 같은 실행이 중복될 수 있어 통합 성공률을 계산하지 않는다.",
            "초기 비교 보고서에는 attack_id가 없을 수 있다.",
        ],
        "security_score": None,
        "overall_risk": "not_assessed",
        "sections": sections,
        "html_output_handling": {
            "state": "separate_evidence",
            "document": "docs/output-handling-01.md",
            "note": (
                "HTML 출력 처리는 별도 자동 테스트와 수동 확인으로 검증했다. "
                "이 통합기는 테스트를 실행하거나 문서 내용을 검증하지 않는다."
            ),
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="실험 결과 통합 보고서")
    parser.add_argument(
        "--reports-dir",
        type=Path,
        default=Path("reports"),
    )
    args = parser.parse_args()

    summary = build_summary(args.reports_dir)
    args.reports_dir.mkdir(parents=True, exist_ok=True)

    json_path = args.reports_dir / "summary.json"
    html_path = args.reports_dir / "summary.html"

    json_path.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    html_path.write_text(render_report(summary), encoding="utf-8")

    for section in summary["sections"]:
        print(f"[{section['state']}] {section['title']}")

    print(f"\n수집 결과: {summary['collection_counts']}")
    print("종합 보안 점수: 미산출")
    print(f"JSON: {json_path}")
    print(f"HTML: {html_path}")


if __name__ == "__main__":
    main()