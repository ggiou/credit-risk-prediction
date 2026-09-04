from app.explanation_context import build_llm_input, build_observed_changes, horizon_pattern
from app.model_bundle import ModelPrediction


def test_peak_horizon_and_front_loaded_pattern_follow_actual_hazards():
    prediction = ModelPrediction(0.02786, 0.01332, 0.00733, 0.0476, "INTEREST", 0.33)
    payload = build_llm_input(
        model_version="miribom-lgbm-v0.3",
        prompt_version="v3.1",
        prediction=prediction,
        reasons=[],
        current={},
        previous=None,
    )

    assert payload["prediction"]["peakHorizonMonth"] == 1
    assert payload["prediction"]["horizonPattern"] == "FRONT_LOADED"
    assert payload["prediction"]["horizonEmphasis"] == "PEAK"
    assert payload["managementPriority"] == "ENHANCED_MONITORING"
    assert payload["managementPriorityDisplay"] == "강화 모니터링"
    assert payload["generationMode"] == "FULL_ANALYSIS"
    assert "cumulativeRisk3m" not in payload["prediction"]
    assert "c3" not in payload["prediction"]


def test_horizon_is_back_loaded_only_when_every_hazard_increases():
    assert horizon_pattern([0.01, 0.02, 0.03]) == "BACK_LOADED"
    assert horizon_pattern([0.03, 0.01, 0.02]) == "MIXED"


def test_current_month_decrease_and_r3m_increase_are_one_mixed_period_signal():
    current = {"청구금액_B0": 55644, "청구금액_R3M": 173964}
    previous = {"청구금액_B0": 66128, "청구금액_R3M": 159489}

    signals = build_observed_changes(current, previous, [])

    assert signals[0]["featureKeys"] == ["청구금액_B0", "청구금액_R3M"]
    assert "15.85% 감소" in signals[0]["statement"]
    assert "9.08% 증가" in signals[0]["statement"]


def test_unchanged_r12m_limit_count_is_not_called_new():
    reasons = [{
        "featureKey": "강제한도감액횟수_R12M",
        "evidenceFeatureKeys": ["강제한도감액횟수_R12M"],
        "patternCode": "CREDIT_AVAILABILITY",
    }]
    signals = build_observed_changes(
        {"강제한도감액횟수_R12M": 1},
        {"강제한도감액횟수_R12M": 1},
        reasons,
    )

    assert signals[0]["statement"].endswith("전월과 동일합니다.")
    assert "신규" not in signals[0]["statement"]


def test_ratio_reason_contains_backend_formatted_percent_values():
    prediction = ModelPrediction(0.02786, 0.01332, 0.00733, 0.0476, "INTEREST", 0.33)
    reason = {
        "reasonId": "R1",
        "featureKey": "f_카드가용비율",
        "unit": "RATIO",
        "currentValue": 0.07354728210691878,
        "previousValue": 0.1,
        "changeValue": -0.02645271789308122,
        "changeRate": -0.2645271789308122,
        "patternCode": "CREDIT_AVAILABILITY",
    }

    payload = build_llm_input(
        model_version="miribom-lgbm-v0.3",
        prompt_version="v3.1",
        prediction=prediction,
        reasons=[reason],
        current={},
        previous=None,
    )

    prepared = payload["modelReasons"][0]
    assert prepared["currentValueDisplay"] == "7.35%"
    assert prepared["previousValueDisplay"] == "10%"
    assert prepared["changeValueDisplay"] == "-2.65%"
    assert prepared["changeRateDisplay"] == "26.45%"


def test_low_normal_hazards_use_stable_horizon_message_contract():
    prediction = ModelPrediction(0.00000003, 0.00000002, 0.00000001, 0.00000006, "NORMAL", 98.7)

    payload = build_llm_input(
        model_version="miribom-lgbm-v0.3",
        prompt_version="v3.1",
        prediction=prediction,
        reasons=[],
        current={},
        previous=None,
    )

    assert payload["prediction"]["horizonEmphasis"] == "LOW_STABLE"
    assert payload["managementPriority"] == "ROUTINE_MONITORING"
    assert payload["managementPriorityDisplay"] == "정기 모니터링"
    assert payload["prediction"]["monthlyHazards"][0]["valueDisplay"] == "0.000003%"


