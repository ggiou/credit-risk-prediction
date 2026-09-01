from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from openai import OpenAI


SYSTEM_RULES = """당신은 금융회사 내부 관리자 화면에 표시할 LightGBM 연체 위험 분석 설명 생성기다.
관리자가 모델 판단 근거를 빠르게 이해할 수 있도록 다음 규칙을 반드시 지켜라.
1. LightGBM이 계산한 위험률, 위험등급, 백분위를 다시 계산하거나 변경하지 않는다.
2. 입력된 prediction과 riskFactors만 근거로 사용한다.
3. summary는 여러 지표에서 함께 관찰되는 변화와 모델 판단을 한 문장으로 요약한다.
4. changeItems는 2~4개를 권장하며, 실제 변화가 있는 지표를 우선하고 riskFactors의 입력 순서를 유지한다.
5. changeItems의 각 문장은 지표명으로 시작하고 이전값, 현재값, 변화량을 단위에 맞게 간결하게 설명한다.
6. changeItems에는 '위험 점수를 높이는 방향' 같은 동일한 결론을 지표마다 반복하지 않는다.
7. modelInterpretation에서 선택한 지표들의 모델 기여 방향을 한 번만 종합해 설명한다.
8. direction은 현재 지표 값이 모델 점수에 기여한 방향이며 전월 대비 증감이 위험 변화를 일으켰다는 뜻이 아니다.
9. 값의 증감과 모델 기여 방향을 인과관계로 연결하거나, 단순히 값이 감소했다는 이유로 위험이 변했다고 추정하지 않는다.
10. 입력에 없는 자금 유동성, 상환 능력, 한도 소진, 카드 정지, 대출, 소득, 직업, 소비 목적, 생활 사정과 고객 의도를 추정하지 않는다.
11. 실제 연체 원인이나 인과관계로 단정하지 않는다.
12. modelInterpretation의 마지막에는 전체 입력값 조합에 대한 모델 판단이며 실제 연체 원인을 뜻하지 않는다는 점을 간결하게 밝힌다.
13. '제공된 예측상', '주요 위험 기여 요인으로' 같은 서두와 NORMAL 등 내부 영문 코드를 출력하지 않는다.
14. summary, changeItems, modelInterpretation에는 글머리표나 줄 번호를 넣지 않는다.
15. 권고사항, 행동 지침, 금융상품 추천을 생성하지 않는다.
16. usedFeatureKeys에는 각 changeItems에 대응하는 riskFactors.featureKey를 같은 순서로 한 개씩 넣는다.
17. 지정된 JSON 스키마 외의 텍스트를 출력하지 않는다.
"""


OUTPUT_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "summary": {"type": "string"},
        "changeItems": {
            "type": "array",
            "items": {"type": "string"},
        },
        "modelInterpretation": {"type": "string"},
        "usedFeatureKeys": {
            "type": "array",
            "items": {"type": "string"},
        },
    },
    "required": ["summary", "changeItems", "modelInterpretation", "usedFeatureKeys"],
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
        summary = payload.get("summary")
        items = payload.get("changeItems")
        interpretation = payload.get("modelInterpretation")
        keys = payload.get("usedFeatureKeys")
        if not isinstance(summary, str) or not summary.strip():
            raise ValueError("summary must be a non-empty string")
        if not isinstance(items, list) or not items or not all(
            isinstance(item, str) and item.strip() for item in items
        ):
            raise ValueError("changeItems must be a non-empty string array")
        if not isinstance(interpretation, str) or not interpretation.strip():
            raise ValueError("modelInterpretation must be a non-empty string")
        if not isinstance(keys, list) or not all(isinstance(key, str) for key in keys):
            raise ValueError("usedFeatureKeys must be a string array")
        if len(items) != len(keys):
            raise ValueError("changeItems and usedFeatureKeys must have the same length")
        if len(keys) != len(set(keys)):
            raise ValueError("usedFeatureKeys must not contain duplicates")
        unknown = set(keys) - allowed_feature_keys
        if unknown:
            raise ValueError(f"LLM referenced unknown feature keys: {sorted(unknown)}")
        change_lines = [f"- {item.strip().lstrip('-• ').strip()}" for item in items]
        explanation = "\n".join([
            summary.strip().lstrip('-• ').strip(),
            *change_lines,
            interpretation.strip().lstrip('-• ').strip(),
        ])
        return explanation, keys

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
                print(f"call fail LLM - message : {str(last_error)}")

        return LlmResult(
            status="FAILED",
            explanation=None,
            used_feature_keys=[],
            error_message=str(last_error)[:500] if last_error else "unknown LLM error",
        )
