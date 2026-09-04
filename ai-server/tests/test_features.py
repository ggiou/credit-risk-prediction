import math

from app.features import derive_features


def test_derived_features_follow_spec_and_keep_missing_as_none():
    current = {
        "잔액_B0M": 800.0,
        "카드이용한도금액": 1000.0,
        "잔액_현금서비스_B0M": 80.0,
        "잔액_현금서비스_B1M": 50.0,
        "잔액_카드론_B0M": 160.0,
        "잔액_카드론_B1M": 100.0,
        "잔액_리볼빙일시불이월_B0M": 40.0,
        "카드이용한도금액_B1M": 900.0,
        "이용가능카드수_신용": 3,
        "유효카드수_신용": 4,
        "청구금액_B0": 300.0,
    }
    previous = {
        "잔액_B0M": 500.0,
        "카드이용한도금액": 1000.0,
        "청구금액_B0": 200.0,
    }

    got = derive_features(current, previous)

    assert got["f_사용률"] == 0.8
    assert got["f_현금서비스비중"] == 0.1
    assert got["f_카드론비중"] == 0.2
    assert got["f_리볼빙비중"] == 0.05
    assert got["f_현금서비스증가"] == 30.0
    assert got["f_카드론증가"] == 60.0
    assert got["f_한도변화"] == 100.0
    assert got["f_잔액증가율"] == 0.6
    assert math.isclose(got["f_사용률변화"], 0.3)
    assert got["f_청구금액증가"] == 100.0
    assert got["f_카드가용비율"] == 0.75

    missing = derive_features(
        {"잔액_B0M": 100.0, "카드이용한도금액": 0},
        None,
    )
    assert missing["f_사용률"] is None
    assert missing["f_잔액증가율"] is None


def test_numeric_sentinel_string_is_missing_without_dropping_categories():
    got = derive_features({"연령": "40대", "잔액_B0M": "-9999"}, None)

    assert got["연령"] == "40대"
    assert got["잔액_B0M"] is None
