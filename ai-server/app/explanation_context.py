from __future__ import annotations

from typing import Any

from .model_bundle import DISPLAY_NAMES, LEAKAGE_FEATURES, PATTERN_FEATURES, ModelPrediction


GRADE_NAMES = {
    "NORMAL": "정상",
    "INTEREST": "관심",
    "CAUTION": "주의",
    "WARNING": "경고",
}

PATTERN_REVIEW_CHECKS = {
    "PAYMENT_REGULARITY": "최근 3개월 결제일별 정상·부분·미납 내역 확인",
    "CREDIT_AVAILABILITY": "강제 한도 감액 발생 시점과 사용 가능 카드 상태 확인",
    "SHORT_TERM_BORROWING": "최근 현금서비스·카드론·리볼빙 이용 변화 확인",
    "BALANCE_EXPOSURE": "한도 대비 잔액과 최근 잔액 구성 변화 확인",
    "BILLING_PRESSURE": "다음 결제 예정 금액과 최근 납부 이력 확인",
    "CARD_ACTIVITY": "최근 3개월 카드 이용금액과 이용 카드 수 변화 확인",
}

MANAGEMENT_PRIORITIES = {
    "NORMAL": "ROUTINE_MONITORING",
    "INTEREST": "ENHANCED_MONITORING",
    "CAUTION": "PRIORITY_REVIEW",
    "WARNING": "URGENT_REVIEW",
}

MANAGEMENT_PRIORITY_LABELS = {
    "ROUTINE_MONITORING": "정기 모니터링",
    "ENHANCED_MONITORING": "강화 모니터링",
    "PRIORITY_REVIEW": "우선 검토",
    "URGENT_REVIEW": "긴급 검토",
}

INDICATOR_TITLES = {
    "PAYMENT_REGULARITY": "결제 규칙성",
    "CREDIT_AVAILABILITY": "카드 이용 가능 상태",
    "SHORT_TERM_BORROWING": "단기성 신용 이용 흐름",
    "BALANCE_EXPOSURE": "잔액 부담 흐름",
    "BILLING_PRESSURE": "청구 부담 흐름",
    "CARD_ACTIVITY": "카드 이용 활동",
}

OBSERVABLE_FEATURES = (
    "상환개월수_결제일_R3M",
    "선결제건수_R3M",
    "연체건수_R3M",
    "연체건수_R6M",
    "시장단기연체여부_R3M",
    "시장단기연체여부_R6M",
    "이용가능카드수_신용",
    "유효카드수_신용",
    "강제한도감액횟수_R12M",
    "잔액_현금서비스_B0M",
    "잔액_카드론_B0M",
    "잔액_리볼빙일시불이월_B0M",
    "잔액_B0M",
    "월중평잔",
    "청구금액_B0",
    "청구금액_R3M",
    "이용금액_R3M_신용",
)

OBSERVED_DISPLAY_NAMES = {
    "청구금액_R3M": "최근 3개월 누적 청구금액",
}


def horizon_pattern(hazards: list[float]) -> str:
    if hazards[0] > hazards[1] > hazards[2]:
        return "FRONT_LOADED"
    if hazards[0] < hazards[1] < hazards[2]:
        return "BACK_LOADED"
    return "MIXED"


