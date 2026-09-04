import math
from pathlib import Path

import pytest

from app.model_bundle import ModelBundle, ModelContractError


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
    current["Life_Stage"] = "2.가족형성기"

    prediction, enriched = model.predict(current, None)

    assert prediction.hazard_1m < 0.5
    assert prediction.hazard_2m < 0.5
    assert prediction.hazard_3m > 0.5
    assert enriched["horizon"] == 3


def test_grade_and_percentile_follow_cumulative_risk_contract():
    payload = make_payload()
    probability = 0.02
    leaf = math.log(probability / (1.0 - probability))
    payload["trees"] = [[36, 0, 2.5, 1, 0, leaf, leaf]]
    payload["c3_quantiles"] = [0.01, 0.03, 0.05, 0.07, 0.09]
    model = ModelBundle(payload, source_sha256="test")
    current = {name: 1.0 for name in payload["features"][:36]}
    current["연령"] = "30대"
    current["Life_Stage"] = "2.가족형성기"

    prediction, _ = model.predict(current, None)

    assert prediction.hazard_3m == probability
    assert prediction.cumulative_risk_3m > payload["grade_thresholds"]["관심"]
    assert prediction.risk_grade == "INTEREST"
    assert prediction.percentile == 50.0


def test_grade_boundaries_and_top_risk_direction_are_exact():
    model = ModelBundle(make_payload(), source_sha256="test")

    assert model._risk_grade(0.029999999999) == "NORMAL"
    assert model._risk_grade(0.03) == "INTEREST"
    assert model._risk_grade(0.08) == "CAUTION"
    assert model._risk_grade(0.15) == "WARNING"
    assert model._percentile(0.9) < model._percentile(0.1)


def test_categories_follow_model_code_order_and_unknown_category_is_rejected():
    model = ModelBundle.from_path(Path(__file__).parents[1] / "models" / "model_lgbm.json")
    current = {name: 0 for name in model.features[:36]}
    current["연령"] = "40대"
    current["Life_Stage"] = "4.자녀성장기(1)"

    vector, _ = model._vector(current, None, 1)

    assert vector[model.features.index("연령")] == 2
    assert vector[model.features.index("Life_Stage")] == 3
    current["연령"] = "10대"
    with pytest.raises(ModelContractError, match="unsupported category for 연령"):
        model._vector(current, None, 1)


def test_counterfactual_recomputes_related_features_without_fake_contribution():
    model = ModelBundle.from_path(Path(__file__).parents[1] / "models" / "model_lgbm.json")
    current = {name: 0 for name in model.features[:36]}
    previous = dict(current)
    current.update({"연령": "40대", "Life_Stage": "4.자녀성장기(1)", "잔액_B0M": 200.0, "카드이용한도금액": 1000.0})
    previous.update({"연령": "40대", "Life_Stage": "4.자녀성장기(1)", "잔액_B0M": 100.0, "카드이용한도금액": 1000.0})
    _, enriched = model.predict(current, previous)

    reasons = model.risk_factors(current, previous, enriched)

    balance_reason = next(reason for reason in reasons if reason["featureKey"] == "잔액_B0M")
    assert balance_reason["reasonMethod"] == "PREVIOUS_VALUE_COUNTERFACTUAL"
    assert "f_사용률" in balance_reason["evidenceFeatureKeys"]
    assert "f_잔액증가율" in balance_reason["evidenceFeatureKeys"]
    assert balance_reason["patternCode"] == "BALANCE_EXPOSURE"
    assert balance_reason["currentTopRiskPercent"] >= 0
    assert balance_reason["topRiskPercentDifference"] == round(abs(
        balance_reason["currentTopRiskPercent"] - balance_reason["counterfactualTopRiskPercent"]
    ), 4)
    assert balance_reason["counterfactualRiskDirection"] in {
        "CURRENT_MORE_RISKY", "CURRENT_LESS_RISKY"
    }
    assert "contribution" not in balance_reason
    assert all(reason["featureKey"] != "horizon" for reason in reasons)
