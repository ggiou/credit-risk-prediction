"""FastAPI 내부 예측 계약과 부분 실패 응답을 검증한다."""

from pathlib import Path

from fastapi.testclient import TestClient

from app.api.prediction import get_explanation_service, get_model_service
from app.core.config import Settings, get_settings
from app.main import app
from app.services.explanation_service import ExplanationService
from app.services.model_service import ModelService


def test_prediction_keeps_risk_when_llm_is_not_configured(tmp_path: Path) -> None:
    """LLM 설정이 없어도 개발용 위험률은 유지하고 FAILED 상태를 반환한다."""

    settings = Settings(
        model_path=tmp_path / "missing-model.txt",
        feature_order_path=tmp_path / "missing-order.json",
        allow_rule_based_fallback=True,
        openai_api_key=None,
        openai_model=None,
    )
    app.dependency_overrides[get_settings] = lambda: settings
    app.dependency_overrides[get_model_service] = lambda: ModelService(settings)
    app.dependency_overrides[get_explanation_service] = lambda: ExplanationService(settings)
    client = TestClient(app)

    response = client.post(
        "/internal/v1/predictions",
        json={
            "requestId": "test-request",
            "customerId": "SYN_123",
            "baseYm": "201812",
            "featureSnapshotId": 1,
            "previousFeatureSnapshotId": None,
            "featureSchemaVersion": "v1",
            "expectedModelVersion": "miribom-lgbm-v0.3",
            "promptVersion": "v1.0",
            "generateExplanation": True,
            "currentFeatures": {
                "카드이용한도금액": 1_000_000,
                "잔액_B0M": 500_000,
                "잔액_현금서비스_B0M": 100_000,
                "잔액_카드론_B0M": 100_000,
                "잔액_리볼빙일시불이월_B0M": 50_000,
            },
            "previousFeatures": None,
        },
    )

    # 테스트 이후 다른 테스트에 의존성 재정의가 남지 않도록 즉시 정리한다.
    app.dependency_overrides.clear()
    assert response.status_code == 200
    body = response.json()
    assert 0 <= body["prediction"]["hazard1m"] <= body["prediction"]["hazard3m"] <= 1
    assert body["llm"]["status"] == "FAILED"
    assert body["explanation"] is None