def _number(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _percent_change(current: Any, previous: Any) -> float | None:
    current_number = _number(current)
    previous_number = _number(previous)
    if current_number is None or previous_number in (None, 0):
        return None
    return (current_number - previous_number) / abs(previous_number) * 100.0


def _format_percent(value: float) -> str:
    return f"{abs(value):.2f}".rstrip("0").rstrip(".")


def _format_hazard_percent(value: float) -> str:
    percent = abs(value) * 100
    digits = 6 if 0 < percent < 0.01 else 2
    return f"{percent:.{digits}f}".rstrip("0").rstrip(".") + "%"


def _display_top_risk(value: float) -> float:
    """화면과 반사실 문장에서 사용하는 고위험 순위를 소수점 한 자리로 맞춘다."""

    return round(value, 1)


def _format_display_top_risk(value: float) -> str:
    return f"{_display_top_risk(value):.1f}"


def _format_number(value: float) -> str:
    if value.is_integer():
        return f"{int(value):,}"
    return f"{value:,.2f}".rstrip("0").rstrip(".")


def _display_value(value: Any, unit: str, *, absolute: bool = False) -> str | None:
    number = _number(value)
    if number is None:
        return None
    if absolute:
        number = abs(number)
    if unit == "RATIO":
        return f"{number * 100:.2f}".rstrip("0").rstrip(".") + "%"
    suffix = {"AMOUNT": "원", "COUNT": "", "FLAG": "", "VALUE": ""}.get(unit, "")
    return _format_number(number) + suffix


def _llm_reason(reason: dict[str, Any]) -> dict[str, Any]:
    """근거 값과 반사실 순위 비교를 LLM이 계산 없이 복사하도록 준비한다."""

    prepared = dict(reason)
    unit = str(reason.get("unit") or "VALUE")
    for value_key in ("currentValue", "previousValue", "changeValue"):
        displayed = _display_value(reason.get(value_key), unit)
        if displayed is not None:
            prepared[f"{value_key}Display"] = displayed
    change_rate = _number(reason.get("changeRate"))
    if change_rate is not None:
        # ModelBundle.changeRate는 비율(0.0735)이며 화면 문장에서는 퍼센트(7.35%)로 표시한다.
        prepared["changeRateDisplay"] = _format_percent(change_rate * 100) + "%"
    current_value = _number(reason.get("currentValue"))
    previous_value = _number(reason.get("previousValue"))
    absolute_change = _display_value(reason.get("changeValue"), unit, absolute=True)
    if current_value is not None and previous_value is not None and absolute_change is not None:
        feature_name = str(reason.get("displayName") or reason.get("featureKey"))
        change_direction = "증가" if current_value > previous_value else "감소" if current_value < previous_value else "동일"
        topic = _topic(feature_name)
        if change_direction == "동일":
            prepared["valueChangeSummaryStatement"] = f"{topic} 전월과 동일했습니다."
            prepared["valueChangeDetailStatement"] = (
                f"{topic} 전월과 현재 모두 {prepared['currentValueDisplay']}로 동일했습니다."
            )
        else:
            if change_rate is not None:
                prepared["valueChangeSummaryStatement"] = (
                    f"{topic} 전월보다 {prepared['changeRateDisplay']} {change_direction}했습니다."
                )
            prepared["valueChangeDetailStatement"] = (
                f"{topic} 전월 {prepared['previousValueDisplay']}에서 현재 "
                f"{_directional(prepared['currentValueDisplay'])} {absolute_change} {change_direction}했습니다."
            )
        value_statement = (
            f"{feature_name}의 전월 스냅샷은 {prepared['previousValueDisplay']}, "
            f"현재는 {prepared['currentValueDisplay']}이며 {absolute_change} {change_direction}"
        )
        prepared["valueChangeStatement"] = (
            f"{value_statement}했고, 변화율은 {prepared['changeRateDisplay']}입니다."
            if change_rate is not None
            else f"{value_statement}했습니다."
        )
    current_top = _number(reason.get("currentTopRiskPercent"))
    counterfactual_top = _number(reason.get("counterfactualTopRiskPercent"))
    difference = _number(reason.get("topRiskPercentDifference"))
    if current_top is not None and counterfactual_top is not None and difference is not None:
        feature_name = str(reason.get("displayName") or reason.get("featureKey"))
        display_current = _display_top_risk(current_top)
        display_counterfactual = _display_top_risk(counterfactual_top)
        if display_current == display_counterfactual:
            prepared["counterfactualComparisonStatement"] = (
                f"{feature_name}을 전월값으로 대체한 재채점에서도 표시상 고위험 순위는 "
                f"{_format_display_top_risk(current_top)}%로 동일했습니다."
            )
        else:
            display_difference = abs(display_current - display_counterfactual)
            prepared["counterfactualComparisonStatement"] = (
                f"{feature_name}을 전월값으로 대체한 재채점에서는 고위험 순위가 "
                f"현재 {_format_display_top_risk(current_top)}%에서 "
                f"{_format_display_top_risk(counterfactual_top)}%로 "
                f"{display_difference:.1f}%p 이동했습니다."
            )
    return prepared


def _topic(subject: str) -> str:
    if not subject:
        return ""
    last = subject[-1]
    has_batchim = "가" <= last <= "힣" and (ord(last) - ord("가")) % 28 != 0
    return f"{subject}{'은' if has_batchim else '는'}"


def _object(subject: str) -> str:
    if not subject:
        return ""
    last = subject[-1]
    has_batchim = "가" <= last <= "힣" and (ord(last) - ord("가")) % 28 != 0
    return f"{subject}{'을' if has_batchim else '를'}"


def _directional(subject: str) -> str:
    """표시값 뒤의 '로/으로' 조사를 자연스럽게 붙인다."""

    if not subject:
        return subject
    last = subject[-1]
    if "가" <= last <= "힣":
        jongseong = (ord(last) - ord("가")) % 28
        return f"{subject}{'으로' if jongseong not in {0, 8} else '로'}"
    return f"{subject}로"


def _join_feature_names(names: list[str]) -> str:
    if len(names) == 1:
        return names[0]
    if len(names) == 2:
        first = names[0]
        last = first[-1]
        has_batchim = "가" <= last <= "힣" and (ord(last) - ord("가")) % 28 != 0
        return f"{first}{'과' if has_batchim else '와'} {names[1]}"
    return ", ".join(names)


def _counterfactual_comparison_facts(reasons: list[dict[str, Any]]) -> list[str]:
    """동일 패턴에서 표시상 같은 순위 이동은 피처명을 묶어 한 문장으로 만든다."""

    grouped: dict[tuple[float, float], list[str]] = {}
    fallback: list[str] = []
    for reason in reasons:
        current_top = _number(reason.get("currentTopRiskPercent"))
        counterfactual_top = _number(reason.get("counterfactualTopRiskPercent"))
        difference = _number(reason.get("topRiskPercentDifference"))
        if current_top is None or counterfactual_top is None or difference is None:
            statement = str(reason.get("counterfactualComparisonStatement", "")).strip()
            if statement:
                fallback.append(statement)
            continue
        signature = (_display_top_risk(current_top), _display_top_risk(counterfactual_top))
        name = str(reason.get("displayName") or reason.get("featureKey"))
        grouped.setdefault(signature, []).append(name)

    facts: list[str] = []
    for (display_current, display_counterfactual), raw_names in grouped.items():
        names = list(dict.fromkeys(raw_names))
        subjects = _join_feature_names(names)
        target = _object(subjects)
        plural = len(names) > 1
        replacement = "각각 전월값으로" if plural else "전월값으로"
        if display_current == display_counterfactual:
            facts.append(
                f"{target} {replacement} 대체한 재채점에서도 표시상 고위험 순위는 "
                f"{display_current:.1f}%로 동일했습니다."
            )
        else:
            movement = abs(display_current - display_counterfactual)
            common = "모두 " if plural else ""
            facts.append(
                f"{target} {replacement} 대체한 재채점에서는 고위험 순위가 "
                f"{common}현재 {display_current:.1f}%에서 {display_counterfactual:.1f}%로 "
                f"{movement:.1f}%p 이동했습니다."
            )
    return list(dict.fromkeys([*facts, *fallback]))


def _observed_display_name(feature_key: str) -> str:
    return OBSERVED_DISPLAY_NAMES.get(feature_key, DISPLAY_NAMES.get(feature_key, feature_key))


def build_observed_changes(
    current: dict[str, Any],
    previous: dict[str, Any] | None,
    reasons: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    if not previous:
        return []

    signals: list[dict[str, Any]] = []
    used: set[str] = set()

    # 당월과 R3M의 방향이 다르면 한 문장에 집계 기간을 명시한다.
    for current_key, aggregate_key in (
        ("청구금액_B0", "청구금액_R3M"),
    ):
        current_rate = _percent_change(current.get(current_key), previous.get(current_key))
        aggregate_rate = _percent_change(current.get(aggregate_key), previous.get(aggregate_key))
        if current_rate is not None and aggregate_rate is not None and current_rate * aggregate_rate < 0:
            statement = (
                f"{_topic(_observed_display_name(current_key))} 전월보다 {_format_percent(current_rate)}% "
                f"{'증가' if current_rate > 0 else '감소'}했지만 "
                f"{_topic(_observed_display_name(aggregate_key))} {_format_percent(aggregate_rate)}% "
                f"{'증가' if aggregate_rate > 0 else '감소'}했습니다."
            )
            signals.append({
                "statement": statement,
                "featureKeys": [current_key, aggregate_key],
                "relationToModel": "CONTEXT",
            })
            used.update((current_key, aggregate_key))

    reason_patterns = {reason.get("patternCode") for reason in reasons}
    relation_by_key = {
        key: ("SUPPORTS" if reason.get("modelDirection") == "INCREASE_RISK" else "MITIGATES")
        for reason in reasons
        for key in [reason.get("featureKey"), *reason.get("evidenceFeatureKeys", [])]
        if key
    }
    for feature_key in OBSERVABLE_FEATURES:
        if feature_key in used or feature_key in LEAKAGE_FEATURES:
            continue
        if feature_key not in current or feature_key not in previous:
            continue
        current_value = current.get(feature_key)
        previous_value = previous.get(feature_key)
        if current_value == previous_value:
            if feature_key == "강제한도감액횟수_R12M" and "CREDIT_AVAILABILITY" in reason_patterns:
                signals.append({
                    "statement": f"{_topic(DISPLAY_NAMES[feature_key])} 전월과 동일합니다.",
                    "featureKeys": [feature_key],
                    "relationToModel": "CONTEXT",
                })
            continue
        rate = _percent_change(current_value, previous_value)
        if rate is None:
            statement = f"{_observed_display_name(feature_key)} 값이 전월과 달라졌습니다."
        else:
            statement = (
                f"{_topic(_observed_display_name(feature_key))} 전월보다 "
                f"{_format_percent(rate)}% {'증가' if rate > 0 else '감소'}했습니다."
            )
        signals.append({
            "statement": statement,
            "featureKeys": [feature_key],
            "relationToModel": relation_by_key.get(feature_key, "CONTEXT"),
        })

    # 모델 근거와 연결된 사실을 먼저 보내고 자유 추론 여지를 줄인다.
    signals.sort(key=lambda signal: signal["relationToModel"] == "CONTEXT")
    for index, signal in enumerate(signals[:6], start=1):
        signal["signalId"] = f"S{index}"
    return signals[:6]


def build_allowed_review_checks(reasons: list[dict[str, Any]]) -> list[str]:
    checks = []
    for reason in reasons:
        check = PATTERN_REVIEW_CHECKS.get(str(reason.get("patternCode")))
        if check and check not in checks:
            checks.append(check)
    return checks[:4]


def _pattern_for_feature(feature_key: str) -> str:
    for pattern_code, feature_keys in PATTERN_FEATURES.items():
        if feature_key in feature_keys:
            return pattern_code
    return "CARD_ACTIVITY"


def _indicator_candidates(
    reasons: list[dict[str, Any]],
    signals: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """LLM이 수치를 계산하지 않도록 카드의 사실·관계·출처를 결정적으로 만든다."""

    candidates: list[dict[str, Any]] = []
    candidate_index_by_pattern: dict[str, int] = {}
    linked_signals: set[str] = set()
    grouped_reasons: dict[str, list[dict[str, Any]]] = {}
    for reason in reasons:
        grouped_reasons.setdefault(str(reason.get("patternCode")), []).append(reason)

    for pattern_code, pattern_reasons in grouped_reasons.items():
        reason_features = {
            key for reason in pattern_reasons
            for key in [reason.get("featureKey"), *reason.get("evidenceFeatureKeys", [])]
            if key
        }
        related = [
            signal for signal in signals
            if reason_features.intersection(signal.get("featureKeys", []))
        ]
        linked_signals.update(str(signal["signalId"]) for signal in related)
        observed_facts = list(dict.fromkeys(
            str(signal["statement"]).strip() for signal in related
            if str(signal.get("statement", "")).strip()
        ))
        observed_feature_keys = {
            key for signal in related for key in signal.get("featureKeys", [])
        }
        observed_facts.extend(
            str(reason["valueChangeSummaryStatement"]).strip()
            for reason in pattern_reasons
            if reason.get("valueChangeSummaryStatement")
            and reason.get("featureKey") not in observed_feature_keys
        )
        value_details = list(dict.fromkeys(
            str(reason["valueChangeDetailStatement"]).strip()
            for reason in pattern_reasons
            if reason.get("valueChangeDetailStatement")
        ))
        comparison_facts = _counterfactual_comparison_facts(pattern_reasons)
        facts = list(dict.fromkeys(fact for fact in observed_facts if fact))
        details = list(dict.fromkeys(
            detail for detail in [*value_details, *comparison_facts] if detail
        ))
        feature_keys = list(dict.fromkeys(str(reason["featureKey"]) for reason in pattern_reasons))
        for signal in related:
            for key in signal.get("featureKeys", []):
                if key not in feature_keys:
                    feature_keys.append(key)
        directions = {reason.get("modelDirection") for reason in pattern_reasons}
        has_mixed_period_signal = any("했지만" in str(signal.get("statement")) for signal in related)
        candidate_index_by_pattern[pattern_code] = len(candidates)
        candidates.append({
            "indicatorId": f"K{len(candidates) + 1}",
            "title": INDICATOR_TITLES.get(pattern_code, str(pattern_reasons[0].get("patternName"))),
            "fact": " ".join(facts),
            "detail": " ".join(details),
            "modelRelation": (
                "MIXED" if len(directions) > 1 or has_mixed_period_signal
                else "RISK_INCREASE" if "INCREASE_RISK" in directions else "RISK_DECREASE"
            ),
            "reasonIds": [reason["reasonId"] for reason in pattern_reasons],
            "signalIds": [signal["signalId"] for signal in related],
            "featureKeys": feature_keys,
        })

    for signal in signals:
        if signal["signalId"] in linked_signals:
            continue
        feature_keys = list(signal.get("featureKeys", []))
        pattern_code = _pattern_for_feature(str(feature_keys[0])) if feature_keys else "CARD_ACTIVITY"
        relation = {
            "SUPPORTS": "RISK_INCREASE",
            "MITIGATES": "RISK_DECREASE",
        }.get(str(signal.get("relationToModel")), "CONTEXT")
        if "했지만" in str(signal.get("statement")):
            relation = "MIXED"
        existing_index = candidate_index_by_pattern.get(pattern_code)
        if existing_index is not None:
            candidate = candidates[existing_index]
            statement = str(signal["statement"]).strip()
            current_fact = str(candidate["fact"]).strip()
            if statement and statement not in current_fact:
                candidate["fact"] = f"{current_fact} {statement}".strip()
            if signal["signalId"] not in candidate["signalIds"]:
                candidate["signalIds"].append(signal["signalId"])
            for key in feature_keys:
                if key not in candidate["featureKeys"]:
                    candidate["featureKeys"].append(key)
            current_relation = str(candidate["modelRelation"])
            if current_relation == "CONTEXT":
                candidate["modelRelation"] = relation
            elif relation not in {"CONTEXT", current_relation}:
                candidate["modelRelation"] = "MIXED"
            continue
        candidate_index_by_pattern[pattern_code] = len(candidates)
        candidates.append({
            "indicatorId": f"K{len(candidates) + 1}",
            "title": INDICATOR_TITLES[pattern_code],
            "fact": str(signal["statement"]),
            "detail": "",
            "modelRelation": relation,
            "reasonIds": [],
            "signalIds": [signal["signalId"]],
            "featureKeys": feature_keys,
        })
    return candidates[:6]


def build_llm_input(
    *,
    model_version: str,
    prompt_version: str,
    prediction: ModelPrediction,
    reasons: list[dict[str, Any]],
    current: dict[str, Any],
    previous: dict[str, Any] | None,
) -> dict[str, Any]:
    hazards = [prediction.hazard_1m, prediction.hazard_2m, prediction.hazard_3m]
    peak_month = max(range(3), key=hazards.__getitem__) + 1
    changes = build_observed_changes(current, previous, reasons)
    low_stable = (
        prediction.risk_grade == "NORMAL"
        and max(hazards) < 0.0001
        and max(hazards) - min(hazards) < 0.0001
    )
    prepared_reasons = []
    for reason in reasons:
        prepared = dict(reason)
        prepared["currentGrade"] = prediction.risk_grade
        prepared_reasons.append(_llm_reason(prepared))
    indicator_candidates = _indicator_candidates(prepared_reasons, changes)
    return {
        "modelContext": {
            "modelVersion": model_version,
            "promptVersion": prompt_version,
            "predictionSource": "LIGHTGBM_JSON",
            "dataType": "PUBLIC_SYNTHETIC_DEMO",
            "target": "기준월 이후 1·2·3개월째 연체 발생 위험",
        },
        "prediction": {
            "grade": GRADE_NAMES[prediction.risk_grade],
            "topRiskPercent": prediction.top_risk_percent,
            "monthlyHazards": [
                {
                    "month": index,
                    "value": value,
                    "valueDisplay": _format_hazard_percent(value),
                }
                for index, value in enumerate(hazards, start=1)
            ],
            "peakHorizonMonth": peak_month,
            "horizonPattern": horizon_pattern(hazards),
            "horizonEmphasis": "LOW_STABLE" if low_stable else "PEAK",
        },
        "managementPriority": MANAGEMENT_PRIORITIES[prediction.risk_grade],
        "managementPriorityDisplay": MANAGEMENT_PRIORITY_LABELS[
            MANAGEMENT_PRIORITIES[prediction.risk_grade]
        ],
        "generationMode": "FULL_ANALYSIS",
        "modelReasons": prepared_reasons,
        "observedChanges": changes,
        "indicatorCandidates": indicator_candidates,
        "allowedReviewChecks": build_allowed_review_checks(reasons),
    }
