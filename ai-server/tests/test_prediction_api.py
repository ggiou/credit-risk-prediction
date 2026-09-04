from fastapi.testclient import TestClient

from app.main import app
from app.main import get_model


def test_prediction_uses_json_model_and_preserves_legacy_percentile_field():
    client = TestClient(app)
    response = client.post(
        "/internal/v1/predictions",
        json={
            "requestId": "test-request",
            "customerId": "SYN_TEST",
            "baseYm": "201812",
            "featureSnapshotId": 1,
            "featureSchemaVersion": "v1",
            "expectedModelVersion": "miribom-lgbm-v0.3",
                "promptVersion": "v3.1",
            "generateExplanation": False,
            "currentFeatures": {"연령": "40대", "Life_Stage": "4.자녀성장기(1)"},
            "previousFeatures": None,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["predictionSource"] == "LIGHTGBM_JSON"
    assert body["prediction"]["topRiskPercent"] == body["prediction"]["percentile"]
    assert body["llm"]["status"] == "NOT_REQUESTED"
    assert body["llmOutput"] is None
    assert body["recommendation"] is None


def test_llm_failure_keeps_json_model_prediction_and_counterfactual_reasons():
    model = get_model()
    current = {name: 0 for name in model.features[:36]}
    previous = dict(current)
    current.update({
        "연령": "40대", "Life_Stage": "4.자녀성장기(1)",
        "이용가능카드수_신용": 1, "유효카드수_신용": 2,
    })
    previous.update({
        "연령": "40대", "Life_Stage": "4.자녀성장기(1)",
        "이용가능카드수_신용": 2, "유효카드수_신용": 2,
    })
    response = TestClient(app).post(
        "/internal/v1/predictions",
        json={
            "requestId": "llm-failure",
            "customerId": "SYN_TEST",
            "baseYm": "201812",
            "featureSnapshotId": 2,
            "previousFeatureSnapshotId": 1,
            "featureSchemaVersion": "v1",
            "expectedModelVersion": "miribom-lgbm-v0.3",
                "promptVersion": "v3.1",
            "generateExplanation": True,
            "currentFeatures": current,
            "previousFeatures": previous,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["llm"]["status"] == "FAILED"
    assert body["predictionSource"] == "LIGHTGBM_JSON"
    assert body["riskFactors"]
    assert body["riskFactors"][0]["reasonMethod"] == "PREVIOUS_VALUE_COUNTERFACTUAL"
    assert body["llmOutput"] is None
    assert body["explanation"] is None
    assert body["recommendation"] is None
