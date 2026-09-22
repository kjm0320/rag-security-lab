\# OWASP LLM Top 10 대응 관계



\- 기준: OWASP Top 10 for LLM Applications 2025

\- 공식 문서 확인일: 2026-09-22

\- 대상: RAG Security Lab의 현재 구현과 기록된 실험



이 문서는 공식 위험 분류를 참고해 프로젝트의 구현 범위를 연결한

자체 분석이다. OWASP의 인증, 준수 판정 또는 전체 취약점 점검 결과가 아니다.



\## 1. 직접 연결되는 실험



| 공식 항목 | 프로젝트 구현 | 현재 증거 | 남은 한계 |

|---|---|---|---|

| LLM01:2025 Prompt Injection | 문서 내 악성 지시 3종 비교, 벡터 검색 경로의 공격 전달 기록 | 키워드 기반 비교 3종 및 벡터 기반 비교 1종에서 목표 출력 변경 미관찰 | 소수 문장·단일 모델·조건별 1회, 다른 공격에 대한 일반화 불가 |

| LLM02:2025 Sensitive Information Disclosure | 지정된 합성 비밀값 출력 필터 | 동일 모델 응답에서 가짜 복구 코드가 가려지고 나머지 정보 유지 | 정확한 문자열만 탐지, 실제 개인정보 탐지와 변형 유출 방어 미구현 |

| LLM05:2025 Improper Output Handling | JSON 보고서 전체의 HTML 이스케이프와 CSP | 파서 검사에서 공격 문자열이 태그가 아닌 텍스트로 보존 | 실제 브라우저 공격 실행 자동 검증 및 다른 출력 문맥 검증 미구현 |

| LLM07:2025 System Prompt Leakage | 자체 시스템 지시문에 합성 표식을 넣고 노출 검사 | 정상·유출 유도 요청에서 정확한 표식 및 전체 지시문 원문 노출 미관찰 | 부분 공개·의역·인코딩 탐지 미구현, 지시문 비공개 보장 아님 |

| LLM08:2025 Vector and Embedding Weaknesses | 검색 전 문서 권한 필터, 벡터 저장·조회, 문서 해시 검사 | 일반 사용자에게 제한 문서 제외, 변경된 문서의 오래된 인덱스 거부 | 사용자 인증·테넌트 격리·임베딩 역추론 방어·운영 환경 검증 미구현 |



\## 2. 구현과 증거 위치



| 공식 항목 | 주요 코드 | 실험 기록 |

|---|---|---|

| LLM01 | compare\_injection.py, vector\_injection.py | \[인젝션 비교](injection-comparison-summary.md), \[벡터 인젝션](vector-injection-01.md) |

| LLM02 | output\_guard.py, disclosure\_demo.py, rag.py | \[출력 필터 실험](disclosure-experiment-01.md) |

| LLM05 | html\_report.py | \[HTML 출력 처리](output-handling-01.md) |

| LLM07 | prompt\_leakage\_demo.py | \[시스템 프롬프트 유출 실험](prompt-leakage-01.md) |

| LLM08 | gateway.py, document\_store.py, vector\_store.py | \[벡터 검색](vector-search-01.md), \[보안 흐름 회귀 테스트](vector-security-flow-01.md) |



코드 파일은 src/rag\_security\_lab/에 있다.

자동 테스트는 tests/에 있다.



\## 3. 분류 해석 시 주의점



\### RAG 데이터 유출은 프로젝트의 실험 명칭



RAG Data Leakage는 2025 Top 10의 독립적인 공식 항목명이 아니다.



이 프로젝트에서는 문서 조회 권한과 벡터 검색 경로를 LLM08에,

민감한 내용의 응답 노출을 LLM02에 연결한다.

하나의 실험이 여러 위험과 관련될 수 있다.



\### 공격 전달과 공격 성공은 다름



공격 문서가 검색되지 않았다면 모델의 공격 거부를 검증한 것이 아니다.



벡터 인젝션 보고서는 다음을 구분한다.



\- 공격 문서 선택 여부

\- 악성 지시의 생성 입력 포함 여부

\- 모델 호출 또는 생성 생략

\- 응답의 목표 마커 포함 여부

\- API 오류와 미실행 조건



공격 전달 후 마커가 없더라도 모든 악성 동작이 없었다는 의미는 아니다.



