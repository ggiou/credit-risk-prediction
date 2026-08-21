import json

from app.model_bundle import ModelBundle


def make_payload():
    features = [f"f{i}" for i in range(48)]
    features[0] = "연령"
    features[1] = "Life_Stage"
    features[36] = "horizon"
    # Keep all derived names in the expected positions so the runtime can populate them.
    derived = [
        "f_사용률",
        "f_현금서비스비중",
        "f_카드론비중",
        "f_리볼빙비중",
        "f_현금서비스증가",
        "f_카드론증가",
        "f_한도변화",
        "f_잔액증가율",
        "f_사용률변화",
        "f_청구금액증가",
        "f_카드가용비율",
    ]
    features[37:] = derived
    # Numeric horizon split: h1/h2 -> left (-1), h3 -> right (+1).
    return {
        "model_version": "test-v1",
        "objective": "binary-sigmoid",
        "features": features,
        "horizon_index": 36,
        "cat_features": {
            "연령": ["20대", "30대"],
            "Life_Stage": ["1.Single", "2.가족형성기"],
        },
        "grade_thresholds": {"관심": 0.03, "주의": 0.08, "경고": 0.15},
        "c3_quantiles": [0.1, 0.5, 0.9],
        "trees": [[36, 0, 2.5, 1, 0, -1.0, 1.0]],
    }


def test_compact_model_executes_without_retraining():
    payload = make_payload()
    model = ModelBundle(payload, source_sha256="test")
    current = {name: 1.0 for name in payload["features"][:36]}
    current["연령"] = "30대"
    current["Life_Stage"] = "가족형성기"

    prediction, contributions, enriched = model.predict(current, None)

    assert prediction.hazard_1m < 0.5
    assert prediction.hazard_2m < 0.5
    assert prediction.hazard_3m > 0.5
    assert "horizon" in contributions
    assert enriched["horizon"] == 3
