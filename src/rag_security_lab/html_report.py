"""JSON 보고서의 모든 내용을 HTML 텍스트로 표시한다."""

import argparse
import json
from html import escape
from pathlib import Path


def render_report(report: dict) -> str:
    # 모델 응답뿐 아니라 JSON의 키와 모든 값까지 함께 이스케이프한다.
    serialized = json.dumps(report, ensure_ascii=False, indent=2)
    safe_content = escape(serialized, quote=True)

    return (
        "<!doctype html>\n"
        '<html lang="ko">\n'
        "<head>\n"
        '<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
        '<meta http-equiv="Content-Security-Policy" '
        'content="default-src \'none\'; style-src \'unsafe-inline\'; '
        'base-uri \'none\'; form-action \'none\'">\n'
        "<title>RAG Security Lab — 실험 보고서</title>\n"
        "<style>\n"
        "body { max-width: 1000px; margin: 40px auto; padding: 0 20px; "
        "font-family: sans-serif; line-height: 1.6; color: #18212f; }\n"
        "pre { padding: 24px; background: #f1f5f9; border-radius: 12px; "
        "white-space: pre-wrap; overflow-wrap: anywhere; }\n"
        "</style>\n"
        "</head>\n"
        "<body>\n"
        "<h1>RAG Security Lab</h1>\n"
        "<p>실험 보고서 — 입력 데이터는 실행하지 않고 텍스트로 표시합니다.</p>\n"
        f"<pre>{safe_content}</pre>\n"
        "</body>\n"
        "</html>\n"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="JSON 보고서를 HTML로 변환")
    parser.add_argument("input", type=Path)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("reports/security_report.html"),
    )
    args = parser.parse_args()

    if args.input.resolve() == args.output.resolve():
        parser.error("입력 파일과 출력 파일은 달라야 합니다.")

    with args.input.open(encoding="utf-8-sig") as file:
        report = json.load(file)

    if not isinstance(report, dict):
        parser.error("보고서의 최상위 값은 JSON 객체여야 합니다.")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(render_report(report), encoding="utf-8")
    print(f"HTML 보고서 저장: {args.output}")


if __name__ == "__main__":
    main()