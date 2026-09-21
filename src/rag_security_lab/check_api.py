"""API 키를 출력하지 않고 Gemini 모델 목록을 조회한다."""

import os
from pathlib import Path

from dotenv import load_dotenv
from google import genai
from google.genai import errors


def main() -> None:
    load_dotenv(
        dotenv_path=Path(".env"),
        encoding="utf-8-sig",
        override=False,
    )
    api_key = os.getenv("GEMINI_API_KEY", "").strip()

    if not api_key:
        raise SystemExit(
            "GEMINI_API_KEY가 없습니다. 프로젝트 루트의 .env를 확인하세요."
        )

    try:
        with genai.Client(api_key=api_key) as client:
            names = sorted(
                model.name
                for model in client.models.list()
                if model.name
                and "generateContent" in (model.supported_actions or [])
            )
    except errors.APIError as exc:
        # 오류 원문 대신 상태 코드만 출력해 인증 정보 노출을 피한다.
        raise SystemExit(
            f"API 조회 실패: HTTP {exc.code}. "
            "키 설정과 AI Studio의 프로젝트 상태를 확인하세요."
        ) from None
    except Exception as exc:
        raise SystemExit(
            f"연결 오류: {type(exc).__name__}. "
            "인터넷 연결과 패키지 설치 상태를 확인하세요."
        ) from None

    print("[OK] 모델 목록 조회 성공")
    print("목록에 표시된 모델이 모두 무료라는 뜻은 아닙니다.")

    for name in names:
        print(f"- {name}")


if __name__ == "__main__":
    main()