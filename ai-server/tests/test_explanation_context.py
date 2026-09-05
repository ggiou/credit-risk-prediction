from app.explanation_context import build_llm_input, build_observed_changes, horizon_pattern
from app.model_bundle import ModelPrediction


def test_peak_horizon_and_front_loaded_pattern_follow_actual_hazards():
    prediction = ModelPrediction(0.02786, 0.01332, 0.00733, 0.0476, "INTEREST", 0.33)
    payload = build_llm_input(
        model_version="miribom-lgbm-v0.3",
        prompt_version="v3.2",
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
    assert "최근 3개월 누적 청구금액은 9.08% 증가" in signals[0]["statement"]


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
        prompt_version="v3.2",
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
        prompt_version="v3.2",
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
        prompt_version="v3.2",
        prediction=prediction,
        reasons=[reason],
        current={"잔액_B0M": 99},
        previous={"잔액_B0M": 100},
    )

    candidate = payload["indicatorCandidates"][0]
    assert candidate["title"] == "잔액 부담 흐름"
    assert candidate["modelRelation"] == "RISK_DECREASE"
    assert candidate["fact"] == (
        "당월 총 카드 잔액은 전월보다 1% 감소했습니다. "
        "당월 총 카드 잔액을 전월값으로 대체한 재채점에서는 고위험 순위가 "
        "현재 81.4%에서 80.6%로 0.8%p 이동했습니다."
    )
    assert "더 위험" not in candidate["fact"]
    assert "덜 위험" not in candidate["fact"]
    assert "등급" not in candidate["fact"]


def test_counterfactual_rank_uses_one_decimal_display_difference():
    prediction = ModelPrediction(0.001, 0.0005, 0.0002, 0.0017, "NORMAL", 81.4)
    reason = {
        "reasonId": "R1", "featureKey": "잔액_B0M", "displayName": "당월 총 카드 잔액",
        "unit": "AMOUNT", "currentValue": 99, "previousValue": 100,
        "changeValue": -1, "changeRate": -0.01, "modelDirection": "DECREASE_RISK",
        "currentTopRiskPercent": 81.4, "counterfactualTopRiskPercent": 81.0,
        "topRiskPercentDifference": 0.4, "counterfactualRiskDirection": "CURRENT_LESS_RISKY",
        "counterfactualGrade": "정상", "counterfactualGradeChanged": False,
        "evidenceFeatureKeys": ["잔액_B0M", "f_사용률"], "patternCode": "BALANCE_EXPOSURE",
    }

    payload = build_llm_input(
        model_version="miribom-lgbm-v0.3", prompt_version="v3.2", prediction=prediction,
        reasons=[reason], current={"잔액_B0M": 99}, previous={"잔액_B0M": 100},
    )

    assert "현재 81.4%에서 81.0%로 0.4%p 이동했습니다." in payload["indicatorCandidates"][0]["fact"]


def test_equal_display_rank_does_not_change_raw_model_direction():
    prediction = ModelPrediction(0.001, 0.0005, 0.0002, 0.0017, "NORMAL", 81.44)
    reason = {
        "reasonId": "R1", "featureKey": "청구금액_B0", "displayName": "당월 청구금액",
        "unit": "AMOUNT", "currentValue": 90440, "previousValue": 100000,
        "changeValue": -9560, "changeRate": -0.0956, "modelDirection": "DECREASE_RISK",
        "currentTopRiskPercent": 81.44, "counterfactualTopRiskPercent": 81.36,
        "topRiskPercentDifference": 0.08, "counterfactualRiskDirection": "CURRENT_LESS_RISKY",
        "counterfactualGrade": "정상", "counterfactualGradeChanged": False,
        "evidenceFeatureKeys": ["청구금액_B0", "f_청구금액증가"], "patternCode": "BILLING_PRESSURE",
    }

    payload = build_llm_input(
        model_version="miribom-lgbm-v0.3", prompt_version="v3.2", prediction=prediction,
        reasons=[reason], current={"청구금액_B0": 90440}, previous={"청구금액_B0": 100000},
    )

    assert payload["modelReasons"][0]["modelDirection"] == "DECREASE_RISK"
    assert payload["indicatorCandidates"][0]["modelRelation"] == "RISK_DECREASE"
    assert "표시상 고위험 순위는 81.4%로 동일했습니다." in payload["indicatorCandidates"][0]["fact"]
    assert "0.0%p" not in payload["indicatorCandidates"][0]["fact"]


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
        model_version="miribom-lgbm-v0.3", prompt_version="v3.2", prediction=prediction,
        reasons=reasons, current={"잔액_B0M": 120, "월중평잔": 95},
        previous={"잔액_B0M": 100, "월중평잔": 100},
    )

    grouped = payload["indicatorCandidates"][0]
    assert grouped["title"] == "잔액 부담 흐름"
    assert grouped["modelRelation"] == "MIXED"
    assert grouped["reasonIds"] == ["R1", "R2"]
    assert payload["managementPriority"] == "PRIORITY_REVIEW"


