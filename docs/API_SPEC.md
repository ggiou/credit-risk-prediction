# API 요약

모든 화면용 API는 `/api/v1`, Spring Boot 전용 AI API는 `/internal/v1`을 사용한다.

## BO 화면용 API

| 기능 | 메서드 | 경로 |
| --- | --- | --- |
| 기준년월 목록 | GET | `/api/v1/meta/base-months` |
| 대시보드 | GET | `/api/v1/dashboard` |
| 고객 목록 | GET | `/api/v1/customers` |
| 고객 요약 | GET | `/api/v1/customers/{customerId}/summary` |
| 카드 이용 | GET | `/api/v1/customers/{customerId}/financials/card-usage` |
| 청구 | GET | `/api/v1/customers/{customerId}/financials/billing` |
| 신용 | GET | `/api/v1/customers/{customerId}/financials/credit` |
| 잔액 | GET | `/api/v1/customers/{customerId}/financials/balance` |
| 예측 실행 | POST | `/api/v1/customers/{customerId}/predictions` |
| 현재 예측 | GET | `/api/v1/customers/{customerId}/predictions/current` |
| 예측 상세 | GET | `/api/v1/predictions/{predictionId}` |
| 예측 이력 | GET | `/api/v1/predictions` |

### 예측 실행 요청

```json
{
  "baseYm": "201812",
  "generateExplanation": true
}
```

- 동일 모델·피처·프롬프트·설명 생성 조건의 `inputHash`가 있으면 기존 결과를 반환한다.
- LightGBM 성공 후 LLM만 실패하면 위험률을 저장하고 `analysisStatus=PARTIAL`로 반환한다.
- 권고 조치, 이메일 알림, 사용자 권한, 모델 학습·배포 기능은 MVP 범위에서 제외한다.

## FastAPI 내부 API

| 기능 | 메서드 | 경로 |
| --- | --- | --- |
| 상태 확인 | GET | `/internal/v1/health` |
| 위험 예측 및 설명 | POST | `/internal/v1/predictions` |

Spring은 현재·이전 월 피처와 예상 모델 버전을 전달한다. FastAPI는 파생 피처 11개를 계산하고
`horizon=1, 2, 3`으로 추론한 뒤 주요 요인과 LLM 설명 상태를 반환한다.

