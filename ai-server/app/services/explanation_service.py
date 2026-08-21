"""구조화된 모델 결과만 사용해 OpenAI 설명을 생성한다."""

import json

import httpx

from app.core.config import Settings
from app.schemas.prediction import LlmResult, PredictionValues, RiskFactor


class ExplanationService:
    """OpenAI Responses API 호출과 출력 검증을 담당한다."""

    def __init__(self, settings: Settings):
        """LLM 설정을 보관한다."""

        self.settings = settings

    @property
    def configured(self) -> bool:
        """API 키와 모델명이 모두 설정되었는지 반환한다."""

        return bool(self.settings.openai_api_key and self.settings.openai_model)

    async def explain(
        self,
        prediction: PredictionValues,
        risk_factors: list[RiskFactor],
        prompt_version: str,
        generate: bool,
    ) -> tuple[str | None, list[str], LlmResult]:
        """위험률과 주요 피처 범위 안에서만 자연어 설명을 생성한다."""

        if not generate:
            return None, [], LlmResult(
                status="NOT_REQUESTED",
                promptVersion=prompt_version,
                errorMessage=None,
            )
        if not self.configured:
            # 설정 누락을 성공처럼 숨기지 않고 부분 성공으로 저장할 수 있게 FAILED를 반환한다.
            return None, [], LlmResult(
                status="FAILED",
                promptVersion=prompt_version,
                errorMessage="OPENAI_API_KEY 또는 OPENAI_MODEL이 설정되지 않았습니다.",
            )

        try:
            result = await self._call_openai(prediction, risk_factors)
            explanation = str(result["explanation"]).strip()
            allowed_keys = {factor.feature_key for factor in risk_factors}
            used_keys = [key for key in result.get("usedFeatureKeys", []) if key in allowed_keys]
            if not explanation:
                raise ValueError("LLM 설명이 비어 있습니다.")
            return explanation, used_keys, LlmResult(
                status="COMPLETED",
                promptVersion=prompt_version,
                errorMessage=None,
            )
        except (httpx.HTTPError, KeyError, ValueError, json.JSONDecodeError) as exception:
            # LLM 실패는 LightGBM 위험률을 버리지 않고 Spring이 PARTIAL로 저장하도록 상태만 반환한다.
            return None, [], LlmResult(
                status="FAILED",
                promptVersion=prompt_version,
                errorMessage=str(exception)[:500],
            )

    async def _call_openai(
        self,
        prediction: PredictionValues,
        risk_factors: list[RiskFactor],
    ) -> dict:
        """OpenAI Responses API에 구조화된 모델 결과를 전달한다."""

        facts = {
            "prediction": prediction.model_dump(by_alias=True),
            "riskFactors": [factor.model_dump(by_alias=True) for factor in risk_factors],
        }
        prompt = (
            "당신은 금융회사 BO용 설명 생성기입니다. "
            "입력된 위험률과 위험 요인만 설명하고 값을 변경하거나 고객 상황을 추정하지 마세요. "
            "권고 조치는 작성하지 마세요. JSON으로 explanation과 usedFeatureKeys만 반환하세요.\n"
            + json.dumps(facts, ensure_ascii=False)
        )
        headers = {
            "Authorization": f"Bearer {self.settings.openai_api_key}",
            "Content-Type": "application/json",
        }
        body = {
            "model": self.settings.openai_model,
            "input": prompt,
        }
        async with httpx.AsyncClient(timeout=self.settings.openai_timeout_seconds) as client:
            response = await client.post("https://api.openai.com/v1/responses", headers=headers, json=body)
            response.raise_for_status()
        payload = response.json()
        output_text = payload.get("output_text") or self._extract_output_text(payload)
        return json.loads(output_text)

    def _extract_output_text(self, payload: dict) -> str:
        """Responses API의 중첩 output에서 최초 텍스트를 추출한다."""

        for item in payload.get("output", []):
            for content in item.get("content", []):
                if content.get("type") == "output_text" and content.get("text"):
                    return str(content["text"])
        raise ValueError("OpenAI 응답에서 output_text를 찾을 수 없습니다.")
