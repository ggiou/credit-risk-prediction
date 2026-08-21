from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from openai import OpenAI


SYSTEM_RULES = """당신은 금융회사 내부 연체 위험 분석 화면의 설명 생성기다.
다음 규칙을 반드시 지켜라.
1. 제공된 LightGBM 위험률과 위험등급을 다시 계산하거나 변경하지 않는다.
2. 제공된 riskFactors의 값, 변화량, 기여도만 판단 근거로 사용한다.
3. 입력에 없는 소득, 직업, 소비 목적, 생활 사정, 상환 능력, 고객 의도를 추정하지 않는다.
4. 권고사항, 행동 지침, 금융상품 추천을 생성하지 않는다.
5. 설명은 2~3문장으로 작성한다.
6. usedFeatureKeys에는 실제 설명에 사용한 riskFactors.featureKey만 넣는다.
7. 지정된 JSON 스키마 외의 텍스트를 출력하지 않는다.
"""


OUTPUT_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "explanation": {"type": "string", "minLength": 1},
        "usedFeatureKeys": {
            "type": "array",
            "items": {"type": "string"},
            "uniqueItems": True,
        },
    },
    "required": ["explanation", "usedFeatureKeys"],
}


@dataclass(frozen=True)
class LlmResult:
    status: str
    explanation: str | None
    used_feature_keys: list[str]
    error_message: str | None


class RiskExplanationClient:
    def __init__(self, *, api_key: str, model: str, timeout_seconds: float):
        self.client = OpenAI(api_key=api_key, timeout=timeout_seconds)
        self.model = model

    def _validate(
        self,
        payload: dict[str, Any],
        allowed_feature_keys: set[str],
    ) -> tuple[str, list[str]]:
        explanation = payload.get("explanation")
        keys = payload.get("usedFeatureKeys")
        if not isinstance(explanation, str) or not explanation.strip():
            raise ValueError("LLM explanation is empty")
        if not isinstance(keys, list) or not all(isinstance(key, str) for key in keys):
            raise ValueError("usedFeatureKeys must be a string array")
        unknown = set(keys) - allowed_feature_keys
        if unknown:
            raise ValueError(f"LLM referenced unknown feature keys: {sorted(unknown)}")
        return explanation.strip(), keys

    def generate(
        self,
        *,
        prediction: dict[str, Any],
        risk_factors: list[dict[str, Any]],
    ) -> LlmResult:
        allowed = {factor["featureKey"] for factor in risk_factors}
        input_payload = {
            "prediction": prediction,
            "riskFactors": risk_factors,
        }
        last_error: Exception | None = None

        # Initial call + one retry for schema/content validation failure.
        for _ in range(2):
            try:
                response = self.client.responses.create(
                    model=self.model,
                    instructions=SYSTEM_RULES,
                    input=json.dumps(input_payload, ensure_ascii=False, allow_nan=False),
                    text={
                        "format": {
                            "type": "json_schema",
                            "name": "credit_risk_explanation",
                            "strict": True,
                            "schema": OUTPUT_SCHEMA,
                        }
                    },
                )
                parsed = json.loads(response.output_text)
                explanation, keys = self._validate(parsed, allowed)
                return LlmResult(
                    status="COMPLETED",
                    explanation=explanation,
                    used_feature_keys=keys,
                    error_message=None,
                )
            except Exception as exc:  # LLM failure must not discard model prediction.
                last_error = exc

        return LlmResult(
            status="FAILED",
            explanation=None,
            used_feature_keys=[],
            error_message=str(last_error)[:500] if last_error else "unknown LLM error",
        )
