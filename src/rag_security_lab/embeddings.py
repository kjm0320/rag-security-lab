"""CPU에서 실행하는 로컬 다국어 임베딩."""

import math
from pathlib import Path


MODEL_NAME = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
DIMENSION = 384
CACHE_DIR = Path(".local/models")


class LocalEmbedder:
    def __init__(self):
        # 선택 패키지가 없는 환경에서도 다른 모듈은 import할 수 있다.
        from fastembed import TextEmbedding

        CACHE_DIR.mkdir(parents=True, exist_ok=True)

        self.model = TextEmbedding(
            model_name=MODEL_NAME,
            cache_dir=str(CACHE_DIR),
            providers=["CPUExecutionProvider"],
            threads=2,
        )

    def encode(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []

        if any(
            not isinstance(text, str) or not text.strip()
            for text in texts
        ):
            raise ValueError("입력은 비어 있지 않은 문자열이어야 합니다.")

        vectors = []

        for embedding in self.model.embed(texts, batch_size=1):
            vector = [float(value) for value in embedding]

            if len(vector) != DIMENSION:
                raise ValueError("예상한 임베딩 차원과 다릅니다.")

            if not all(math.isfinite(value) for value in vector):
                raise ValueError("임베딩에 유효하지 않은 숫자가 있습니다.")

            norm = math.sqrt(sum(value * value for value in vector))
            if norm == 0:
                raise ValueError("길이가 0인 임베딩입니다.")

            # 내적으로 코사인 유사도를 계산할 수 있도록 정규화한다.
            vectors.append([value / norm for value in vector])

        if len(vectors) != len(texts):
            raise ValueError("입력 개수와 임베딩 개수가 다릅니다.")

        return vectors


def main() -> None:
    print(f"[모델] {MODEL_NAME}")
    print("[실행 장치] CPU")
    print(f"[모델 저장 위치] {CACHE_DIR}")
    print("[안내] 최초 실행에는 모델 다운로드가 필요합니다.")

    embedder = LocalEmbedder()
    texts = [
        "비밀번호 변경 주기는 90일입니다.",
        "암호는 얼마나 자주 바꿔야 하나요?",
        "VPN 접속에는 다중 인증이 필요합니다.",
    ]
    vectors = embedder.encode(texts)

    print(f"\n[생성 완료] {len(vectors)}개 벡터")
    print(f"[차원] {len(vectors[0])}")

    for index in (1, 2):
        similarity = sum(
            left * right
            for left, right in zip(vectors[0], vectors[index])
        )
        print(f"[유사도] 문장 1 ↔ 문장 {index + 1}: {similarity:.4f}")


if __name__ == "__main__":
    main()