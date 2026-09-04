from __future__ import annotations

from math import isfinite
from typing import Any

SENTINELS = {-99999999, -9999999, -999999, -99999, -9999}

DERIVED_FEATURES = (
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
)


def _missing(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, (int, float)):
        return not isfinite(float(value)) or value in SENTINELS
    if isinstance(value, str):
        try:
            numeric = float(value)
        except ValueError:
            return False
        return not isfinite(numeric) or numeric in SENTINELS
    return False


def clean(value: Any) -> Any:
    return None if _missing(value) else value


def number(features: dict[str, Any] | None, key: str) -> float | None:
    if not features:
        return None
    value = clean(features.get(key))
    if value is None or isinstance(value, bool):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def safe_div(numerator: float | None, denominator: float | None) -> float | None:
    if numerator is None or denominator is None or denominator == 0:
        return None
    return numerator / denominator


def safe_sub(left: float | None, right: float | None) -> float | None:
    if left is None or right is None:
        return None
    return left - right


def derive_features(
    current: dict[str, Any],
    previous: dict[str, Any] | None,
) -> dict[str, Any]:
    """
    Reuses the feature formulas fixed in the project DB/API specification.
    Missing/sentinel values remain missing; they are never replaced with zero.
    """
    out = {key: clean(value) for key, value in current.items()}

    balance = number(current, "잔액_B0M")
    limit_amount = number(current, "카드이용한도금액")
    cash = number(current, "잔액_현금서비스_B0M")
    cash_b1 = number(current, "잔액_현금서비스_B1M")
    loan = number(current, "잔액_카드론_B0M")
    loan_b1 = number(current, "잔액_카드론_B1M")
    revolving = number(current, "잔액_리볼빙일시불이월_B0M")
    limit_b1 = number(current, "카드이용한도금액_B1M")
    available_cards = number(current, "이용가능카드수_신용")
    valid_cards = number(current, "유효카드수_신용")

    usage = safe_div(balance, limit_amount)
    out["f_사용률"] = usage
    out["f_현금서비스비중"] = safe_div(cash, balance)
    out["f_카드론비중"] = safe_div(loan, balance)
    out["f_리볼빙비중"] = safe_div(revolving, balance)
    out["f_현금서비스증가"] = safe_sub(cash, cash_b1)
    out["f_카드론증가"] = safe_sub(loan, loan_b1)
    out["f_한도변화"] = safe_sub(limit_amount, limit_b1)
    out["f_카드가용비율"] = safe_div(available_cards, valid_cards)

    prev_balance = number(previous, "잔액_B0M")
    prev_limit = number(previous, "카드이용한도금액")
    prev_usage = safe_div(prev_balance, prev_limit)
    prev_bill = number(previous, "청구금액_B0")
    current_bill = number(current, "청구금액_B0")

    if previous is None:
        out["f_잔액증가율"] = None
        out["f_사용률변화"] = None
        out["f_청구금액증가"] = None
    else:
        balance_delta = safe_sub(balance, prev_balance)
        out["f_잔액증가율"] = safe_div(balance_delta, prev_balance)
        out["f_사용률변화"] = safe_sub(usage, prev_usage)
        out["f_청구금액증가"] = safe_sub(current_bill, prev_bill)

    return out