\### 시스템 지시문은 권한 통제 수단이 아님



합성 내부 표식은 유출 관찰용이다.

실제 키나 기밀정보를 시스템 지시문에 저장하지 않는다.



문서 접근 권한은 모델의 판단이 아니라 Python·SQL 코드로 검사한다.

다만 역할을 CLI 사용자가 선택하므로 실제 사용자 인증은 구현되지 않았다.



시스템 프롬프트 공개 자체와,

그 안에 잘못 저장된 비밀정보 또는 권한 통제 우회의 위험을 구분한다.



\### 출력 필터와 HTML 이스케이프는 목적이 다름



\- 출력 필터: 지정한 합성 비밀값을 응답에서 가린다.

\- HTML 이스케이프: 보고서 내용을 HTML 코드가 아닌 텍스트로 표시한다.



HTML 이스케이프가 개인정보나 비밀값을 제거하지는 않는다.

출력 필터 역시 다른 출력 문맥의 코드 실행을 막는 일반 방어가 아니다.



\### 문서 해시는 신뢰성 인증이 아님



현재 문서 해시는 저장된 벡터와 문서의 변경 여부를 확인한다.

문서 작성자의 신원이나 내용의 진실성을 증명하지 않는다.



악성 문서를 다시 인덱싱하면 새 해시와 벡터가 생성될 수 있으므로,

이 기능을 문서 오염 방지나 서명 검증으로 표현하지 않는다.



\## 4. 관련 요소만 있거나 아직 평가하지 않은 항목



| 공식 항목 | 현재 상태 |

|---|---|

| LLM03:2025 Supply Chain | 일부 패키지 버전을 지정했지만 전체 의존성·모델 무결성·공급망 공격을 평가하지 않음 |

| LLM04:2025 Data and Model Poisoning | 공격 문서 삽입은 관련될 수 있으나, 현재 실험은 간접 인젝션 중심이며 학습·파인튜닝 오염 등은 평가하지 않음 |

| LLM06:2025 Excessive Agency | 현재 모델에 외부 작업 실행 도구를 제공하지 않으며, 에이전트 권한 남용 실험은 수행하지 않음 |

| LLM09:2025 Misinformation | 검색 품질과 소수 답변을 확인했지만 생성 답변의 사실성·인용 정확성을 체계적으로 평가하지 않음 |

| LLM10:2025 Unbounded Consumption | 출력 토큰·타임아웃·요청 시도 수를 제한했지만 서비스 단위 예산·요청률·부하 공격은 평가하지 않음 |



관련 설정이나 코드가 있다는 사실을

해당 항목 전체의 대응 완료로 해석하지 않는다.



\## 5. 결과 표현 원칙



사용하는 표현:



\- 특정 합성 데이터와 조건에서 관찰한 결과

\- 해당 공격 문장이 전달된 뒤 목표 마커 출력이 관찰되지 않음

\- 지정된 문자열에 대한 출력 가림 확인

\- 고정 벡터와 가짜 응답을 사용한 보안 흐름 테스트 통과

\- 실제 모델 실험과 자동 회귀 테스트를 구분



사용하지 않는 표현:



\- OWASP 인증 완료

\- LLM Top 10 전체 방어 완료

\- 모든 프롬프트 인젝션 차단

\- 민감정보 유출 완전 방지

\- 테스트 통과율을 그대로 보안 점수로 환산



현재 종합 보안 점수는 산출하지 않는다.

이 대응 관계 문서 역시 새로운 모델 실험이나 취약점 점검을 수행한 결과는 아니다.



\## 6. 공식 참고 자료



\- \[OWASP LLM Top 10 2025](https://genai.owasp.org/llm-top-10/)

\- \[LLM01 Prompt Injection](https://genai.owasp.org/llmrisk/llm01-prompt-injection/)

\- \[LLM02 Sensitive Information Disclosure](https://genai.owasp.org/llmrisk/llm022025-sensitive-information-disclosure/)

\- \[LLM05 Improper Output Handling](https://genai.owasp.org/llmrisk/llm052025-improper-output-handling/)

\- \[LLM07 System Prompt Leakage](https://genai.owasp.org/llmrisk/llm072025-system-prompt-leakage/)

\- \[LLM08 Vector and Embedding Weaknesses](https://genai.owasp.org/llmrisk/llm082025-vector-and-embedding-weaknesses/)

