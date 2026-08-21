import pytest

from app.llm import RiskExplanationClient


def test_llm_validation_rejects_feature_not_sent_to_model():
    client = object.__new__(RiskExplanationClient)
    with pytest.raises(ValueError):
        client._validate(
            {
                "explanation": "입력 근거만 사용한 설명",
                "usedFeatureKeys": ["not_supplied"],
            },
            {"f_사용률"},
        )


def test_llm_validation_accepts_only_allowed_keys():
    client = object.__new__(RiskExplanationClient)
    explanation, keys = client._validate(
        {
            "explanation": "카드 한도 사용률 변화가 주요 요인으로 반영되었습니다.",
            "usedFeatureKeys": ["f_사용률"],
        },
        {"f_사용률"},
    )
    assert explanation
    assert keys == ["f_사용률"]
