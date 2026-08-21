"""파생 피처 계산의 결측값과 전월 비교 규칙을 검증한다."""

import math

from app.services.feature_service import calculate_derived_features, clean_number, safe_divide


def test_sentinel_value_is_missing() -> None:
    """원천 센티널 값은 실제 음수값이 아니라 결측값으로 변환한다."""

    assert clean_number(-99999999) is None
    assert clean_number("값없음") is None


def test_zero_denominator_is_missing() -> None:
    """분모가 0인 비율은 0%로 오해하지 않도록 결측값으로 유지한다."""

    assert safe_divide(100, 0) is None
    assert safe_divide(None, 100) is None


def test_derived_features_use_previous_month() -> None:
    """현재·이전 월 값으로 사용률과 잔액 증가율을 계산한다."""

    current = {
        "카드이용한도금액": 5_000_000,
        "카드이용한도금액_B1M": 5_200_000,
        "잔액_B0M": 4_000_000,
        "잔액_현금서비스_B0M": 400_000,
        "잔액_현금서비스_B1M": 300_000,
        "잔액_카드론_B0M": 800_000,
        "잔액_카드론_B1M": 700_000,
        "잔액_리볼빙일시불이월_B0M": 200_000,
        "청구금액_B0": 1_500_000,
        "이용가능카드수_신용": 3,
        "유효카드수_신용": 4,
    }
    previous = {
        "카드이용한도금액": 5_200_000,
        "잔액_B0M": 3_000_000,
        "청구금액_B0": 1_200_000,
    }

    result = calculate_derived_features(current, previous)

    assert math.isclose(result["f_사용률"], 0.8)
    assert math.isclose(result["f_잔액증가율"], 1 / 3)
    assert result["f_청구금액증가"] == 300_000
    assert result["f_카드가용비율"] == 0.75

