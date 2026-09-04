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

- 동일 `featureSnapshotId`와 `modelVersion`의 결과가 있으면 기존 결과를 반환한다.
- LightGBM 성공 후 LLM만 실패하면 위험률을 저장하고 `analysisStatus=PARTIAL`로 반환한다.
- 권고 조치, 이메일 알림, 사용자 권한, 모델 학습·배포 기능은 MVP 범위에서 제외한다.

## FastAPI 내부 API

| 기능 | 메서드 | 경로 |
| --- | --- | --- |
| 상태 확인 | GET | `/internal/v1/health` |
| 위험 예측 및 설명 | POST | `/internal/v1/predictions` |

Spring은 현재·이전 월 피처와 예상 모델 버전을 전달한다. FastAPI는 파생 피처 11개를 계산하고
`horizon=1, 2, 3`으로 추론한 뒤 주요 요인과 LLM 설명 상태를 반환한다.

- `prediction.topRiskPercent`: c3 quantile로 계산한 위험 상위 비율이며 작을수록 위험하다.
- `prediction.percentile`: 기존 소비자를 위해 `topRiskPercent`와 같은 값을 유지하는 호환 필드다.
- `prediction.cumulativeRisk3m`: 등급·상위 위험 비율 계산 및 기존 API 호환용이며 화면/LLM 확률 문장에는 사용하지 않는다.
- `riskFactors`: `PREVIOUS_VALUE_COUNTERFACTUAL` 모델 근거다. 정확한 SHAP 산출물이 없어 `contribution`을 반환하지 않는다.
- `riskFactors.currentTopRiskPercent`, `counterfactualTopRiskPercent`, `topRiskPercentDifference`: 현재 순위와 전월값 반사실 재채점 순위의 결정적 비교값이다. LLM은 이 값을 계산하지 않는다.
- `observedChanges`: 백엔드가 현재·전월 원천 피처로 계산한 변화 사실과 모델 관계다.
- `llmOutput`: 검증 완료된 구조화 설명 원본이다. `summary`, `modelInterpretation`, `keyIndicators`, `changeContext`, `reviewPoints`, `managementPriority`, 출처 ID와 `generationMode`를 포함한다.
- `keyIndicators`: 백엔드가 만든 후보에서 선택된 2~4개 카드다. `fact`와 참조 필드는 후보와 같아야 하며 LLM은 `interpretation`만 작성한다.
- `managementPriority`: 모델 등급에 따라 `ROUTINE_MONITORING`, `ENHANCED_MONITORING`, `PRIORITY_REVIEW`, `URGENT_REVIEW` 중 하나를 백엔드가 결정한다.
- `explanation`, `recommendation`: 기존 소비자를 위해 `llmOutput`을 렌더링한 호환 필드다.
- `llm.promptVersion`: 저장된 설명을 생성한 프롬프트 버전이다.
- `llm.currentPromptVersion`: 서버가 현재 사용하는 프롬프트 버전이다.
- `llm.outdated`: 저장된 설명이 현재 프롬프트보다 오래됐는지 나타낸다. `true`이면 동일 모델 예측을 유지하면서 설명만 갱신할 수 있다.
- `predictionSource`: 현재 운영 런타임에서는 `LIGHTGBM_JSON`이다.

정상 등급이면서 세 월별 위험률이 모두 극히 낮고 차이가 미미하면 `horizonEmphasis=LOW_STABLE`로 처리해 특정 월의 상대적 최대값을 경고처럼 강조하지 않는다. 그 외에는 실제 hazard 최댓값에 따른 `PEAK` 시점을 사용한다.