def test_billing_increase_and_model_decrease_are_separated_as_objective_facts():
    prediction = ModelPrediction(0.001, 0.0005, 0.0002, 0.0017, "NORMAL", 81.4)
    reason = {
        "reasonId": "R1", "featureKey": "청구금액_B0", "displayName": "당월 청구금액",
        "unit": "AMOUNT", "currentValue": 100130, "previousValue": 100000,
        "changeValue": 130, "changeRate": 0.0013, "modelDirection": "DECREASE_RISK",
        "currentTopRiskPercent": 81.4, "counterfactualTopRiskPercent": 80.6,
        "topRiskPercentDifference": 0.8, "counterfactualRiskDirection": "CURRENT_LESS_RISKY",
        "counterfactualGrade": "정상", "counterfactualGradeChanged": False,
        "evidenceFeatureKeys": ["청구금액_B0", "f_청구금액증가"],
        "patternCode": "BILLING_PRESSURE",
    }
    payload = build_llm_input(
        model_version="miribom-lgbm-v0.3", prompt_version="v3.2", prediction=prediction,
        reasons=[reason], current={"청구금액_B0": 100130, "청구금액_R3M": 96000},
        previous={"청구금액_B0": 100000, "청구금액_R3M": 100000},
    )

    candidate = payload["indicatorCandidates"][0]
    assert candidate["modelRelation"] == "MIXED"
    assert candidate["fact"] == (
        "당월 청구금액은 전월보다 0.13% 증가했지만 최근 3개월 누적 청구금액은 4% 감소했습니다. "
        "당월 청구금액을 전월값으로 대체한 재채점에서는 고위험 순위가 "
        "현재 81.4%에서 80.6%로 0.8%p 이동했습니다."
    )
    assert candidate["fact"].count("당월 청구금액") == 2
    assert "위험 완화" not in candidate["fact"]
    assert "등급" not in candidate["fact"]


def test_billing_mixed_period_flow_uses_equal_display_rank_wording():
    prediction = ModelPrediction(0.00003, 0.00002, 0.00001, 0.00006, "NORMAL", 81.44)
    reason = {
        "reasonId": "R2", "featureKey": "청구금액_B0", "displayName": "당월 청구금액",
        "unit": "AMOUNT", "currentValue": 90440, "previousValue": 100000,
        "changeValue": -9560, "changeRate": -0.0956, "modelDirection": "DECREASE_RISK",
        "currentTopRiskPercent": 81.44, "counterfactualTopRiskPercent": 81.36,
        "topRiskPercentDifference": 0.08, "counterfactualRiskDirection": "CURRENT_LESS_RISKY",
        "counterfactualGrade": "정상", "counterfactualGradeChanged": False,
        "evidenceFeatureKeys": ["청구금액_B0", "f_청구금액증가"], "patternCode": "BILLING_PRESSURE",
    }
    payload = build_llm_input(
        model_version="miribom-lgbm-v0.3", prompt_version="v3.2", prediction=prediction,
        reasons=[reason],
        current={"청구금액_B0": 90440, "청구금액_R3M": 104580},
        previous={"청구금액_B0": 100000, "청구금액_R3M": 100000},
    )

    candidate = payload["indicatorCandidates"][0]
    assert candidate == {
        "indicatorId": "K1",
        "title": "청구 부담 흐름",
        "fact": (
            "당월 청구금액은 전월보다 9.56% 감소했지만 최근 3개월 누적 청구금액은 4.58% 증가했습니다. "
            "당월 청구금액을 전월값으로 대체한 재채점에서도 표시상 고위험 순위는 "
            "81.4%로 동일했습니다."
        ),
        "modelRelation": "MIXED",
        "reasonIds": ["R2"],
        "signalIds": ["S1"],
        "featureKeys": ["청구금액_B0", "청구금액_R3M"],
    }


def test_prompt_version_change_does_not_change_backend_numeric_context():
    prediction = ModelPrediction(0.00003, 0.00002, 0.00001, 0.00006, "NORMAL", 81.44)
    reason = {
        "reasonId": "R1", "featureKey": "잔액_B0M", "displayName": "당월 총 카드 잔액",
        "unit": "AMOUNT", "currentValue": 99, "previousValue": 100,
        "changeValue": -1, "changeRate": -0.01, "modelDirection": "DECREASE_RISK",
        "currentTopRiskPercent": 81.44, "counterfactualTopRiskPercent": 81.36,
        "topRiskPercentDifference": 0.08, "counterfactualRiskDirection": "CURRENT_LESS_RISKY",
        "counterfactualGrade": "정상", "counterfactualGradeChanged": False,
        "evidenceFeatureKeys": ["잔액_B0M", "f_사용률"], "patternCode": "BALANCE_EXPOSURE",
    }
    arguments = {
        "model_version": "miribom-lgbm-v0.3", "prediction": prediction, "reasons": [reason],
        "current": {"잔액_B0M": 99}, "previous": {"잔액_B0M": 100},
    }

    before = build_llm_input(prompt_version="v3.1", **arguments)
    after = build_llm_input(prompt_version="v3.2", **arguments)

    assert before["prediction"] == after["prediction"]
    assert before["modelReasons"] == after["modelReasons"]
    assert before["observedChanges"] == after["observedChanges"]
    assert before["indicatorCandidates"] == after["indicatorCandidates"]
