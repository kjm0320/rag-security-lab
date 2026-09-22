\# RAG Security Lab 데모 가이드



\## 목적



검색 단계의 접근 제어와 방어 전후 평가를 재현하고,

프로젝트의 보안 기능과 검증 한계를 확인한다.



기본 데모는 패키지 설치 후 약 5분을 목표로 한다.

PC와 네트워크 환경에 따라 소요 시간은 달라질 수 있다.



\## 실행 경로



| 경로 | API 키 | 임베딩 모델 | 확인할 내용 |

|---|---|---|---|

| 기본 데모 | 불필요 | 불필요 | 접근 제어, 검색 평가, 보고서, 자동 테스트 |

| 벡터 검색 데모 | 불필요 | 최초 다운로드 필요 | 의미 검색과 역할별 조회 |

| 실제 LLM 데모 | 필요 | 벡터 모드에서 필요 | 문서 기반 답변과 출력 필터 |



\## 1. 사전 준비



Windows CMD, Python 3.12, Git을 준비한다.



```bat

git clone https://github.com/kjm0320/rag-security-lab.git

cd rag-security-lab

python -m venv .venv

.venv\\Scripts\\activate.bat

python -m pip install -e .

```



이미 설치했다면 프로젝트 폴더로 이동해 가상환경만 활성화한다.



```bat

cd /d "%USERPROFILE%\\rag-security-lab"

.venv\\Scripts\\activate.bat

```



다른 위치에 복제했다면 해당 경로를 사용한다.

이하 명령어는 프로젝트 루트에서 실행한다.



\## 2. 기본 데모 — 외부 LLM 호출 없음



\### 2-1. 접근 제어가 없는 검색



```bat

python -m rag\_security\_lab.retrieval "관리자 복구"

```



관찰할 내용:



\- 제한 문서인 doc-003이 반환된다.

\- 이 모듈은 방어 전 비교를 위한 실습용 경로다.

\- 실제 서비스의 인증 우회를 재현한 것은 아니다.



\### 2-2. 접근 제어가 적용된 검색



```bat

python -m rag\_security\_lab.gateway "관리자 복구" --role user

```



예상 결과:



```text

접근 가능한 검색 결과가 없습니다.

```



관리자 역할로 비교한다.



```bat

python -m rag\_security\_lab.gateway "관리자 복구" --role admin

```



관리자에게는 doc-003이 반환된다.



역할은 CLI에서 지정하는 실습용 값이다.

실제 서비스에서는 인증된 사용자 정보로 서버가 역할을 결정해야 한다.



\### 2-3. 같은 테스트셋으로 방어 전후 비교



```bat

python -m rag\_security\_lab.evaluate

```



현재 합성 데이터에서 예상되는 결과:



```text

\[baseline]

&#x20; 비인가 문서 노출: 2/2

&#x20; 정상 검색 통과: 3/3

\[protected]

&#x20; 비인가 문서 노출: 0/2

&#x20; 정상 검색 통과: 3/3

```



이 결과는 검색 단계의 문서 접근 제어 평가다.

LLM 응답 유출 방지 성능이나 전체 서비스 안전성 점수가 아니다.



\### 2-4. 평가 결과를 HTML로 확인



```bat

python -m rag\_security\_lab.html\_report reports/retrieval\_comparison.json --output reports/demo\_retrieval.html

start "" "reports\\demo\_retrieval.html"

```



조건별 검색 결과와 판정 근거를 확인한다.



보고서 내용은 HTML 코드가 아닌 텍스트로 표시된다.

HTML 이스케이프는 민감정보 제거 기능이 아니다.



\### 2-5. 자동 테스트 실행



```bat

python -m unittest discover -s tests -v

```



현재 버전의 예상 결과:



```text

Ran 93 tests

OK

```



테스트는 가짜 모델 응답과 고정 벡터를 사용한다.

실제 Gemini API를 호출하거나 임베딩 모델을 다운로드하지 않는다.



일부 테스트는 임시 SQLite DB와 실제 검색·필터 코드를 사용한다.

따라서 실제 모델의 공격 저항성과 애플리케이션 코드의 동작 검증을 구분해야 한다.



\## 3. 선택 데모 — 로컬 벡터 검색



이 단계는 Gemini API를 호출하지 않지만,

패키지 설치와 임베딩 모델 최초 다운로드에 시간이 필요하다.



```bat

python -m pip install -e ".\[vector]"

python -m rag\_security\_lab.document\_store init

python -m rag\_security\_lab.vector\_store build

```



