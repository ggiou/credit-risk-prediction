"""LLM 설명의 수치 정합성 회귀 테스트.

배포본에서 관찰된 실제 사고를 고정한다.
  - 잔액_현금서비스_B0M 740180 -> 908261 은 +22.71% 인데 설명은 "1.2% 감소"였다.
  - 잔액_현금서비스_B0M 3038359 -> 2401756 은 -20.95% 인데 설명은 "1.15% 감소"였다.
원인은 (1) 한 피처에 전월 기준이 두 개라 서로 다른 변화율이 동시에 존재했고,
(2) 검증이 입력 전체 숫자를 한 집합으로만 비교해 피처 간 교차 오용을 잡지 못한 것이다.
"""

import pytest

from app.explanation_context import (
    build_feature_change_facts,
    build_observed_changes,
    resolve_previous_value,
)
from app.llm import RiskExplanationClient
from app.model_bundle import EMBEDDED_PREVIOUS_FEATURES


CASH = "잔액_현금서비스_B0M"
CASH_B1M = "잔액_현금서비스_B1M"


def _current(cash_now: float, cash_b1m: float) -> dict:
    return {CASH: cash_now, CASH_B1M: cash_b1m}


# --- 1. 전월 기준 단일화 ------------------------------------------------


def test_embedded_previous_wins_over_snapshot():
    """B1M이 있으면 근거와 관찰 신호가 같은 전월값을 쓴다."""

    current = _current(908261, 740180)
    previous = {CASH: 674609}  # 직전월 스냅샷: 기준이 갈리던 원인
    assert resolve_previous_value(current, previous, CASH) == 740180


def test_snapshot_used_when_no_embedded_previous():
    current = {"청구금액_B0": 176494}
    previous = {"청구금액_B0": 287903}
    assert resolve_previous_value(current, previous, "청구금액_B0") == 287903


def test_cash_advance_is_registered_in_embedded_map():
    assert EMBEDDED_PREVIOUS_FEATURES[CASH] == CASH_B1M


def test_observed_change_matches_reason_basis():
    """관찰 신호가 근거와 같은 +22.71%를 말해야 한다 (기존엔 +34.64%)."""

    current = _current(908261, 740180)
    previous = {CASH: 674609}
    reason = {
        "featureKey": CASH,
        "displayName": "기준월 현금서비스 잔액",
        "changeRate": (908261 - 740180) / 740180,
        "modelDirection": "INCREASE_RISK",
        "evidenceFeatureKeys": [CASH],
        "patternCode": "SHORT_TERM_BORROWING",
    }
    signals = build_observed_changes(current, previous, [reason])
    cash_signals = [s for s in signals if CASH in s["featureKeys"]]
    assert cash_signals, "현금서비스 관찰 신호가 생성되어야 한다"
    statement = cash_signals[0]["statement"]
    assert "22.71% 증가" in statement, statement
    assert "34.64" not in statement, "직전월 스냅샷 기준 값이 남아 있다"


# --- 2. 확정 사실표 -----------------------------------------------------


def test_feature_change_facts_agree_between_paths():
    current = _current(908261, 740180)
    previous = {CASH: 674609}
    reason = {
        "featureKey": CASH,
        "displayName": "기준월 현금서비스 잔액",
        "changeRate": (908261 - 740180) / 740180,
    }
    facts = build_feature_change_facts(current, previous, [reason])
    fact = facts["기준월 현금서비스 잔액"]
    assert fact["percent"] == 22.71
    assert fact["direction"] == "증가"
    assert fact["conflict"] is False


def test_conflicting_rates_are_flagged():
    """같은 표시명에 다른 변화율이 오면 대조 기준을 세울 수 없으므로 CONFLICT."""

    current = _current(908261, 740180)
    reasons = [
        {"featureKey": CASH, "displayName": "기준월 현금서비스 잔액", "changeRate": 0.2271},
        {"featureKey": "다른키", "displayName": "기준월 현금서비스 잔액", "changeRate": -0.0115},
    ]
    facts = build_feature_change_facts(current, None, reasons)
    assert facts["기준월 현금서비스 잔액"]["conflict"] is True


# --- 3. 출력 대조 검증 --------------------------------------------------


def _payload(percent: float, direction: str) -> dict:
    return {
        "featureChangeFacts": {
            "기준월 현금서비스 잔액": {
                "percent": percent,
                "direction": direction,
                "conflict": False,
            }
        }
    }


def test_wrong_percent_is_rejected():
    """재현 사례 1: 실제 +22.71%인데 1.2%로 서술."""

    text = "기준월 현금서비스 잔액은 전월보다 1.2% 감소했습니다."
    with pytest.raises(ValueError, match="percentage mismatch"):
        RiskExplanationClient._validate_feature_change_claims(text, _payload(22.71, "증가"))


def test_wrong_percent_is_rejected_second_case():
    """재현 사례 2: 실제 -20.95%인데 1.15%로 서술."""

    text = "기준월 현금서비스 잔액은 전월보다 1.15% 감소했습니다."
    with pytest.raises(ValueError, match="percentage mismatch"):
        RiskExplanationClient._validate_feature_change_claims(text, _payload(20.95, "감소"))


def test_wrong_direction_is_rejected():
    text = "기준월 현금서비스 잔액은 전월보다 22.71% 감소했습니다."
    with pytest.raises(ValueError, match="direction mismatch"):
        RiskExplanationClient._validate_feature_change_claims(text, _payload(22.71, "증가"))


def test_conflict_blocks_any_percentage():
    text = "기준월 현금서비스 잔액은 전월보다 22.71% 증가했습니다."
    payload = {
        "featureChangeFacts": {
            "기준월 현금서비스 잔액": {"percent": 22.71, "direction": "증가", "conflict": True}
        }
    }
    with pytest.raises(ValueError, match="ambiguous"):
        RiskExplanationClient._validate_feature_change_claims(text, payload)


def test_correct_claim_passes():
    text = "기준월 현금서비스 잔액은 전월보다 22.71% 증가했습니다."
    RiskExplanationClient._validate_feature_change_claims(text, _payload(22.71, "증가"))


def test_modifier_prefixed_name_still_matches():
    """'단기성 신용 이용 흐름 기준월 현금서비스 잔액은 …' 처럼 앞에 말이 붙어도 잡는다."""

    text = "단기성 신용 흐름에서 기준월 현금서비스 잔액은 전월보다 1.2% 감소했습니다."
    with pytest.raises(ValueError, match="percentage mismatch"):
        RiskExplanationClient._validate_feature_change_claims(text, _payload(22.71, "증가"))


def test_unknown_feature_is_ignored():
    """사실표에 없는 표시명은 기존 _allowed_numbers 검증에 맡긴다."""

    text = "알 수 없는 지표는 전월보다 5% 증가했습니다."
    RiskExplanationClient._validate_feature_change_claims(text, _payload(22.71, "증가"))


def test_no_facts_is_noop():
    RiskExplanationClient._validate_feature_change_claims("아무 문장", {})
