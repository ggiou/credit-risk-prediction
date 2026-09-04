# DB 구현 기준

구현 DDL은 [`../database/schema.sql`](../database/schema.sql), 로컬 확인용 데이터는
[`../database/sample-data.sql`](../database/sample-data.sql)을 사용한다.

- 운영 기준: MySQL 8.4, 데이터베이스 `credit_risk`
- 기준년월: `YYYYMM`
- 원천 스냅샷: 회원, 신용, 청구, 잔액
- 모델 입력: `feature_snapshot.features` JSON
- 예측 결과: 1개월, 2개월, 3개월 위험률과 LLM 설명
- 학습 정답 컬럼은 BO 조회 API와 FastAPI 입력에서 제외한다.
- `reasons`에는 모델이 산출한 근거만 저장하고 담당자 확인 사항을 섞지 않는다.
- `explanation`은 구조화된 LLM 결과 중 요약·주요 관찰 지표·모델 해석·변화 맥락을 조합한 화면 호환 문자열이다.
- `recommendation`은 `reviewPoints`를 우선순위 문자열로 렌더링한 기존 화면 호환 값이다.
- `llm_output`은 검증이 끝난 LLM 구조화 JSON 원본이며 기존 행과 LLM 실패 행은 `NULL`을 허용한다.
- `llm_output.keyIndicators`, `managementPriority`, `generationMode`는 기존 JSON 컬럼 안에서 확장하며 새 테이블이나 컬럼을 만들지 않는다.
