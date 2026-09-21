# RAG Security Lab

[![Security Tests](https://github.com/kjm0320/rag-security-lab/actions/workflows/tests.yml/badge.svg)](https://github.com/kjm0320/rag-security-lab/actions/workflows/tests.yml)

LLM/RAG 애플리케이션의 보안 동작을 실험하고,
검색·접근 제어·출력 처리 결과를 기록하는 개인 프로젝트입니다.

키워드 및 로컬 벡터 검색, SQLite 문서 저장소,
Gemini 기반 답변 생성, 합성 비밀값 출력 필터,
보안 실험 및 JSON·HTML 보고서를 구현했습니다.

소규모 합성 데이터 기반 실습 프로젝트이며,
실제 서비스의 안전성을 인증하거나 보장하지 않습니다.

## 주요 기능

- JSON 기반 키워드 검색
- 다국어 로컬 임베딩 및 SQLite 벡터 저장
- 역할별 문서 접근 제어
- 검색 임계값 적용과 근거 문서가 없을 때 LLM 호출 생략
- Gemini API를 통한 문서 기반 답변 생성
- 지정한 합성 비밀값의 출력 가림
- 간접 프롬프트 인젝션 및 시스템 프롬프트 유출 실험
- 검색 품질과 출력 필터 적용 전후 비교
- HTML 이스케이프를 적용한 보고서 생성
- 기존 실험 결과 통합
- 실제 LLM 호출 없는 자동 테스트 76개
- GitHub Actions 자동 테스트

## 구현 범위

| 영역 | 구현·검증 내용 | 현재 한계 |
|---|---|---|
| Prompt Injection | 문서 내 공격 3종, 기본·보안 지시문 비교 | 소수 사례, 조건별 1회 실행 |
| Sensitive Information Disclosure | 합성 비밀값의 필터 적용 전후 비교 | 지정 문자열의 정확한 일치만 탐지 |
| Improper Output Handling | HTML 텍스트 이스케이프 및 태그 생성 방지 테스트 | 실제 브라우저 공격 실행 자동 검증은 미구현 |
| RAG Data Leakage | 검색 전 역할별 후보 제한 | 실제 사용자 인증은 미구현 |
| System Prompt Leakage | 합성 내부 표식과 지시문 전체 원문 노출 검사 | 부분 공개·의역 등을 포괄적으로 탐지하지 못함 |

위 항목은 프로젝트의 실험 영역이며,
OWASP GenAI 공식 분류와 일대일 대응하지 않습니다.
공식 분류와의 상세 연결은 후속 작업입니다.

## 동작 흐름

1. 질문과 실습용 역할을 입력합니다.
2. 선택한 검색 방식으로 접근 가능한 문서만 검색합니다.
3. 검색 결과가 없으면 Gemini를 호출하지 않습니다.
4. 검색 결과가 있으면 질문과 문서를 Gemini에 전달합니다.
5. 생성 답변에 합성 비밀값 출력 필터를 적용합니다.
6. 필터 적용 답변을 출력합니다.

| 검색 방식 | 저장소 | 결과 선택 |
|---|---|---|
| keyword — 기본값 | JSON | 공통 토큰 점수, 최대 3개 |
| vector | SQLite | 코사인 유사도, 최대 1개, 기본 임계값 0.3 |

벡터 검색은 SQLite에 임베딩을 저장하고 Python에서 후보 전체를 비교합니다.
대규모 전용 벡터 DB나 근사 최근접 검색 인덱스는 아닙니다.

## 검증 환경

| 항목 | 환경 |
|---|---|
| 로컬 개발 | Windows CMD / Python 3.12.10 |
| RAM | 8GB |
| 임베딩 실행 장치 | CPU |
| FastEmbed | 0.8.0 |
| ONNX Runtime | 1.30.0 |
| 임베딩 모델 | sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2 |
| 벡터 차원 | 384 |
| 답변 생성 모델 | gemini-3.5-flash-lite |
| GitHub CI | Ubuntu / Python 3.12 |

FastEmbed와 ONNX Runtime은 vector 선택 의존성에 버전을 지정했습니다.
전체 하위 의존성과 모델 파일 리비전까지 고정한 환경은 아닙니다.

## 설치

Windows CMD에서 실행합니다.

```bat
git clone https://github.com/kjm0320/rag-security-lab.git
cd rag-security-lab
python -m venv .venv
.venv\Scripts\activate.bat
python -m pip install -e .
```

벡터 검색을 사용하려면 추가로 설치합니다.

```bat
python -m pip install -e ".[vector]"
```

이하 명령어는 모두 프로젝트 루트에서 실행합니다.

## Gemini API 설정

프로젝트 루트에 `.env` 파일을 만듭니다.
형식은 `.env.example`을 참고합니다.

```dotenv
GEMINI_API_KEY=발급받은_API_키
GEMINI_MODEL=gemini-3.5-flash-lite
```

- 실제 키는 `.env`에만 설정하고 Git에 올리지 않습니다.
- `.env.example`에는 실제 키를 넣지 않습니다.
- 기존 환경 변수가 있으면 `.env`보다 우선합니다.
- 실제 답변 생성에는 API 키, 네트워크 및 사용 가능한 할당량이 필요합니다.
- 무료 사용을 원하면 AI Studio의 프로젝트 등급과 모델별 무료 할당량을 확인합니다.
- 모델 제공 여부와 요금·할당량은 변경될 수 있습니다.

[API 키 관리](https://aistudio.google.com/apikey) ·
[공식 요금표](https://ai.google.dev/gemini-api/docs/pricing)

연결 확인:

```bat
python -m rag_security_lab.check_api
```

모델 목록 조회 성공은 모든 모델의 무료 사용이나
해당 계정의 답변 생성 가능 여부를 보장하지 않습니다.

## 빠른 실행

### 키워드 RAG

```bat
python -m rag_security_lab.rag "비밀번호 변경 주기는?" --role user
```

관찰한 답변:

```text
비밀번호 변경 주기는 90일입니다 [doc-001].
```

### 벡터 RAG 준비

```bat
python -m rag_security_lab.document_store init
python -m rag_security_lab.vector_store build
```

- init: DB의 문서를 JSON 내용으로 교체합니다.
- build: 저장된 문서의 벡터 인덱스를 재생성합니다.
- 모델 최초 다운로드에는 인터넷 연결이 필요합니다.
- 임베딩 계산은 로컬 CPU에서 수행합니다.
- DB와 모델 캐시는 Git에서 제외한 `.local/`에 저장합니다.

벡터 RAG 실행:

```bat
python -m rag_security_lab.rag "암호는 얼마나 자주 바꿔야 하나요?" --role user --retriever vector
```

실제 확인 결과:

```text
[모델] gemini-3.5-flash-lite
[전달 문서] doc-001

[답변]
비밀번호 변경 주기는 90일입니다 [doc-001].
```

생성 문장은 실행마다 달라질 수 있습니다.

### 접근 가능한 근거가 없는 질문

```bat
python -m rag_security_lab.rag "관리자 복구" --role user --retriever vector
```

현재 문서와 기본 임계값에서 확인한 결과:

```text
접근 가능한 근거 문서가 없어 답변할 수 없습니다.
[API 호출 없음]
```

여기서 API 호출 없음은 Gemini 답변 생성 요청을 생략했다는 뜻입니다.
벡터 모드의 로컬 임베딩 계산은 수행합니다.

## 접근 제어와 출력 정책

| 역할 | 조회 가능한 문서 |
|---|---|
| user | public |
| admin | public, restricted |

권한 필터는 검색 순위 및 상위 결과 선택 전에 적용합니다.
질문에서 관리자라고 주장해도 역할은 변경되지 않습니다.

`--role`은 실습용 선택 옵션입니다.
CLI 사용자가 직접 역할을 정할 수 있으므로 실제 사용자 인증이 아닙니다.
서비스에서는 서버가 인증 결과를 바탕으로 역할을 결정해야 합니다.

출력 정책은 별도로 적용합니다.

- 일반 RAG CLI는 역할과 관계없이 `LAB-RECOVERY-7391`을 가립니다.
- 해당 값은 실습 문서에 있는 가짜 복구 코드입니다.
- 출력 시 `[REDACTED]`로 바꾸며, 문서의 모델 전달 자체를 막지는 않습니다.
- 대소문자 변경, 분할 출력, 인코딩 등은 탐지하지 못할 수 있습니다.

실험 모듈은 비교를 위해 원본 응답을 표시하거나 저장할 수 있습니다.
일반 RAG CLI의 출력 정책과 구분해야 합니다.

## 검색만 실행하기

기본 키워드 검색은 비교 실험용으로 접근 제어 없이 동작합니다.

```bat
python -m rag_security_lab.retrieval "관리자 복구"
```

접근 제어 적용 키워드 검색:

```bat
python -m rag_security_lab.gateway "관리자 복구" --role user
python -m rag_security_lab.gateway "관리자 복구" --role admin
```

벡터 검색:

```bat
python -m rag_security_lab.vector_store search "관리자 복구" --role user
python -m rag_security_lab.vector_store search "관리자 복구" --role admin
```

벡터 검색 모듈 단독 실행의 기본 임계값은 0.0입니다.
일반 RAG CLI의 벡터 모드 기본 임계값 0.3과 다릅니다.

```bat
python -m rag_security_lab.vector_store search "관리자 복구" --role user --min-score 0.3
```

문서 내용이나 접근 등급 변경은 해시로 검사하며,
불일치하면 벡터 인덱스를 다시 만들어야 합니다.

## 검색 품질 실험

### 초기 탐색 — 질문 8개

| 지표 | 키워드 | 벡터·임계값 0.0 |
|---|---:|---:|
| 정답 문서 1순위 검색 | 5/6 | 6/6 |
| 근거 없는 질문에서 빈 결과 | 2/2 | 0/2 |

벡터 검색은 표현이 다른 질문을 찾았지만,
관련 없는 문서도 반환했습니다.

탐색 결과에서 정답 문서의 최저 점수는 0.4815,
불필요한 결과의 최고 점수는 0.1001이었습니다.
이를 바탕으로 실험용 임계값 0.3을 선택했습니다.

### 별도 검증 — 새로운 질문 8개

| 지표 | 키워드 | 벡터·임계값 0.3 |
|---|---:|---:|
| 정답 문서 1순위 검색 | 4/6 | 6/6 |
| 근거 없는 질문에서 빈 결과 | 2/2 | 2/2 |

같은 문서 3개에 대한 작은 검증입니다.
일반적인 검색 정확도나 다른 데이터의 최적 임계값으로 해석하지 않습니다.

실행:

```bat
python -m rag_security_lab.evaluate_search --min-score 0.0 --output reports/search_quality_threshold_0.json
python -m rag_security_lab.evaluate_search --cases datasets/search_validation_cases.json --min-score 0.3 --output reports/search_validation_threshold_03.json
```

이 명령어들은 Gemini API를 호출하지 않습니다.

## 보안 실험 결과

| 실험 | 관찰 결과 | 해석 범위 |
|---|---|---|
| 검색 접근 제어 | 제한 문서 노출 2/2 → 0/2, 정상 검색 3/3 유지 | 합성 검색 테스트셋 |
| 간접 인젝션 3종 | basic·guarded 모두 목표 마커 출력 0/3 | 추가 보안 지시문의 효과 차이 미관찰 |
| 합성 비밀값 필터 | 원본에 코드 포함, 필터 후 정확한 코드 없음 | 동일 모델 응답 1개 |
| 시스템 프롬프트 유출 | 정상·유출 유도 조건 모두 표식 및 전체 원문 노출 미관찰 | 조건별 1회 |
| HTML 출력 처리 | 공격 문자열이 태그로 생성되지 않고 텍스트로 보존 | HTMLParser 자동 테스트와 정상 보고서 열기 확인 |

기존 인젝션·프롬프트 유출 실험 전체를
벡터 RAG 경로에서 재실행한 것은 아닙니다.

### 실험 명령어

검색 접근 제어 — API 호출 없음:

```bat
python -m rag_security_lab.evaluate
```

인젝션 비교 준비 — API 호출 없음:

```bat
python -m rag_security_lab.compare_injection --case fake-system-message
```

실제 인젝션 비교 — 최대 4회 모델 호출:

```bat
python -m rag_security_lab.compare_injection --case fake-system-message --execute --output reports/fake-system-message.json
```

다른 공격 ID:

- ignore-instructions
- fake-evaluation-rule

합성 비밀값 필터 — 모델 1회 호출:

```bat
python -m rag_security_lab.disclosure_demo --execute
```

시스템 프롬프트 유출 — 최대 2회 모델 호출:

```bat
python -m rag_security_lab.prompt_leakage_demo --execute
```

API 오류는 공격 차단 성공으로 판정하지 않습니다.
보고서의 실행 완료 여부와 케이스별 상태를 함께 확인해야 합니다.

## JSON·HTML 보고서

개별 보고서 HTML 변환:

```bat
python -m rag_security_lab.html_report reports/disclosure_demo.json
start "" "reports\security_report.html"
```

입력 데이터 전체를 HTML 텍스트로 이스케이프합니다.
이 처리는 민감정보 제거 기능이 아닙니다.

통합 보고서 생성:

```bat
python -m rag_security_lab.summary_report
start "" "reports\summary.html"
```

출력 파일:

- reports/summary.json
- reports/summary.html

통합기는 지정된 기존 실험 보고서 6개를 읽습니다.
검색 품질 보고서는 아직 통합 대상에 포함하지 않습니다.

| 수집 상태 | 의미 |
|---|---|
| loaded | 필요한 항목을 읽어 통합함 |
| missing | 원본 파일이 없음 |
| unreadable | 파싱, 실험 범위 확인 또는 필요한 항목 읽기에 실패 |

loaded는 보안 테스트 통과를 의미하지 않습니다.
미완료 상태와 API 오류는 원본에 기록된 그대로 유지합니다.

현재 종합 점수와 위험도는 산출하지 않습니다.

- security_score: null
- overall_risk: not_assessed

통합기는 기존 판정을 모으는 기능입니다.
응답을 재평가하거나 모든 데이터 형식·수치의 일관성을 검증하지 않습니다.

생성 보고서는 Git에 포함되지 않습니다.
새로 복제한 저장소에서는 원본 보고서가 missing으로 표시될 수 있습니다.
관찰 결과는 docs/의 문서에서 확인할 수 있습니다.

같은 출력 경로로 재실행하면 이전 보고서를 덮어씁니다.

## 자동 테스트

```bat
python -m unittest discover -s tests -v
```

현재 자동 테스트는 총 76개입니다.

| 파일 | 개수 | 주요 검증 |
|---|---:|---|
| test_gateway.py | 7 | 검색 전 접근 제어 |
| test_evaluate.py | 6 | 검색 보안 평가 계산 |
| test_rag.py | 5 | 전달 문서와 생성 호출 조건 |
| test_injection_demo.py | 4 | 마커 판정 및 준비 실행 |
| test_compare_injection.py | 6 | 비교 조건과 공격 입력 분리 |
| test_output_guard.py | 6 | 비밀값 가림 및 탐지 한계 |
| test_disclosure_demo.py | 3 | 출력 필터 전후 비교 |
| test_rag_output.py | 2 | 일반 CLI의 출력 필터 |
| test_html_report.py | 3 | HTML 텍스트 처리 |
| test_prompt_leakage.py | 6 | 내부 표식 분리와 노출 판정 |
| test_summary_report.py | 7 | 보고서 수집 상태 |
| test_document_store.py | 5 | SQLite 저장 및 권한 조회 |
| test_vector_store.py | 7 | 벡터 순위·권한·인덱스 검사 |
| test_evaluate_search.py | 5 | 검색 품질 지표 |
| test_rag_vector.py | 4 | 벡터 RAG 연결 |

자동 테스트는 가짜 응답과 고정 벡터를 사용합니다.
실제 Gemini API 호출이나 임베딩 모델 다운로드는 하지 않습니다.
기본 설치만으로 실행할 수 있습니다.

GitHub Actions는 push와 pull request마다 동일한 테스트를 실행합니다.

```bat
gh run list --workflow tests.yml --limit 3
```

## 디렉터리

| 경로 | 용도 |
|---|---|
| src/rag_security_lab/ | 검색·RAG·필터·실험·보고서 코드 |
| datasets/ | 합성 문서와 평가 질문 |
| tests/ | 자동 테스트 |
| docs/ | 설계·실험 조건·관찰 결과 |
| reports/ | 생성 보고서, Git 추적 제외 |
| .local/ | SQLite DB와 모델 캐시, Git 추적 제외 |
| .env | 로컬 API 키와 모델 설정, Git 추적 제외 |
| .env.example | 실제 키가 없는 설정 예시 |

## 실험 기록

- [인젝션 비교](docs/injection-comparison-summary.md)
- [합성 비밀값 출력 필터](docs/disclosure-experiment-01.md)
- [HTML 출력 처리](docs/output-handling-01.md)
- [시스템 프롬프트 유출](docs/prompt-leakage-01.md)
- [로컬 벡터 검색](docs/vector-search-01.md)
- [검색 품질 비교](docs/search-quality-01.md)
- [벡터 RAG 연결](docs/vector-rag-01.md)

## 한계와 후속 작업

- 실제 사용자 인증과 서버 측 역할 결정 미구현
- 작은 합성 데이터와 소수 공격 사례에 한정
- 긴 문서의 청크 분할 미구현
- 모델 입력 길이 제한에 따른 잘림 가능
- 생성 답변의 인용·정확성 자동 검증 미구현
- 비밀값의 변형·인코딩·분할 출력 탐지 미구현
- 시스템 프롬프트 부분 공개·의역 탐지 미구현
- 실제 브라우저에서의 공격 실행 자동 검증 미구현
- 모델 파일 리비전과 전체 의존성 고정 미완료
- 동시 문서 변경·검색에 대한 운영 환경 검증 미완료
- 벡터 경로에서 전체 공격 회귀 실험 미완료
- 검색 품질 보고서의 통합 보고서 연결 미완료
- OWASP GenAI 상세 매핑 및 종합 점수 산식 미구현

## 데이터 원칙

합성 문서와 가짜 비밀값만 사용합니다.

실제 API 키·개인정보·기밀 문서를 저장소나 실험 데이터에 넣지 않습니다.
Gemini 답변 생성 시 질문, 검색 문서, 시스템 지시문이 외부 API로 전송됩니다.

보고서에는 원본 응답과 합성 비밀값이 포함될 수 있으므로,
공개하거나 공유하기 전에 내용을 확인합니다.