def test_indicator_candidate_uses_backend_fact_and_counterfactual_rank_difference():
    prediction = ModelPrediction(0.02786, 0.01332, 0.00733, 0.0476, "CAUTION", 81.4)
    reason = {
        "reasonId": "R1",
        "featureKey": "잔액_B0M",
        "displayName": "당월 총 카드 잔액",
        "unit": "AMOUNT",
        "currentValue": 99,
        "previousValue": 100,
        "changeValue": -1,
        "changeRate": -0.01,
        "modelDirection": "DECREASE_RISK",
        "currentTopRiskPercent": 81.4,
        "counterfactualTopRiskPercent": 80.6,
        "topRiskPercentDifference": 0.8,
        "counterfactualRiskDirection": "CURRENT_LESS_RISKY",
        "counterfactualGrade": "주의",
        "counterfactualGradeChanged": False,
        "evidenceFeatureKeys": ["잔액_B0M", "f_사용률", "f_현금서비스비중"],
        "patternCode": "BALANCE_EXPOSURE",
    }

    payload = build_llm_input(
        model_version="miribom-lgbm-v0.3",
        prompt_version="v3.1",
        prediction=prediction,
        reasons=[reason],
        current={"잔액_B0M": 99},
        previous={"잔액_B0M": 100},
    )

    candidate = payload["indicatorCandidates"][0]
    assert candidate["title"] == "잔액 부담 흐름"
    assert candidate["modelRelation"] == "RISK_DECREASE"
    assert "전월 스냅샷은 100원, 현재는 99원이며 1원 감소" in candidate["fact"]
    assert "81.4%" in candidate["fact"]
    assert "80.6%" in candidate["fact"]
    assert "0.8%p" in candidate["fact"]


def test_caution_customer_groups_increase_and_decrease_reasons_as_mixed_pattern():
    prediction = ModelPrediction(0.04, 0.03, 0.02, 0.087, "CAUTION", 6.2)
    reasons = [
        {
            "reasonId": "R1", "featureKey": "잔액_B0M", "displayName": "당월 총 카드 잔액",
            "unit": "AMOUNT", "modelDirection": "INCREASE_RISK", "currentTopRiskPercent": 6.2,
            "counterfactualTopRiskPercent": 7.0, "topRiskPercentDifference": 0.8,
            "counterfactualRiskDirection": "CURRENT_MORE_RISKY", "counterfactualGrade": "주의",
            "counterfactualGradeChanged": False, "evidenceFeatureKeys": ["잔액_B0M", "f_사용률"],
            "patternCode": "BALANCE_EXPOSURE",
        },
        {
            "reasonId": "R2", "featureKey": "월중평잔", "displayName": "월중 평균잔액",
            "unit": "AMOUNT", "modelDirection": "DECREASE_RISK", "currentTopRiskPercent": 6.2,
            "counterfactualTopRiskPercent": 5.8, "topRiskPercentDifference": 0.4,
            "counterfactualRiskDirection": "CURRENT_LESS_RISKY", "counterfactualGrade": "주의",
            "counterfactualGradeChanged": False, "evidenceFeatureKeys": ["월중평잔"],
            "patternCode": "BALANCE_EXPOSURE",
        },
    ]

    payload = build_llm_input(
        model_version="miribom-lgbm-v0.3", prompt_version="v3.1", prediction=prediction,
        reasons=reasons, current={"잔액_B0M": 120, "월중평잔": 95},
        previous={"잔액_B0M": 100, "월중평잔": 100},
    )

    grouped = payload["indicatorCandidates"][0]
    assert grouped["title"] == "잔액 부담 흐름"
    assert grouped["modelRelation"] == "MIXED"
    assert grouped["reasonIds"] == ["R1", "R2"]
    assert payload["managementPriority"] == "PRIORITY_REVIEW"


def test_indicator_relation_is_mixed_when_current_month_and_r3m_move_oppositely():
    prediction = ModelPrediction(0.001, 0.0005, 0.0002, 0.0017, "NORMAL", 81.4)
    reason = {
        "reasonId": "R1", "featureKey": "청구금액_B0", "displayName": "당월 청구금액",
        "unit": "AMOUNT", "currentValue": 99, "previousValue": 100,
        "changeValue": -1, "changeRate": -0.01, "modelDirection": "DECREASE_RISK",
        "currentTopRiskPercent": 81.4, "counterfactualTopRiskPercent": 81.0,
        "topRiskPercentDifference": 0.4, "counterfactualRiskDirection": "CURRENT_LESS_RISKY",
        "counterfactualGrade": "정상", "counterfactualGradeChanged": False,
        "evidenceFeatureKeys": ["청구금액_B0", "f_청구금액증가"],
        "patternCode": "BILLING_PRESSURE",
    }
    payload = build_llm_input(
        model_version="miribom-lgbm-v0.3", prompt_version="v3.1", prediction=prediction,
        reasons=[reason], current={"청구금액_B0": 99, "청구금액_R3M": 110},
        previous={"청구금액_B0": 100, "청구금액_R3M": 100},
    )

    assert payload["indicatorCandidates"][0]["modelRelation"] == "MIXED"
    assert "당월 청구금액" in payload["indicatorCandidates"][0]["fact"]
    assert "최근 3개월 청구금액" in payload["indicatorCandidates"][0]["fact"]