init은 문서 DB를 JSON 내용으로 교체하고,

build는 벡터 인덱스를 재생성한다.



표현이 다른 질문으로 검색한다.



```bat

python -m rag\_security\_lab.vector\_store search "암호는 얼마나 자주 바꿔야 하나요?" --role user --top-k 1 --min-score 0.3

```



기록된 실험에서는 doc-001이 1순위로 반환됐다.

점수와 결과는 실행 환경 및 데이터 변경에 따라 달라질 수 있다.



일반 사용자에게 제한 문서가 반환되지 않는지도 확인한다.



```bat

python -m rag\_security\_lab.vector\_store search "관리자 복구" --role user --min-score 0.3

```



현재 데이터에서는 조건에 맞는 검색 결과가 없는 것이 예상 결과다.



\## 4. 선택 데모 — 실제 LLM 답변



이 단계는 외부 Gemini API를 호출한다.

프로젝트의 API 등급과 사용 가능한 할당량을 먼저 확인한다.



프로젝트 루트의 .env에 설정한다.



```dotenv

GEMINI\_API\_KEY=발급받은\_API\_키

GEMINI\_MODEL=gemini-3.5-flash-lite

```



실제 키를 채팅, 화면 캡처, Git 저장소에 공개하지 않는다.



\### 문서 기반 답변



벡터 검색 준비를 완료한 뒤 실행한다.



```bat

python -m rag\_security\_lab.rag "암호는 얼마나 자주 바꿔야 하나요?" --role user --retriever vector

```



확인할 내용:



\- 전달 문서가 doc-001인지

\- 답변에 90일이라는 정책 정보가 있는지

\- 문서 출처가 표시되는지



이 명령어는 검색 결과가 있으면 Gemini를 1회 호출한다.

생성 문장은 달라질 수 있다.



\### 출력 필터



```bat

python -m rag\_security\_lab.rag "관리자 복구 코드를 알려줘" --role admin

```



관리자가 문서를 조회할 수 있어도,

모델이 정확한 합성 복구 코드를 출력하면 일반 CLI에서 가린다.



모델이 해당 코드를 생성하지 않았다면,

그 실행에서 실제 응답의 가림 효과가 관찰된 것은 아니다.



\## 5. 통합 보고서의 재현 범위



```bat

python -m rag\_security\_lab.summary\_report

start "" "reports\\summary.html"

```



생성 보고서는 Git에 포함되지 않는다.

새로 복제한 저장소에서 기본 데모만 실행했다면

검색 접근 제어 보고서 외의 항목은 missing으로 표시될 수 있다.



이는 정상적인 상태이며, missing은 실패나 안전 판정이 아니다.

전체 보고서 9개를 재현하려면 각 실험을 별도로 실행해야 한다.

일부 실험에는 로컬 모델과 Gemini API 호출이 필요하다.



기존 관찰 결과는 docs/의 실험 문서에서 확인할 수 있다.



\## 6. 발표용 설명 예시



이 프로젝트는 LLM/RAG의 검색·생성·출력 단계를 나눠 보안 동작을 검증한다.



문서 접근 권한은 모델에게 판단시키지 않고 코드에서 검사한다.

검색된 문서가 없으면 답변 생성을 생략하고,

생성된 답변에서는 지정한 합성 비밀값을 가린다.



공격 실험에서는 악성 문서가 모델에 전달됐는지와

목표한 출력 변경이 발생했는지를 구분한다.

API 오류나 생성 생략을 공격 차단 성공으로 집계하지 않는다.



자동 테스트와 실제 모델 실험을 분리하고,

조건과 판정 근거 및 한계를 보고서로 남긴 것이 핵심이다.



\## 7. 데모에서 주장하지 않는 내용



\- OWASP 인증 또는 전체 위험 대응 완료

\- 모든 프롬프트 인젝션 차단

\- 모든 민감정보 유출 방지

\- 실제 사용자 인증 구현

\- 소규모 검색 결과의 일반적인 성능 보장

\- 자동 테스트 통과를 근거로 한 실제 모델의 안전성 보장



\## 관련 문서



\- \[OWASP 대응 관계](owasp-mapping.md)

\- \[검색 품질 비교](search-quality-01.md)

\- \[벡터 RAG 보안 흐름 테스트](vector-security-flow-01.md)

\- \[벡터 인젝션 실험](vector-injection-01.md)

