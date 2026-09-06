"""_unit_for 회귀 테스트.

'강제한도감액횟수_R12M'에는 '한도'가 들어 있어 AMOUNT를 먼저 판정하면
3회가 "3원"으로 표시된다. COUNT 토큰을 먼저 봐야 한다.
"""

import pytest

from app.model_bundle import ModelBundle


@pytest.mark.parametrize(
    "feature_key,expected",
    [
        # 회귀 대상: '한도'/'금액'을 품은 카운트 피처
        ("강제한도감액횟수_R12M", "COUNT"),
        ("자발한도감액횟수_R12M", "COUNT"),
        ("한도증액횟수_R12M", "COUNT"),
        ("한도심사요청건수", "COUNT"),
        ("한도요청거절건수", "COUNT"),
        # 진짜 금액
        ("강제한도감액금액_R12M", "AMOUNT"),
        ("카드이용한도금액", "AMOUNT"),
        ("CA한도금액", "AMOUNT"),
        ("청구금액_B0", "AMOUNT"),
        ("잔액_B0M", "AMOUNT"),
        ("월중평잔", "AMOUNT"),
        # 카운트
        ("유효카드수_신용", "COUNT"),
        ("이용가능카드수_신용", "COUNT"),
        ("연체건수_R6M", "COUNT"),
        ("상환개월수_결제일_R3M", "COUNT"),
        ("입회경과개월수_신용", "COUNT"),
        # 비율 / 플래그
        ("f_사용률", "RATIO"),
        ("f_카드가용비율", "RATIO"),
        ("RV약정청구율", "RATIO"),
        ("시장단기연체여부_R3M", "FLAG"),
        ("회원여부_연체", "FLAG"),
    ],
)
def test_unit_for(feature_key, expected):
    assert ModelBundle._unit_for(feature_key) == expected


def test_count_precedence_over_amount():
    """횟수 피처는 금액 토큰을 포함해도 절대 AMOUNT가 되지 않는다."""

    for key in ("강제한도감액횟수_R12M", "자발한도감액횟수_R12M", "한도증액횟수_R12M"):
        assert "한도" in key
        assert ModelBundle._unit_for(key) != "AMOUNT"
