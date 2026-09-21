"""지정한 비밀값의 정확한 문자열을 응답에서 가린다."""

from dataclasses import dataclass


@dataclass(frozen=True)
class GuardResult:
    text: str
    redacted: bool
    matched_secret_count: int


def redact_secrets(
    text: str,
    secrets: list[str],
) -> GuardResult:
    if any(
        not isinstance(secret, str) or not secret.strip()
        for secret in secrets
    ):
        raise ValueError("비밀값은 비어 있지 않은 문자열이어야 합니다.")

    # 중복 값을 제거하고 긴 값부터 처리한다.
    unique_secrets = sorted(set(secrets), key=lambda value: (-len(value), value))

    # 원본 응답을 기준으로 탐지한다.
    matched = [
        secret for secret in unique_secrets
        if secret in text
    ]

    # 겹치는 비밀값까지 처리하기 위해 원본의 일치 구간을 수집한다.
    spans = []
    for secret in matched:
        start = 0
        while True:
            index = text.find(secret, start)
            if index == -1:
                break
            spans.append((index, index + len(secret)))
            start = index + 1

    if not spans:
        return GuardResult(
            text=text,
            redacted=False,
            matched_secret_count=0,
        )

    # 겹치는 구간을 합쳐 비밀값 일부가 남지 않도록 한다.
    merged = []
    for start, end in sorted(spans):
        if merged and start <= merged[-1][1]:
            previous_start, previous_end = merged[-1]
            merged[-1] = (previous_start, max(previous_end, end))
        else:
            merged.append((start, end))

    parts = []
    cursor = 0
    for start, end in merged:
        parts.append(text[cursor:start])
        parts.append("[REDACTED]")
        cursor = end
    parts.append(text[cursor:])

    return GuardResult(
        text="".join(parts),
        redacted=True,
        matched_secret_count=len(matched),
    )