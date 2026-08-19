# 모델 파일 배치

실제 추론을 실행하려면 다음 파일을 이 디렉터리에 배치한다.

- `miribom-lgbm-v0.3.txt`: LightGBM Booster 모델
- `feature-order.json`: 학습에 사용한 48개 입력 열 순서의 JSON 문자열 배열

모델이 없을 때 API는 `503 MODEL_NOT_LOADED`를 반환한다. 화면과 API 연결만 확인할 때는
`AI_ALLOW_RULE_BASED_FALLBACK=true`를 명시적으로 설정할 수 있다. 이 모드는 실제 모델 성능이나
공모전 결과로 사용하면 안 된다.

