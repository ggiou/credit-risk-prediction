import pytest

from app.llm import RiskExplanationClient


def test_llm_validation_rejects_feature_not_sent_to_model():
    client = object.__new__(RiskExplanationClient)
    with pytest.raises(ValueError):
        client._validate(
            {
                "summary": "모델 판단 요약",
                "changeItems": ["입력 근거만 사용한 설명"],
                "modelInterpretation": "전체 입력값 조합에 대한 모델 판단입니다.",
                "usedFeatureKeys": ["not_supplied"],
            },
            {"f_사용률"},
        )


def test_llm_validation_accepts_only_allowed_keys():
    client = object.__new__(RiskExplanationClient)
    explanation, keys = client._validate(
        {
            "summary": "카드 한도 사용률 변화가 확인되었습니다.",
            "changeItems": ["카드 한도 사용률은 전월보다 증가했습니다."],
            "modelInterpretation": "현재 값은 위험 점수를 높이는 방향으로 반영됐으며 실제 연체 원인을 뜻하지 않습니다.",
            "usedFeatureKeys": ["f_사용률"],
        },
        {"f_사용률"},
    )
    assert explanation == (
        "카드 한도 사용률 변화가 확인되었습니다.\n"
        "- 카드 한도 사용률은 전월보다 증가했습니다.\n"
        "현재 값은 위험 점수를 높이는 방향으로 반영됐으며 실제 연체 원인을 뜻하지 않습니다."
    )
    assert keys == ["f_사용률"]


def test_llm_validation_rejects_duplicate_feature_keys():
    client = object.__new__(RiskExplanationClient)
    with pytest.raises(ValueError, match="must not contain duplicates"):
        client._validate(
            {
                "summary": "모델 판단 요약",
                "changeItems": ["첫 번째 설명", "두 번째 설명"],
                "modelInterpretation": "전체 입력값 조합에 대한 모델 판단입니다.",
                "usedFeatureKeys": ["f_사용률", "f_사용률"],
            },
            {"f_사용률"},
        )


def test_llm_validation_rejects_item_and_key_count_mismatch():
    client = object.__new__(RiskExplanationClient)
    with pytest.raises(ValueError, match="must have the same length"):
        client._validate(
            {
                "summary": "모델 판단 요약",
                "changeItems": ["첫 번째 설명", "두 번째 설명"],
                "modelInterpretation": "전체 입력값 조합에 대한 모델 판단입니다.",
                "usedFeatureKeys": ["첫번째피처"],
            },
            {"첫번째피처", "두번째피처"},
        )


def test_llm_validation_normalizes_item_markers_and_line_breaks():
    client = object.__new__(RiskExplanationClient)
    explanation, keys = client._validate(
        {
            "summary": "잔액과 청구 관련 지표가 함께 감소했습니다.",
            "changeItems": [
                "- 월중 평균잔액은 모델 판단에 반영되었습니다.",
                "• 기준월 청구금액은 전월보다 감소했습니다.",
            ],
            "modelInterpretation": "현재 값들은 위험 점수를 높이는 방향으로 반영됐으며 실제 연체 원인을 뜻하지 않습니다.",
            "usedFeatureKeys": ["월중평잔", "청구금액_B0"],
        },
        {"월중평잔", "청구금액_B0"},
    )

    assert explanation == (
        "잔액과 청구 관련 지표가 함께 감소했습니다.\n"
        "- 월중 평균잔액은 모델 판단에 반영되었습니다.\n"
        "- 기준월 청구금액은 전월보다 감소했습니다.\n"
        "현재 값들은 위험 점수를 높이는 방향으로 반영됐으며 실제 연체 원인을 뜻하지 않습니다."
    )
    assert keys == ["월중평잔", "청구금액_B0"]
