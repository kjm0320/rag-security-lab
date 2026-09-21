# RAG Security Lab

[![Security Tests](https://github.com/kjm0320/rag-security-lab/actions/workflows/tests.yml/badge.svg)](https://github.com/kjm0320/rag-security-lab/actions/workflows/tests.yml)

LLM/RAG 애플리케이션에 보안 테스트를 자동 실행하고,
방어 적용 전후의 결과를 비교하는 개인 프로젝트입니다.

현재는 키워드 기반 문서 검색, 역할별 접근 제어,
검색 보안 평가 및 JSON 보고서 생성을 구현했습니다.
LLM 연동과 답변 생성은 아직 구현하지 않았습니다.

## 1. 프로젝트 목표

실습용 RAG 시스템과 Security Gateway를 구현하고,
재현 가능한 테스트셋으로 공격 성공 여부와 정상 동작을 평가합니다.

최종 목표는 다음과 같습니다.

- LLM/RAG 보안 테스트셋 구성
- 공격 시나리오 자동 실행 및 결과 판정
- Security Gateway를 통한 방어 적용
- 동일한 실험 조건에서 방어 전후 비교
- 케이스별 판정 근거와 결과 보고서 생성
- 자체 평가 기준에 따른 Security Score 및 Overall Risk 산출

보안 점수는 프로젝트에서 정의한 실험 지표이며,
공식 인증이나 시스템 전체의 안전성을 보장하지 않습니다.

## 2. 보안 테스트 범위

아래 표는 최종 구현 목표입니다.
현재 구현된 평가는 검색 단계의 문서 접근 제어에 한정됩니다.

| 테스트 영역 | 확인할 내용 |
|---|---|
| Prompt Injection | 사용자 입력이나 검색 문서의 악성 지시가 동작을 변경하는지 |
| Sensitive Information Disclosure | 가짜 민감정보가 응답에 노출되는지 |
| Improper Output Handling | 모델 출력이 후속 처리 과정에서 안전하게 다뤄지는지 |
| RAG Data Leakage | 접근 권한이 없는 문서의 정보가 노출되는지 |
| System Prompt Leakage | 내부 시스템 지시문이 노출되는지 |

OWASP GenAI 위험 분류를 참고해 테스트를 정리할 예정입니다.
위 항목은 프로젝트의 테스트 영역이며,
공식 분류와 일대일 대응하지는 않습니다.

## 3. 시스템 구성

### 현재 구현

| 구성 요소 | 역할 |
|---|---|
| retrieval.py | 공통 토큰 개수 기반 문서 검색 |
| gateway.py | 역할별 문서 접근 권한 검사 후 검색 |
| evaluate.py | 동일한 테스트셋으로 방어 전후 비교 및 JSON 보고서 생성 |
| datasets/ | 합성 문서와 검색 평가 테스트셋 |
| tests/ | 접근 제어 및 평가 계산 자동 테스트 |
| GitHub Actions | push 및 pull request 발생 시 자동 테스트 |

기본 검색 경로는 방어 전 비교를 위해 접근 제어 없이 동작합니다.
보호된 검색 경로는 접근 가능한 문서만 선별한 뒤 검색합니다.

### 최종 구현 예정

테스트 실행기에서 Security Gateway와 RAG 애플리케이션을 호출하고,
검색된 문서를 바탕으로 LLM이 답변을 생성하도록 구성할 예정입니다.

평가 모듈은 검색 결과와 생성 답변을 검사해
공격 성공 여부, 정상 동작 유지 여부 및 판정 근거를 기록합니다.

## 4. 개발 환경

- Windows CMD
- Python 3.12
- Git
- GitHub CLI
- GitHub Actions: Ubuntu / Python 3.12

현재 애플리케이션 코드는 Python 표준 라이브러리를 사용합니다.
외부 LLM API나 API 키 없이 현재 구현 기능을 실행할 수 있습니다.

## 5. 설치

Windows CMD에서 실행합니다.

```bat
git clone https://github.com/kjm0320/rag-security-lab.git
cd rag-security-lab
python -m venv .venv
.venv\Scripts\activate.bat
python -m pip install -e .
```

이미 저장소와 가상환경이 있다면 프로젝트 루트에서 실행합니다.

```bat
.venv\Scripts\activate.bat
python -m pip install -e .
```

아래 실행 명령어는 모두 프로젝트 루트를 기준으로 합니다.

## 6. 문서 검색

### 기본 검색 — 접근 제어 미적용

```bat
python -m rag_security_lab.retrieval "비밀번호 변경"
python -m rag_security_lab.retrieval "VPN"
python -m rag_security_lab.retrieval "관리자 복구"
```

기본 검색은 문서의 접근 등급을 검사하지 않습니다.
따라서 `관리자 복구`를 검색하면 제한 문서인 `doc-003`이 반환됩니다.

검색 점수는 질문과 문서에 공통으로 등장한 서로 다른 토큰의 개수입니다.
의미 유사도나 보안 점수가 아닙니다.

### 접근 제어 적용 검색

일반 사용자:

```bat
python -m rag_security_lab.gateway "관리자 복구" --role user
```

예상 결과:

```text
접근 가능한 검색 결과가 없습니다.
```

관리자:

```bat
python -m rag_security_lab.gateway "관리자 복구" --role admin
```

관리자는 제한 문서인 `doc-003`을 검색할 수 있습니다.

### 접근 제어 정책

| 역할 | 검색 가능한 문서 등급 |
|---|---|
| user | public |
| admin | public, restricted |

- 접근 등급이 누락되거나 알 수 없는 문서는 제외합니다.
- 지원하지 않는 역할은 거부합니다.
- 권한 필터는 검색과 상위 결과 선택 전에 적용합니다.
- 질문에 관리자라고 주장하는 문장을 넣어도 역할은 변경되지 않습니다.

`--role`은 실습용 역할 선택 옵션이며 사용자 인증 기능이 아닙니다.
서비스에서는 인증된 사용자 정보를 바탕으로 서버가 역할을 결정해야 합니다.
문서의 접근 등급 역시 신뢰할 수 있는 경로에서 관리해야 합니다.

## 7. 검색 접근 제어 비교 실험

### 실행 방법

```bat
python -m rag_security_lab.evaluate
```

보고서는 다음 경로에 저장됩니다.

```text
reports/retrieval_comparison.json
```

같은 경로로 다시 실행하면 이전 보고서를 덮어씁니다.
별도 파일로 저장하려면 출력 경로를 지정합니다.

```bat
python -m rag_security_lab.evaluate --output reports/experiment_02.json
```

보고서를 확인하려면:

```bat
notepad reports\retrieval_comparison.json
```

### 실험 조건

| 항목 | 설정 |
|---|---|
| 검색 방식 | 공통 토큰 개수 기반 키워드 검색 |
| 검색 결과 수 | 최대 3개 |
| 실습 문서 | 공개 문서 2개, 제한 문서 1개 |
| 정상 검색 테스트 | 3개 |
| 비인가 접근 테스트 | 2개 |
| baseline | 접근 제어 미적용 |
| protected | 역할별 문서 필터를 검색 전에 적용 |

두 모드에 동일한 문서와 테스트셋을 사용합니다.

### 테스트셋 구성

| ID | 유형 | 역할 | 검증 내용 |
|---|---|---|---|
| normal-001 | 정상 | user | 비밀번호 정책 검색 |
| normal-002 | 정상 | user | VPN 안내 검색 |
| normal-003 | 정상 | admin | 관리자에게 제한 문서 검색 허용 |
| attack-001 | 공격 | user | 일반 사용자의 제한 문서 검색 시도 |
| attack-002 | 공격 | user | 질문에서 관리자라고 주장하며 제한 문서 검색 시도 |

각 테스트에는 기대 문서 ID와 금지 문서 ID가 기록되어 있습니다.
질문 속 관리자 주장은 역할 값을 변경하지 않습니다.

### 실행 결과

| 지표 | baseline | protected |
|---|---:|---:|
| 비인가 문서 노출 | 2/2 (100%) | 0/2 (0%) |
| 정상 검색 통과 | 3/3 (100%) | 3/3 (100%) |

예상 콘솔 출력:

```text
[baseline]
  비인가 문서 노출: 2/2
  정상 검색 통과: 3/3
[protected]
  비인가 문서 노출: 0/2
  정상 검색 통과: 3/3

보고서 저장: reports\retrieval_comparison.json
```

### 지표 정의

**비인가 문서 노출률**

공격 테스트 중 금지 문서가 하나 이상 검색된 사례의 비율입니다.

**정상 검색 통과율**

정상 테스트에서 반환된 문서 ID 집합이
기대 문서 ID 집합과 정확히 일치한 사례의 비율입니다.
결과 순서는 평가하지 않습니다.

해당 유형의 테스트가 없으면 비율은 `0`이 아닌 `null`로 기록합니다.
JSON 보고서의 비율 값은 0부터 1 사이입니다.

### 보고서 구성

- 보고서 스키마 버전
- 평가 범위 및 UTC 실행 시각
- 검색 방식과 최대 결과 수
- 입력 문서와 테스트셋의 경로 및 내용
- 모드별 요약 지표
- 케이스별 기대 문서, 금지 문서, 실제 검색 문서
- 노출된 금지 문서와 기대 결과 일치 여부

생성 보고서는 기본적으로 Git 추적에서 제외합니다.
공개할 실험 결과는 검토 후 README 또는 docs/에 정리합니다.

### 결과 해석

이번 테스트셋에서는 접근 제어 적용 후 제한 문서 노출이 차단됐고,
정상 검색 결과는 유지됐습니다.

이는 소규모 합성 데이터에서 수행한 검색 단계의 접근 제어 실험입니다.
LLM 응답 유출, 프롬프트 인젝션 방어 성능이나
실제 서비스 전체의 안전성을 평가한 결과는 아닙니다.

정상 검색 통과율 역시 생성 답변의 품질을 의미하지 않습니다.

## 8. 자동 테스트

```bat
python -m unittest discover -s tests -v
```

현재 자동 테스트는 총 13개입니다.

| 테스트 파일 | 개수 | 주요 검증 내용 |
|---|---:|---|
| test_gateway.py | 7 | 제한 문서 차단, 관리자 접근, 공개 문서 검색 유지, 잘못된 역할 및 접근 등급 처리 |
| test_evaluate.py | 6 | 노출 판정 근거, 방어 전후 지표, 정상 검색 실패 집계, 분모가 0인 경우 및 잘못된 입력 처리 |

GitHub Actions는 push와 pull request 발생 시 프로젝트를 설치하고
동일한 자동 테스트 명령어를 실행합니다.
수동 실행도 지원합니다.

실행 결과는 저장소의 Actions 탭 또는 다음 명령어로 확인합니다.

```bat
gh run list --workflow tests.yml --limit 3
```

## 9. 주요 파일

| 경로 | 용도 |
|---|---|
| src/rag_security_lab/retrieval.py | 기본 문서 검색 |
| src/rag_security_lab/gateway.py | 접근 제어가 적용된 검색 |
| src/rag_security_lab/evaluate.py | 비교 평가 및 JSON 보고서 생성 |
| datasets/documents.json | 합성 실습 문서 |
| datasets/retrieval_cases.json | 검색 평가 테스트셋 |
| tests/test_gateway.py | 접근 제어 테스트 |
| tests/test_evaluate.py | 평가 계산 테스트 |
| .github/workflows/tests.yml | GitHub Actions 워크플로 |
| pyproject.toml | Python 패키지 설정 |
| reports/ | 생성 보고서 저장 위치 |
| docs/ | 향후 설계와 실험 문서 저장 위치 |

빈 디렉터리는 Git에 기록되지 않으므로,
docs/는 문서를 추가하기 전까지 복제한 저장소에 없을 수 있습니다.

## 10. 현재 한계

- 키워드 검색만 구현했으며 벡터 검색과 RAG DB는 아직 연결하지 않았습니다.
- 한국어 형태소 분석을 지원하지 않아 조사에 따라 검색 결과가 달라질 수 있습니다.
- LLM 연동과 생성 답변 평가는 아직 구현하지 않았습니다.
- 역할은 CLI에서 지정하며 실제 사용자 인증은 구현하지 않았습니다.
- 기본 검색 모듈은 비교 실험을 위해 접근 제어 없이 동작합니다.
- 테스트셋 규모가 작아 다양한 공격과 질문을 대표하지 못합니다.
- 현재 보고서는 검색 접근 제어만 평가하며 종합 보안 점수는 산출하지 않습니다.

## 11. 진행 상태

- [x] 로컬 개발 환경 준비
- [x] GitHub 공개 저장소 연결
- [x] 키워드 기반 문서 검색 구현
- [x] 검색 전 역할별 접근 제어 구현
- [x] 검색 접근 제어 테스트셋 구성
- [x] 방어 전후 비교 및 JSON 보고서 구현
- [x] 접근 제어 및 평가 계산 자동 테스트 13개 구현
- [x] GitHub Actions 자동 테스트 연결
- [ ] LLM 연동 및 문서 기반 답변 생성
- [ ] 벡터 검색 및 RAG DB 연결
- [ ] 전체 보안 테스트 영역의 공격 테스트셋 및 자동 평가 구현
- [ ] Security Gateway 방어 기능 확장
- [ ] 정상 답변 품질 및 과잉 차단 평가
- [ ] 종합 보고서와 자체 보안 점수 구현
- [ ] OWASP GenAI 위험 분류와 테스트 항목 연결

## 12. 실험 데이터 원칙

직접 구성한 실습 환경과 합성 데이터를 사용합니다.

- 문서의 복구 코드는 실습용 가짜 값입니다.
- 실제 비밀키와 개인정보를 테스트 데이터나 저장소에 포함하지 않습니다.
- `.env` 파일과 가상환경은 Git 추적에서 제외합니다.
- 보고서에 입력 문서가 포함되므로 공개 전 내용을 검토합니다.