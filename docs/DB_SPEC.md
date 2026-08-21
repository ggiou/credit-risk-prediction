# DB 구현 기준

구현 DDL은 [`../database/schema.sql`](../database/schema.sql), 로컬 확인용 데이터는
[`../database/sample-data.sql`](../database/sample-data.sql)을 사용한다.

- 운영 기준: MySQL 8.4, 데이터베이스 `credit_risk`
- 기준년월: `YYYYMM`
- 원천 스냅샷: 회원, 신용, 청구, 잔액
- 모델 입력: `feature_snapshot.features` JSON
- 예측 결과: 1개월, 2개월, 3개월 위험률과 LLM 설명
- 학습 정답 컬럼은 BO 조회 API와 FastAPI 입력에서 제외한다.
- `recommendation`은 기존 호환을 위해 컬럼만 유지하고 MVP에서는 사용하지 않는다.

