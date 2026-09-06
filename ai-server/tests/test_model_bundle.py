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


def test_nan_missing_split_does_not_treat_zero_as_missing():
    payload = make_payload()
    # missingType=1 means only NaN/null is missing. A legitimate zero must
    # follow the numeric comparison instead of defaultLeft.
    payload["trees"] = [[2, 0, -1.0, 1, 1, -3.0, 3.0]]
    model = ModelBundle(payload, source_sha256="test")
    vector = [0.0] * 48

    assert model._tree_leaf(payload["trees"][0], vector) == 3.0

    vector[2] = None
    assert model._tree_leaf(payload["trees"][0], vector) == -3.0


def test_zero_missing_split_uses_default_branch_only_for_zero():
    payload = make_payload()
    payload["trees"] = [[2, 0, -1.0, 1, 2, -3.0, 3.0]]
    model = ModelBundle(payload, source_sha256="test")
    vector = [0.0] * 48

    assert model._tree_leaf(payload["trees"][0], vector) == -3.0

    vector[2] = 1.0
    assert model._tree_leaf(payload["trees"][0], vector) == 3.0


def test_none_missing_split_compares_nan_as_zero():
    payload = make_payload()
    payload["trees"] = [[2, 0, 0.5, 0, 0, -3.0, 3.0]]
    model = ModelBundle(payload, source_sha256="test")
    vector = [0.0] * 48
    vector[2] = None

    assert model._tree_leaf(payload["trees"][0], vector) == -3.0


def test_unknown_missing_type_is_rejected_by_model_contract():
    payload = make_payload()
    payload["trees"] = [[2, 0, 0.5, 0, 3, -3.0, 3.0]]

    with pytest.raises(ModelContractError, match="unsupported missingType"):
        ModelBundle(payload, source_sha256="test")


def test_syn_116_regression_uses_zero_values_as_values_not_nan():
    model = ModelBundle.from_path(Path(__file__).parents[1] / "models" / "model_lgbm.json")
    current = {
        "연령": "30대", "Life_Stage": "4.자녀성장기(1)", "잔액_B0M": 2195521,
        "월중평잔": 1159383, "CA한도금액": 0, "청구금액_B0": 206868,
        "연체건수_R3M": 2, "연체건수_R6M": 4, "청구금액_R3M": 675523,
        "RV약정청구율": 20.20317522605343, "잔액_할부_B0M": 0, "남녀구분코드": 2,
        "선결제건수_R3M": 0, "회원여부_연체": 0, "잔액_일시불_B0M": 1119123,
        "잔액_카드론_B0M": 0, "잔액_카드론_B1M": 0, "유효카드수_신용": 2,
        "이용카드수_신용": 0, "이용금액_R3M_신용": 0, "한도증액횟수_R12M": 1,
        "카드이용한도금액": 393250, "한도심사요청건수": 0, "한도요청거절건수": 0,
        "잔액_현금서비스_B0M": 0, "잔액_현금서비스_B1M": 0,
        "시장단기연체여부_R3M": 0, "시장단기연체여부_R6M": 0,
        "이용가능카드수_신용": 0, "입회경과개월수_신용": 46,
        "카드이용한도금액_B1M": 410231, "강제한도감액금액_R12M": 202,
        "강제한도감액횟수_R12M": 4, "상환개월수_결제일_R3M": 0,
        "자발한도감액횟수_R12M": 0, "잔액_리볼빙일시불이월_B0M": 1076398,
    }
    previous = {
        "잔액_B0M": 2260378,
        "카드이용한도금액": 393250,
        "청구금액_B0": 211090,
    }

    prediction, _ = model.predict(current, previous)

    assert prediction.hazard_1m == pytest.approx(0.026541829006770875, abs=1e-12)
    assert prediction.hazard_2m == pytest.approx(0.012679861666223062, abs=1e-12)
    assert prediction.hazard_3m == pytest.approx(0.00697384051683748, abs=1e-12)
    assert prediction.cumulative_risk_3m == pytest.approx(0.04558780567725573, abs=1e-12)
    assert prediction.risk_grade == "INTEREST"


def test_counterfactual_prefers_explicit_b1m_when_snapshots_are_identical():
    model = ModelBundle.from_path(Path(__file__).parents[1] / "models" / "model_lgbm.json")
    current = {
        "연령": "30대", "Life_Stage": "4.자녀성장기(1)", "잔액_B0M": 1151640,
        "월중평잔": 486112, "CA한도금액": 0, "청구금액_B0": 164499,
        "연체건수_R3M": 3, "연체건수_R6M": 5, "청구금액_R3M": 482902,
        "RV약정청구율": 0.0, "잔액_할부_B0M": 0, "남녀구분코드": 2,
        "선결제건수_R3M": 0, "회원여부_연체": 0, "잔액_일시불_B0M": 155431,
        "잔액_카드론_B0M": 0, "잔액_카드론_B1M": 0, "유효카드수_신용": 2,
        "이용카드수_신용": 1, "이용금액_R3M_신용": 394282,
        "한도증액횟수_R12M": 0, "카드이용한도금액": 424278,
        "한도심사요청건수": 0, "한도요청거절건수": 0,
        "잔액_현금서비스_B0M": 996209, "잔액_현금서비스_B1M": 1003163,
        "시장단기연체여부_R3M": 0, "시장단기연체여부_R6M": 0,
        "이용가능카드수_신용": 0, "입회경과개월수_신용": 61,
        "카드이용한도금액_B1M": 437554, "강제한도감액금액_R12M": 202,
        "강제한도감액횟수_R12M": 3, "상환개월수_결제일_R3M": 0,
        "자발한도감액횟수_R12M": 0, "잔액_리볼빙일시불이월_B0M": 0,
    }

    prediction, enriched = model.predict(current, current)
    reasons = model.risk_factors(current, current, enriched)

    assert prediction.hazard_1m == pytest.approx(0.2272044874768498, abs=1e-12)
    assert prediction.risk_grade == "WARNING"
    assert reasons
    limit_reason = next(reason for reason in reasons if reason["featureKey"] == "카드이용한도금액")
    assert limit_reason["currentValue"] == 424278
    assert limit_reason["previousValue"] == 437554
    assert limit_reason["reasonMethod"] == "PREVIOUS_VALUE_COUNTERFACTUAL"


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
