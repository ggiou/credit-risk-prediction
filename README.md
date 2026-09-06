# AI 신용카드 연체 위험 조기예측

금융회사 BO 직원이 고객의 카드 이용·청구·신용·잔액 변화를 확인하고, LightGBM이 계산한
향후 1개월·2개월·3개월 연체 위험률과 주요 위험 요인을 조회하는 공모전 MVP다.

## 구성

```text
credit_risk_prediction/
├─ spring-app/       Spring Boot, JSP, JavaScript, MyBatis
├─ ai-server/        FastAPI, LightGBM, OpenAI 설명
├─ database/         MySQL DDL과 합성 샘플 데이터
├─ docs/             API·DB 구현 기준
└─ docker-compose.yml
```

## 화면

- 대시보드: 분석 대상, 고위험, 위험도 상승, 완료율, 위험 분포
- 고객 목록: 고객번호, 위험등급, 분석 상태 검색
- 고객 상세: 고객 요약, 카드 이용, 청구, 신용, 잔액
- AI 분석: 기간별 위험률, 주요 위험 요인, LLM 설명
- 예측 이력: 전체 또는 특정 고객의 과거 결과

## 빠른 실행

Docker가 설치된 환경에서 다음 명령을 실행한다.

```bash
docker compose up --build
```

- BO 화면: `http://localhost:8080`
- FastAPI 내부 문서: `http://localhost:8000/internal/docs`
- MySQL: `localhost:3306`, 데이터베이스 `credit_risk`

FastAPI는 전달된 JSON 모델만 실행하며 규칙 기반 대체 점수를 생성하지 않는다. 실제 실행 전
아래 파일을 배치한다.

```text
ai-server/models/model_lgbm.json
```

LLM 설명을 사용하려면 저장소에 키를 기록하지 말고 환경변수로 전달한다.

```bash
export OPENAI_API_KEY="..."
export OPENAI_MODEL="..."
export AI_LLM_TIMEOUT_SECONDS="60"
export AI_READ_TIMEOUT_SECONDS="75"
docker compose up --build
```

## 개별 실행

Spring Boot는 Java 17과 Gradle 8 이상을 사용한다.

```bash
gradle :spring-app:bootRun
```

FastAPI는 Python 3.11 기준이다.

```bash
cd ai-server
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

## 관리자 다건 AI 분석

일반 대시보드 메뉴에는 다건 분석 화면을 노출하지 않는다. 관리자는 `/admin/prediction-batches`에 직접 접근한 뒤 `config/application-secret.yml`에 설정한 별도 계정으로 로그인한다.

```yaml
admin:
  batch:
    email: "admin@example.com"
    password: "CHANGE_ME"
```

관리자 세션이 없는 `/api/v1/admin/prediction-batches/**` 요청은 `401`로 차단된다. 한 요청에서 최대 50명을 처리하고 AI 호출 동시성은 기본 2개로 제한한다. 다건 작업의 진행 상태는 서버 메모리에서만 관리하며, 고객별 최종 예측 결과만 기존 `prediction_result` 저장 흐름을 사용한다.

## 실패 처리 기준

- 피처 스냅샷 없음: `FEATURE_SNAPSHOT_NOT_FOUND`
- LightGBM 모델 미탑재: FastAPI `503 MODEL_NOT_LOADED`
- AI 서버 연결·타임아웃: `AI_SERVER_TIMEOUT`
- AI 응답 버전·위험률 오류: `AI_SERVER_INVALID_RESPONSE`
- LLM 실패: 위험률은 저장하고 `llmStatus=FAILED`, `analysisStatus=PARTIAL`

실패 원인을 성공값이나 임의의 0으로 바꾸지 않는다. 세부 오류와 인증 정보는 사용자 응답에 노출하지 않는다.
AI 오류는 Spring의 SLF4J 로그와 FastAPI의 Python 표준 로그에 요청 ID·고객번호·기준월을 포함해 기록한다.
API 키, 전체 피처 JSON, LLM 요청·응답 원문은 오류 로그에 기록하지 않는다.

## 문서

- [API 요약](docs/API_SPEC.md)
- [DB 구현 기준](docs/DB_SPEC.md)
- [모델 파일 배치](ai-server/models/README.md)
