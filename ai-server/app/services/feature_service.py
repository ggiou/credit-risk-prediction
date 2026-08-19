"""학습 코드와 공유해야 하는 파생 피처 계산 규칙을 제공한다."""

import math
from typing import Any


SENTINEL_VALUES = {-99999999, -9999999, -999999, -99999, -9999}


def clean_number(value: Any) -> float | None:
    """원천 센티널과 숫자가 아닌 값을 결측값으로 정리한다."""

    # bool은 숫자의 하위 자료형이지만 모델 숫자 피처로는 0과 1을 사용할 수 있다.
    if value is None:
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if number in SENTINEL_VALUES or math.isnan(number) or math.isinf(number):
        return None
    return number


def safe_divide(numerator: float | None, denominator: float | None) -> float | None:
    """분모가 없거나 0인 비율 계산을 결측값으로 처리한다."""

    # 임의의 0을 넣으면 실제 0%와 계산 불가 상태가 섞이므로 None을 유지한다.
    if numerator is None or denominator in (None, 0):
        return None
    return numerator / denominator


def difference(current: float | None, previous: float | None) -> float | None:
    """두 값이 모두 존재할 때만 변화량을 계산한다."""

    # 전월이 없으면 증가량도 추정하지 않는다.
    if current is None or previous is None:
        return None
    return current - previous


def calculate_derived_features(
    current: dict[str, Any], previous: dict[str, Any] | None
) -> dict[str, float | None]:
    """현재·이전 월 원천값으로 확정된 파생 피처 11개를 계산한다."""

    # 명세의 한글 원천 키를 그대로 사용해 학습 코드와 서빙 코드의 열 의미를 맞춘다.
    previous = previous or {}
    credit_limit = clean_number(current.get("카드이용한도금액"))
    balance = clean_number(current.get("잔액_B0M"))
    cash_advance = clean_number(current.get("잔액_현금서비스_B0M"))
    card_loan = clean_number(current.get("잔액_카드론_B0M"))
    revolving = clean_number(current.get("잔액_리볼빙일시불이월_B0M"))

    previous_balance = clean_number(previous.get("잔액_B0M"))
    previous_limit = clean_number(previous.get("카드이용한도금액"))
    usage = safe_divide(balance, credit_limit)
    previous_usage = safe_divide(previous_balance, previous_limit)

    return {
        "f_사용률": usage,
        "f_현금서비스비중": safe_divide(cash_advance, balance),
        "f_카드론비중": safe_divide(card_loan, balance),
        "f_리볼빙비중": safe_divide(revolving, balance),
        "f_현금서비스증가": difference(
            cash_advance, clean_number(current.get("잔액_현금서비스_B1M"))
        ),
        "f_카드론증가": difference(
            card_loan, clean_number(current.get("잔액_카드론_B1M"))
        ),
        "f_한도변화": difference(
            credit_limit, clean_number(current.get("카드이용한도금액_B1M"))
        ),
        "f_카드가용비율": safe_divide(
            clean_number(current.get("이용가능카드수_신용")),
            clean_number(current.get("유효카드수_신용")),
        ),
        "f_잔액증가율": safe_divide(
            difference(balance, previous_balance), previous_balance
        ),
        "f_사용률변화": difference(usage, previous_usage),
        "f_청구금액증가": difference(
            clean_number(current.get("청구금액_B0")),
            clean_number(previous.get("청구금액_B0")),
        ),
    }

