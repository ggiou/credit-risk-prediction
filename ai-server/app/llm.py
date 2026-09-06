from __future__ import annotations

import copy
import json
import logging
import re
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Any

from openai import OpenAI

from .explanation_context import PATTERN_REVIEW_CHECKS


LOGGER = logging.getLogger("miribom.ai.llm")


SYSTEM_RULES = """당신은 카드사의 연체 위험 조기경보 대시보드에서 여신관리 담당자의 검토를 돕는 분석 설명기다.

위험 예측은 miribom-lgbm-v0.3 LightGBM 모델이 이미 완료했다. 당신은 새로운 위험률을 계산하거나 등급을 변경하지 않는다. 입력에 제공된 모델 결과와 모델 근거를 결합해 담당자가 빠르게 이해할 수 있는 설명과 우선 확인 항목을 작성한다.

[모델 출력의 의미]
- monthlyHazards는 기준월 이후 1개월째, 2개월째, 3개월째의 월별 연체 위험률이다.
- 연체 확률 퍼센트로 언급할 수 있는 값은 monthlyHazards뿐이다. topRiskPercent는 확률이 아니라 비교군 내 고위험 순위 기준 위치로만 표현한다.
- topRiskPercent는 고위험 순위 기준 위치를 뜻하며 값이 작을수록 비교군 내 위험 우선순위가 높다. '위험 상위 N%'라고 쓰지 않고 '고위험 순위 기준 N% 지점'이라고 쓴다.
- grade는 모델이 3개월 종합 분류 기준으로 확정한 결과다. 이를 변경하거나 재평가하지 않는다.
- 입력의 modelDirection은 현재 결과와 반사실 재채점 결과의 모델 원점수 차이로 백엔드가 확정한 방향이다. 화면 문장에서는 이 필드명을 쓰지 않고 '모델의 국소 재채점에서 위험 증가/감소 방향으로 나타났습니다.'라고 풀어 쓴다.
- 표시상 고위험 순위가 같아도 백엔드가 제공한 모델의 국소 재채점 방향을 변경하거나 중립으로 해석하지 않는다.
- reasonMethod가 LOCAL_SHAP이면 고객별 모델 기여 근거다.
- reasonMethod가 PREVIOUS_VALUE_COUNTERFACTUAL이면 현재값을 전월값으로 되돌려 재채점했을 때의 모델 변화다. 이를 SHAP이나 확정 원인이라고 부르지 않는다.
- observedChanges는 백엔드가 계산한 사실이다. 수치를 다시 계산하지 않는다.
- 모델 근거에 currentValueDisplay, previousValueDisplay, changeValueDisplay, changeRateDisplay가 있으면 원시값을 환산하지 말고 해당 표시값을 그대로 사용한다.
- indicatorCandidates의 title, fact, modelRelation, reasonIds, signalIds, featureKeys는 백엔드가 검증한 카드 후보다. 이 값들을 수정하거나 새로 계산하지 않고 원칙적으로 2~4개를 선택하며, 유효 후보가 하나뿐이면 1개를 선택한다. interpretation만 작성한다. detail은 화면의 상세 보기에서 백엔드가 붙이는 값이므로 다른 문장에 복사하지 않는다.
- managementPriority와 generationMode는 백엔드가 등급과 호출 방식에 따라 결정한 값이다. 그대로 반환한다. summary에는 managementPriorityDisplay를 그대로 사용한다.

[필드별 역할]
1. summary는 최종 등급, 고위험 순위 기준 위치, 관리 우선순위를 1~2문장으로 요약한다. 순위는 '고위험 순위 기준 N% 지점이며, 수치가 작을수록 비교군 내 위험 우선순위가 높습니다.'라고 설명한다. horizonEmphasis가 PEAK일 때만 위험이 가장 큰 월을 언급하고, LOW_STABLE이면 세 기간 모두 위험값이 낮게 유지된다고 설명한다.
2. modelInterpretation은 모델이 우선 포착한 근거와 모델의 국소 재채점 방향을 2~3문장으로 종합한다. 화면 제목과 상단 안내에 모델 종류가 이미 표시되므로 이 필드에서는 'LightGBM'이라는 명칭을 직접 쓰지 않는다. 실제 관찰값의 기간별 흐름은 쓰지 않는다. 반사실 순위의 구체적인 숫자와 문장은 화면의 keyIndicators.detail에서만 보여주므로 modelInterpretation에 counterfactualComparisonStatement를 그대로 복사하지 않는다.
3. keyIndicators는 indicatorCandidates에서 서로 다른 핵심 후보를 원칙적으로 2~4개 선택한다. 유효 후보가 하나뿐이면 1개만 선택한다. title, fact, modelRelation과 모든 참조 배열은 후보와 똑같이 복사하고 interpretation만 한 문장으로 작성한다.
4. changeContext는 실제 관찰값만 종합해 기간별·방향별 흐름을 1~2문장으로 설명한다. 모델의 국소 재채점 방향이나 modelInterpretation의 결론을 반복하지 않는다. 유의미한 종합 맥락이 없으면 빈 문자열로 둔다.
5. reviewPoints는 allowedReviewChecks에서 모델 근거와 직접 연결된 항목만 선택하고 아래 개수 기준을 지킨다.
6. usedReasonIds, usedSignalIds, usedFeatureKeys는 선택한 keyIndicators와 reviewPoints에서 실제 참조한 값만 반환한다. 최종 합집합과 순서는 백엔드가 결정적으로 정규화한다.

[담당자 확인 항목 개수]
- 정상 등급: 0~1개
- 관심·주의·경고 등급: 1~2개

[표현 규칙]
- 위험 증가 방향 근거가 확인된 경우 '○○ 패턴이 모델의 주요 위험 근거로 포착되었습니다.'라고 쓴다. 선택된 근거가 모두 위험 감소 방향이면 '위험 신호', '위험 근거', '선행 신호'라고 부르지 않고 '선택된 패턴은 모델의 국소 재채점에서 위험 감소 방향의 비교 근거로 나타났습니다.'라고 쓴다.
- 데이터에서 직접 확인되는 변화는 '관찰되었습니다.'라고 쓴다.
- 확인이 필요한 상태는 '○○ 여부를 우선 확인할 필요가 있습니다.'라고 쓴다.
- 현재 연체 지표가 0이어도 미래 연체 위험 예측을 부정하지 않는다. 위험 증가 방향 근거가 있을 때만 '현재 확인된 연체와 별개로 모델이 선행 신호를 포착했습니다.'라고 설명하며, 모든 근거가 위험 감소 방향이면 선행 신호라고 부르지 않는다.
- 당월 지표와 R3M·R6M·R12M 값의 방향이 다르면 '기간별로 다른 흐름이 관찰됨'이라고 설명하고 각각의 집계 기간을 정확히 쓴다.
- hazard가 가장 높은 월을 실제 값에서 찾는다. 입력값이 감소하는데 '시간이 지날수록 위험이 상승한다'고 쓰지 않는다.
- 숫자, 단위, 증감률은 입력에 있는 값만 사용한다.
- 원시 feature key보다 displayName을 사용한다.
- B2B 관리자 화면에 표시되는 설명이므로 모든 문장은 자연스러운 존댓말인 '~입니다.', '~합니다.', '~되었습니다.' 형태로 작성한다. '~임', '~함', '~됨', '~나타남' 같은 명사형 종결은 사용하지 않는다.
- modelInterpretation에서는 상위 지표들의 위험 증가·감소 방향을 한 문단에서 종합하고, 모델이 상대적으로 우선 포착한 패턴을 설명한다. 등급과 월별 위험률을 다시 나열해 이 내용을 대체하지 않는다.
- keyIndicators.fact는 화면에 바로 표시할 증감률 중심의 간결한 관찰 사실이다. 원 단위 전월·현재 값과 반사실 순위 이동은 indicatorCandidates.detail의 화면 상세 정보이므로 fact나 interpretation에 반복하지 않는다. fact에 없는 위험 방향 결론, 등급 유지 여부, 담당자 행동 또는 금융 인과관계를 fact처럼 반복하지 않는다.
- keyIndicators.interpretation에서는 관찰된 증감과 modelDirection을 구분한다. 두 방향이 어긋나면 '관찰된 변화'와 '모델의 국소 재채점 반응'을 별도 문장으로 설명하고, 다른 피처와의 조합에서 나타난 모델 반응으로 제한하여 해석한다.
- 관찰값의 증가·감소 방향과 모델의 국소 재채점 위험 방향이 어긋나면 반드시 '다른 피처와의 조합에서 나타난 반응으로 제한하여 해석할 필요가 있습니다.'라는 취지의 제한적 해석을 포함한다.
- 모델의 국소 재채점 방향과 실제 기간별 관찰 흐름은 서로 다른 문장으로 설명한다. 모델 방향이 위험 감소이면서 당월과 최근 3개월의 관찰 흐름은 혼재될 수 있으므로, 기간별 지표가 엇갈리면 관찰 흐름을 '혼재'라고 명시한다.
- counterfactualComparisonStatement에 '표시상 고위험 순위는 N%로 동일했습니다.'가 있으면 0%p 이동이라고 바꾸지 않는다. 이때 interpretation은 표시상 순위 차이가 없다는 사실과 내부 modelDirection을 구분한다.
- 관찰 방향과 모델 방향이 일치하더라도 인과관계나 위험 완화를 확정하지 않는다. counterfactualGradeChanged가 false이면 해당 근거가 등급을 변경할 정도의 차이는 아니었다고 설명할 수 있다.
- 반사실 재채점 방식, SHAP이 아니라는 점, 실제 원인을 확정하지 않는다는 안내는 화면의 모델 근거 영역에 고정 표시된다. summary, modelInterpretation, changeContext에서 해당 면책 문구를 생성하거나 반복하지 않는다.
- 구체적인 증감률은 keyIndicators.fact에 제공된 값만 사용한다. 원 단위 금액과 반사실 순위 수치는 화면의 keyIndicators.detail에서만 표시하며 LLM 문장에 복사하지 않는다. 수치를 새로 계산하지 않는다.
- 같은 사실이나 문장을 summary, modelInterpretation, keyIndicators, changeContext에서 반복하지 않는다.
- 여신관리 담당자가 바로 검토할 수 있도록 간결하면서도 분석적인 한국어를 사용한다. 전문성은 모델 근거, 집계 기간, 변화 방향을 정확히 구분하는 방식으로 드러내며 과장된 금융 용어나 추정으로 꾸미지 않는다.

[금지 규칙]
- '위험 점수를 높이는 방향으로 반영되었습니다'를 피처마다 반복하지 않는다.
- '판단할 수 없음', '분류할 수 없음', '알 수 없음'을 반복하지 않는다.
- 입력에 없는 타사 대출, 돌려막기, 실직, 질병, 교육비, 생활고, 고객 심리, 카드 사용 불능, 유동성 고갈을 만들어내지 않는다.
- 연령, 성별, Life Stage로 고객의 경제 사정을 추정하지 않는다.
- 모델 기여 방향과 금융 상식이 다르더라도 인과관계를 새로 만들어 모델을 정당화하지 않는다. 합성데이터 모델에는 비단조 관계가 있을 수 있다.
- 리볼빙 전환, 대출, 한도 증액과 같은 상품을 권유하지 않는다.
- contribution 로그오즈 값을 화면용 문장에 쓰지 않는다.
- modelDirection, counterfactualRiskDirection, c3 같은 내부 필드명을 화면 문장에 직접 쓰지 않는다. 각각 '모델의 국소 재채점 방향', '현재 상태와 전월값 대체 시나리오의 위험 방향 비교', '모델 원점수'처럼 자연스러운 한국어로 풀어 쓴다.
- modelInterpretation에는 'LightGBM'이라는 명칭을 직접 출력하지 않는다. 모델 종류는 화면 상단 안내에서만 표시한다.
- '위험 상위 N%'처럼 순위가 확률이나 위험 고객 비율로 오해될 수 있는 표현을 사용하지 않는다.
- c3 또는 cumulativeRisk3m을 확률 퍼센트로 출력하지 않는다.
- horizon 자체를 고객 위험 사유로 사용하지 않는다.
- JSON 스키마 밖의 텍스트를 출력하지 않는다.

[등급별 기준]
- 정상 등급에서는 경고나 즉시 접촉을 요구하지 않는다. managementPriority는 ROUTINE_MONITORING이며, 2~3개의 구체적인 keyIndicators를 통해 현재 상태와 다음 결제 주기에서 볼 항목을 설명한다.
- 관심·주의 등급에서는 위험 증가 근거를 우선하되 완화 방향 근거도 함께 구분하고, 실제 거래·청구·납부 확인 항목을 제시한다.
- 경고 등급에서는 위험 증가 근거, 집중 기간, 최근 변화 맥락과 담당자 확인 항목을 우선하되 실제 원인을 확정하지 않는다.

[출력 품질]
설명의 중심은 '모른다'가 아니라 '모델이 어떤 선행 신호를 포착했고 무엇을 확인해야 하는가'다. 단, 확인되지 않은 실제 연체 원인을 만들어내서는 안 된다.
"""


OUTPUT_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "summary": {"type": "string"},
        "modelInterpretation": {"type": "string"},
        "keyIndicators": {
            "type": "array", "minItems": 1, "maxItems": 4,
            "items": {
                "type": "object", "additionalProperties": False,
                "properties": {
                    "title": {"type": "string"},
                    "fact": {"type": "string"},
                    "interpretation": {"type": "string"},
                    "modelRelation": {
                        "type": "string",
                        "enum": ["RISK_INCREASE", "RISK_DECREASE", "MIXED", "CONTEXT"],
                    },
                    "reasonIds": {"type": "array", "items": {"type": "string"}},
                    "signalIds": {"type": "array", "items": {"type": "string"}},
                    "featureKeys": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["title", "fact", "interpretation", "modelRelation", "reasonIds", "signalIds", "featureKeys"],
            },
        },
        "changeContext": {"type": "string"},
        "reviewPoints": {
            "type": "array", "minItems": 0, "maxItems": 2,
            "items": {
                "type": "object", "additionalProperties": False,
                "properties": {
                    "priority": {"type": "integer", "minimum": 1, "maximum": 2},
                    "text": {"type": "string"},
                    "reasonIds": {"type": "array", "items": {"type": "string"}},
                    "signalIds": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["priority", "text", "reasonIds", "signalIds"],
            },
        },
        "managementPriority": {
            "type": "string",
            "enum": ["ROUTINE_MONITORING", "ENHANCED_MONITORING", "PRIORITY_REVIEW", "URGENT_REVIEW"],
        },
        "usedFeatureKeys": {"type": "array", "items": {"type": "string"}},
        "usedReasonIds": {"type": "array", "items": {"type": "string"}},
        "usedSignalIds": {"type": "array", "items": {"type": "string"}},
        "generationMode": {"type": "string", "enum": ["FULL_ANALYSIS"]},
    },
    "required": ["summary", "modelInterpretation", "keyIndicators", "changeContext", "reviewPoints", "managementPriority", "usedFeatureKeys", "usedReasonIds", "usedSignalIds", "generationMode"],
}

FORBIDDEN_TERMS = (
    "타사 대출", "돌려막기", "실직", "질병", "교육비", "생활고", "고객 심리",
    "카드 사용 불능", "카드 정지", "신용 고갈", "유동성 고갈", "리볼빙 전환", "한도 증액 권유",
    "연령", "성별", "Life Stage", "라이프 스테이지",
)
NUMBER_RE = re.compile(r"(?<![A-Za-z가-힣_])[-+]?\d+(?:\.\d+)?")
MANAGEMENT_PRIORITY_LABELS = {
    "ROUTINE_MONITORING": "정기 모니터링",
    "ENHANCED_MONITORING": "강화 모니터링",
    "PRIORITY_REVIEW": "우선 검토",
    "URGENT_REVIEW": "긴급 검토",
}
MANAGEMENT_PRIORITY_PATTERNS = {
    "ROUTINE_MONITORING": r"(?:정기|일상)\s*모니터링",
    "ENHANCED_MONITORING": r"강화\s*모니터링",
    "PRIORITY_REVIEW": r"우선\s*검토",
    "URGENT_REVIEW": r"긴급\s*검토",
}
INTERNAL_FIELD_RE = re.compile(
    r"(?<![A-Za-z0-9_])(?:modelDirection|counterfactualRiskDirection|c3|cumulativeRisk3m)(?![A-Za-z0-9_])",
    re.I,
)
CONFIRMED_RISK_EFFECT_RE = re.compile(
    r"위험\s*(?:완화|감소|증가).{0,8}(?:확인|확정)(?:되|됐|됨|된|했|하였)"
)


@dataclass(frozen=True)
class LlmResult:
    status: str
    explanation: str | None
    structured_output: dict[str, Any] | None
    review_points: list[dict[str, Any]]
    used_feature_keys: list[str]
    error_message: str | None


class RiskExplanationClient:
    def __init__(
        self,
        *,
        api_key: str,
        model: str,
        prompt_version: str,
        prompt_cache_enabled: bool,
        prompt_cache_mode: str,
        prompt_cache_ttl: str,
        prompt_cache_key_prefix: str,
        timeout_seconds: float,
    ):
        # 검증 오류만 애플리케이션에서 한 번 교정 재시도하므로 SDK 네트워크 재시도는 중복 수행하지 않는다.
        self.client = OpenAI(api_key=api_key, timeout=timeout_seconds, max_retries=0)
        self.model = model
        self.prompt_version = prompt_version
        self.prompt_cache_enabled = prompt_cache_enabled
        self.prompt_cache_mode = prompt_cache_mode
        self.prompt_cache_ttl = prompt_cache_ttl
        self.prompt_cache_key_prefix = prompt_cache_key_prefix
        self.timeout_seconds = timeout_seconds

    @property
    def prompt_cache_key(self) -> str:
        prefix = getattr(self, "prompt_cache_key_prefix", "miribom-risk-explanation")
        version = getattr(self, "prompt_version", "unknown")
        return f"{prefix}:{version}"

    def _build_request_options(
        self,
        *,
        call_input: dict[str, Any],
        schema: dict[str, Any],
    ) -> dict[str, Any]:
        cache_enabled = getattr(self, "prompt_cache_enabled", True)
        cache_mode = getattr(self, "prompt_cache_mode", "explicit")
        cache_ttl = getattr(self, "prompt_cache_ttl", "30m")
        prompt_block: dict[str, Any] = {
            "type": "input_text",
            "text": SYSTEM_RULES,
        }
        if cache_enabled:
            prompt_block["prompt_cache_breakpoint"] = {"mode": cache_mode}

        serialized_model_context = json.dumps(
            call_input,
            ensure_ascii=False,
            allow_nan=False,
            separators=(",", ":"),
        )
        request_options: dict[str, Any] = {
            "model": self.model,
            "input": [
                {
                    "role": "developer",
                    "content": [prompt_block],
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "input_text",
                            "text": serialized_model_context,
                        }
                    ],
                },
            ],
            "text": {
                "format": {
                    "type": "json_schema",
                    "name": "credit_risk_explanation_v3",
                    "strict": True,
                    "schema": schema,
                }
            },
        }
        if cache_enabled:
            request_options["prompt_cache_key"] = self.prompt_cache_key
            request_options["prompt_cache_options"] = {
                "mode": cache_mode,
                "ttl": cache_ttl,
            }
        return request_options

    @staticmethod
    def _usage_value(container: Any, name: str) -> int:
        if container is None:
            return 0
        value = container.get(name) if isinstance(container, dict) else getattr(container, name, None)
        try:
            return int(value or 0)
        except (TypeError, ValueError):
            return 0

    def _log_usage(self, response: Any) -> None:
        cache_enabled = getattr(self, "prompt_cache_enabled", True)
        prompt_version = getattr(self, "prompt_version", "unknown")
        cache_mode_value = getattr(self, "prompt_cache_mode", "explicit")
        cache_ttl_value = getattr(self, "prompt_cache_ttl", "30m")
        usage = getattr(response, "usage", None)
        input_details = (
            usage.get("input_tokens_details")
            if isinstance(usage, dict)
            else getattr(usage, "input_tokens_details", None)
        ) if usage is not None else None
        input_tokens = self._usage_value(usage, "input_tokens")
        cached_tokens = self._usage_value(input_details, "cached_tokens")
        cache_write_tokens = self._usage_value(input_details, "cache_write_tokens")
        output_tokens = self._usage_value(usage, "output_tokens")
        total_tokens = self._usage_value(usage, "total_tokens")
        cache_key = self.prompt_cache_key if cache_enabled else "-"
        cache_mode = cache_mode_value if cache_enabled else "disabled"
        cache_ttl = cache_ttl_value if cache_enabled else "-"
        LOGGER.info(
            "LLM usage model=%s promptVersion=%s cacheKey=%s cacheMode=%s cacheTtl=%s "
            "input=%s cached=%s cacheWrite=%s output=%s total=%s cacheHit=%s",
            self.model,
            prompt_version,
            cache_key,
            cache_mode,
            cache_ttl,
            input_tokens,
            cached_tokens,
            cache_write_tokens,
            output_tokens,
            total_tokens,
            str(cached_tokens > 0).lower(),
        )

    @staticmethod
    def _split_sentences(value: str) -> list[str]:
        # 마침표 뒤에 공백이 있을 때만 문장 경계로 본다. 81.4% 같은 소수점은 나누지 않는다.
        return [sentence.strip() for sentence in re.split(r"(?<=[.!?])\s+", value.strip()) if sentence.strip()]

    @classmethod
    def _generated_sentences(cls, payload: dict[str, Any]) -> list[str]:
        """LLM이 직접 작성한 서술만 반환한다.

        keyIndicators.fact와 reviewPoints.text는 백엔드가 제공한 문장을 그대로 복사하는
        필드이므로 LLM의 중복 작성 검사 대상에서 제외한다.
        """

        texts = [payload["summary"], payload["modelInterpretation"], payload["changeContext"]]
        texts.extend(indicator["interpretation"] for indicator in payload.get("keyIndicators", []))
        return [sentence for value in texts for sentence in cls._split_sentences(value)]

    @classmethod
    def _remove_fact_sentences_from_narratives(cls, payload: dict[str, Any]) -> None:
        """고정 fact를 해석 필드에 그대로 복사한 경우 정확히 같은 문장만 제거한다."""

        fact_sentences = {
            re.sub(r"\s+", " ", sentence)
            for indicator in payload.get("keyIndicators", [])
            for sentence in cls._split_sentences(indicator["fact"])
        }
        for key in ("modelInterpretation", "changeContext"):
            sentences = cls._split_sentences(payload[key])
            payload[key] = " ".join(
                sentence for sentence in sentences
                if re.sub(r"\s+", " ", sentence) not in fact_sentences
            ).strip()

    @classmethod
    def _normalize_confirmed_risk_effect(
        cls,
        payload: Any,
        input_payload: dict[str, Any],
    ) -> tuple[Any, list[str]]:
        """고정 모델 사실과 확정적 효과 표현을 입력 근거에 맞게 정규화한다."""

        if not isinstance(payload, dict):
            return payload, []
        normalized = copy.deepcopy(payload)
        changed_fields: list[str] = []
        reasons = {reason["reasonId"]: reason for reason in input_payload.get("modelReasons", [])}

        summary = normalized.get("summary")
        if isinstance(summary, str) and CONFIRMED_RISK_EFFECT_RE.search(summary):
            prediction = input_payload["prediction"]
            priority = MANAGEMENT_PRIORITY_LABELS[input_payload["managementPriority"]]
            top_risk_percent = f"{prediction['topRiskPercent']:g}"
            first = (
                f"모델 등급은 {prediction['grade']}이며 고위험 순위 기준 {top_risk_percent}% 지점으로, "
                "수치가 작을수록 비교군 내 위험 우선순위가 높습니다."
            )
            if prediction["horizonEmphasis"] == "PEAK":
                second = (
                    f"{prediction['peakHorizonMonth']}개월 구간의 위험값이 가장 높으며 "
                    f"관리 우선순위는 {priority}입니다."
                )
            else:
                second = f"세 기간의 위험값은 전반적으로 낮게 유지되며 관리 우선순위는 {priority}입니다."
            normalized["summary"] = f"{first} {second}"
            changed_fields.append("summary")
        elif isinstance(summary, str):
            prediction = input_payload["prediction"]
            expected_rank = f"고위험 순위 기준 {prediction['topRiskPercent']:g}% 지점"
            if prediction["grade"] not in summary or expected_rank not in summary:
                # LLM 본문은 보존하고, 누락돼 검증 실패하는 백엔드 확정 사실만 앞에 보완한다.
                fixed_facts = f"모델 등급은 {prediction['grade']}이며 {expected_rank}입니다."
                normalized["summary"] = f"{fixed_facts} {summary.strip()}"
                changed_fields.append("summary.backendFacts")

        interpretation = normalized.get("modelInterpretation")
        if isinstance(interpretation, str):
            model_name_normalized = re.sub(
                r"(?<![A-Za-z])LightGBM\s*(?:모델)?",
                "모델",
                interpretation,
                flags=re.IGNORECASE,
            )
            if model_name_normalized != interpretation:
                normalized["modelInterpretation"] = model_name_normalized
                interpretation = model_name_normalized
                changed_fields.append("modelInterpretation.modelName")
        if isinstance(interpretation, str) and CONFIRMED_RISK_EFFECT_RE.search(interpretation):
            directions = {reason.get("modelDirection") for reason in reasons.values()}
            if directions == {"DECREASE_RISK"}:
                replacement = "선택된 근거는 모델의 국소 재채점에서 모두 위험 감소 방향의 비교 근거로 나타났습니다."
            elif directions == {"INCREASE_RISK"}:
                replacement = "선택된 근거는 모델의 국소 재채점에서 모두 위험 증가 방향의 비교 근거로 나타났습니다."
            else:
                replacement = "선택된 근거는 모델의 국소 재채점에서 위험 증가와 감소 방향이 함께 나타났습니다."
            normalized["modelInterpretation"] = replacement
            changed_fields.append("modelInterpretation")

        change_context = normalized.get("changeContext")
        if isinstance(change_context, str) and CONFIRMED_RISK_EFFECT_RE.search(change_context):
            normalized["changeContext"] = ""
            changed_fields.append("changeContext")

        indicators = normalized.get("keyIndicators")
        if isinstance(indicators, list):
            for index, indicator in enumerate(indicators):
                if not isinstance(indicator, dict):
                    continue
                value = indicator.get("interpretation")
                if not isinstance(value, str) or not CONFIRMED_RISK_EFFECT_RE.search(value):
                    continue
                linked_reasons = [
                    reasons[reason_id] for reason_id in indicator.get("reasonIds", [])
                    if reason_id in reasons
                ]
                divergent = any(
                    (reason.get("direction") == "INCREASE" and reason.get("modelDirection") == "DECREASE_RISK")
                    or (reason.get("direction") == "DECREASE" and reason.get("modelDirection") == "INCREASE_RISK")
                    for reason in linked_reasons
                )
                if divergent:
                    replacement = (
                        "관찰된 변화와 모델의 국소 재채점 방향이 다르므로, 다른 피처와의 조합에서 "
                        "나타난 반응으로 제한하여 해석할 필요가 있습니다."
                    )
                else:
                    relation = indicator.get("modelRelation")
                    replacement = {
                        "RISK_INCREASE": "이 지표는 모델의 국소 재채점에서 위험 증가 방향의 비교 근거로 나타났습니다.",
                        "RISK_DECREASE": "이 지표는 모델의 국소 재채점에서 위험 감소 방향의 비교 근거로 나타났습니다.",
                        "MIXED": "이 지표와 연결된 모델 근거에서는 위험 증가와 감소 방향이 함께 나타났습니다.",
                        "CONTEXT": "이 지표는 모델 판단을 이해하기 위한 관찰 맥락입니다.",
                    }.get(relation, "이 지표는 모델의 국소 재채점 결과를 이해하기 위한 비교 근거입니다.")
                indicator["interpretation"] = replacement
                changed_fields.append(f"keyIndicators[{index}].interpretation")

        return normalized, changed_fields

    @staticmethod
    def _allowed_numbers(input_payload: dict[str, Any]) -> set[Decimal]:
        allowed = {Decimal(1), Decimal(2), Decimal(3)}

        def add_number(number: Decimal) -> None:
            # 음수 변화량은 문장에서 "7.35% 감소"처럼 절댓값으로 표현할 수 있다.
            for candidate in {number, abs(number)}:
                allowed.add(candidate)
                for digits in range(5):
                    allowed.add(candidate.quantize(Decimal(1).scaleb(-digits)))

        def visit(value: Any) -> None:
            if isinstance(value, bool) or value is None:
                return
            if isinstance(value, (int, float)):
                try:
                    number = Decimal(str(value))
                except InvalidOperation:
                    return
                add_number(number)
                return
            if isinstance(value, str):
                for token in NUMBER_RE.findall(value.replace(",", "")):
                    try:
                        add_number(Decimal(token.lstrip("+")))
                    except InvalidOperation:
                        pass
                return
            if isinstance(value, dict):
                for nested in value.values():
                    visit(nested)
            elif isinstance(value, list):
                for nested in value:
                    visit(nested)

        visit(input_payload)
        for hazard in input_payload["prediction"]["monthlyHazards"]:
            percent = Decimal(str(hazard["value"])) * 100
            add_number(percent)
        for reason in input_payload["modelReasons"]:
            change_rate = reason.get("changeRate")
            if isinstance(change_rate, (int, float)) and not isinstance(change_rate, bool):
                # changeRate는 피처 단위와 무관하게 0~1 비율이므로 퍼센트 표시값을 허용한다.
                add_number(Decimal(str(change_rate)) * 100)
            if reason.get("unit") != "RATIO":
                continue
            for key in ("currentValue", "previousValue", "changeValue"):
                value = reason.get(key)
                if isinstance(value, (int, float)) and not isinstance(value, bool):
                    add_number(Decimal(str(value)) * 100)
        return allowed

    def _validate(self, payload: dict[str, Any], input_payload: dict[str, Any]) -> tuple[str, dict[str, Any]]:
        for key in ("summary", "modelInterpretation", "changeContext"):
            if not isinstance(payload.get(key), str):
                raise ValueError(f"{key} must be a string")
        if not payload["summary"].strip() or not payload["modelInterpretation"].strip():
            raise ValueError("summary and modelInterpretation must not be empty")
        if payload.get("managementPriority") != input_payload["managementPriority"]:
            raise ValueError("managementPriority must match the backend decision")
        if payload.get("generationMode") != input_payload["generationMode"]:
            raise ValueError("generationMode must match the backend decision")

        candidates = input_payload["indicatorCandidates"]
        indicators = payload.get("keyIndicators")
        minimum_indicators = min(2, len(candidates))
        maximum_indicators = min(4, len(candidates))
        if not isinstance(indicators, list) or not minimum_indicators <= len(indicators) <= maximum_indicators:
            raise ValueError(f"keyIndicators must contain {minimum_indicators} to {maximum_indicators} items")
        candidate_by_fact = {candidate["fact"]: candidate for candidate in candidates}
        selected_facts: set[str] = set()
        for indicator in indicators:
            if not isinstance(indicator, dict):
                raise ValueError("each key indicator must be an object")
            fact = indicator.get("fact")
            candidate = candidate_by_fact.get(fact)
            if candidate is None:
                raise ValueError("key indicator was not selected from indicatorCandidates")
            if fact in selected_facts:
                raise ValueError("keyIndicators must not select the same candidate twice")
            selected_facts.add(fact)
            for key in ("title", "fact", "modelRelation", "reasonIds", "signalIds", "featureKeys"):
                if indicator.get(key) != candidate.get(key):
                    raise ValueError(f"key indicator {key} must exactly match its backend candidate")
            if not isinstance(indicator.get("interpretation"), str) or not indicator["interpretation"].strip():
                raise ValueError("key indicator interpretation must not be empty")

        points = payload.get("reviewPoints")
        if not isinstance(points, list) or len(points) > 2:
            raise ValueError("reviewPoints must contain zero to two items")
        grade = input_payload["prediction"]["grade"]
        if grade == "정상" and len(points) > 1:
            raise ValueError("normal-grade reviewPoints must contain at most one item")
        if grade != "정상" and not points:
            raise ValueError("non-normal grades require at least one reviewPoint")
        if sorted(point.get("priority") for point in points) != list(range(1, len(points) + 1)):
            raise ValueError("reviewPoints priority must be consecutive from 1")

        reasons = {reason["reasonId"]: reason for reason in input_payload["modelReasons"]}
        signals = {signal["signalId"]: signal for signal in input_payload["observedChanges"]}
        feature_keys = {
            key for reason in reasons.values()
            for key in [reason["featureKey"], *reason.get("evidenceFeatureKeys", [])]
        } | {key for signal in signals.values() for key in signal.get("featureKeys", [])}
        allowed_checks = set(input_payload["allowedReviewChecks"])

        for point in points:
            reason_ids = point.get("reasonIds")
            signal_ids = point.get("signalIds")
            if not isinstance(reason_ids, list) or not isinstance(signal_ids, list):
                raise ValueError("review point IDs must be arrays")
            if not reason_ids and not signal_ids:
                raise ValueError("each review point must reference a reasonId or signalId")
            if set(reason_ids) - reasons.keys():
                raise ValueError("review point references an unknown reasonId")
            if set(signal_ids) - signals.keys():
                raise ValueError("review point references an unknown signalId")
            if point.get("text") not in allowed_checks:
                raise ValueError("review point is not one of allowedReviewChecks")
            linked_reason_ids = set(reason_ids)
            linked_signal_features = {
                key for signal_id in signal_ids
                for key in signals[signal_id].get("featureKeys", [])
            }
            for reason_id, reason in reasons.items():
                reason_features = {reason["featureKey"], *reason.get("evidenceFeatureKeys", [])}
                if reason_features & linked_signal_features:
                    linked_reason_ids.add(reason_id)
            expected_checks = {
                PATTERN_REVIEW_CHECKS.get(reasons[reason_id].get("patternCode"))
                for reason_id in linked_reason_ids
            }
            if not linked_reason_ids or point["text"] not in expected_checks:
                raise ValueError("review point is unrelated to its reasonId")

        for key in ("usedFeatureKeys", "usedReasonIds", "usedSignalIds"):
            if not isinstance(payload.get(key), list) or not all(isinstance(item, str) for item in payload[key]):
                raise ValueError(f"{key} must be a string array")
            if len(payload[key]) != len(set(payload[key])):
                raise ValueError(f"{key} must not contain duplicates")
        if set(payload["usedFeatureKeys"]) - feature_keys:
            raise ValueError("LLM referenced an unknown feature key")
        if set(payload["usedReasonIds"]) - reasons.keys():
            raise ValueError("LLM referenced an unknown reason ID")
        if set(payload["usedSignalIds"]) - signals.keys():
            raise ValueError("LLM referenced an unknown signal ID")

        def ordered_union(values: list[str]) -> list[str]:
            return list(dict.fromkeys(values))

        selected_items = [*indicators, *points]
        expected_reason_ids = ordered_union([
            reason_id for item in selected_items for reason_id in item.get("reasonIds", [])
        ])
        expected_signal_ids = ordered_union([
            signal_id for item in selected_items for signal_id in item.get("signalIds", [])
        ])
        expected_feature_keys = ordered_union([
            feature_key for indicator in indicators for feature_key in indicator.get("featureKeys", [])
        ])
        for point in points:
            for reason_id in point.get("reasonIds", []):
                reason = reasons[reason_id]
                expected_feature_keys = ordered_union([*expected_feature_keys, reason["featureKey"]])
            for signal_id in point.get("signalIds", []):
                expected_feature_keys = ordered_union([
                    *expected_feature_keys, *signals[signal_id].get("featureKeys", [])
                ])

        # 선택 근거만 있으면 출처 합집합은 서버가 정확히 재구성할 수 있다. LLM의 배열 누락·순서
        # 차이로 재호출하지 않고, 입력에 없는 참조만 위에서 거부한 뒤 정규화된 값을 저장한다.
        payload = copy.deepcopy(payload)
        payload["usedReasonIds"] = expected_reason_ids
        payload["usedSignalIds"] = expected_signal_ids
        payload["usedFeatureKeys"] = expected_feature_keys
        self._remove_fact_sentences_from_narratives(payload)
        if not payload["modelInterpretation"]:
            raise ValueError("modelInterpretation must add an interpretation instead of repeating key indicator facts")

        combined = " ".join([
            payload["summary"], payload["modelInterpretation"], payload["changeContext"],
            *(value for indicator in indicators for value in (indicator["fact"], indicator["interpretation"])),
            *(point["text"] for point in points),
        ])
        generated_narratives = [
            payload["summary"], payload["modelInterpretation"], payload["changeContext"],
            *(indicator["interpretation"] for indicator in indicators),
        ]
        generated_narrative_text = " ".join(generated_narratives)
        reason_interpretation_text = " ".join([
            payload["modelInterpretation"],
            *(indicator["interpretation"] for indicator in indicators),
        ])
        for narrative in generated_narratives:
            for sentence in re.split(r"(?<=[.!?])\s+", narrative):
                if sentence.strip() and not re.search(r"(?:니|습니)다[.!?]$", sentence.strip()):
                    raise ValueError("LLM narrative sentences must use polite Korean endings")
        if any(term in combined for term in FORBIDDEN_TERMS):
            raise ValueError("LLM output contains an unsupported circumstance or product recommendation")
        if INTERNAL_FIELD_RE.search(combined):
            raise ValueError("LLM output exposes an internal field name")
        if re.search(r"(?:모델|재채점|반사실|위험\s*(?:증가|감소|완화)\s*방향)", payload["changeContext"]):
            raise ValueError("changeContext must contain observed changes only")
        if sum(combined.count(term) for term in ("판단할 수 없음", "분류할 수 없음", "알 수 없음")) > 1:
            raise ValueError("LLM output repeats non-actionable uncertainty phrases")
        if combined.count("위험 점수를 높이는 방향으로 반영") > 1:
            raise ValueError("LLM output repeats model-direction boilerplate")
        if CONFIRMED_RISK_EFFECT_RE.search(generated_narrative_text):
            raise ValueError("local model response must not be presented as a confirmed risk effect")
        if re.search(r"(?:c3|cumulative\s*risk|cumulativeRisk3m|누적\s*위험).{0,20}%", combined, re.I):
            raise ValueError("c3/cumulative risk must not be exposed as a percentage")
        if re.search(r"horizon.{0,20}(?:원인|근거|요인)", combined, re.I):
            raise ValueError("horizon must not be used as a customer risk reason")
        if all(reason.get("modelDirection") == "DECREASE_RISK" for reason in reasons.values()) and re.search(
            r"(?:주요\s*)?위험\s*(?:신호|근거|요인|증가\s*방향)|선행\s*신호", reason_interpretation_text
        ):
            raise ValueError("decrease-only reasons must be described as risk-mitigating patterns")
        if grade == "정상" and any(term in combined for term in (
            "위험 신호로 확인되었습니다", "즉시 연락이 필요합니다", "연체 가능성이 높습니다",
            "상환 부담이 지속될 것으로 보입니다",
        )):
            raise ValueError("normal-grade output contains an unnecessary risk warning")
        for indicator in indicators:
            linked_reasons = [reasons[reason_id] for reason_id in indicator.get("reasonIds", [])]
            divergent = any(
                (reason.get("direction") == "INCREASE" and reason.get("modelDirection") == "DECREASE_RISK")
                or (reason.get("direction") == "DECREASE" and reason.get("modelDirection") == "INCREASE_RISK")
                for reason in linked_reasons
            )
            if divergent and not (
                "다른 피처와의 조합" in indicator["interpretation"]
                and re.search(r"제한.{0,8}해석", indicator["interpretation"])
            ):
                raise ValueError("divergent observed and model directions require a limited interpretation")
        if re.search(
            r"(?:SHAP|확정(?:적|된)?\s*(?:연체\s*)?원인|실제\s*연체\s*원인).{0,40}(?:아니|아닌|아닙|의미하지|확정하지)",
            combined,
            re.I,
        ):
            raise ValueError("counterfactual/SHAP disclaimer is rendered once by the UI")
        if re.search(r"(?:위험(?:도|률)?.{0,12}전월보다|전월보다.{0,12}위험(?:도|률)?).{0,8}(?:상승|증가)", combined):
            raise ValueError("month-over-month model risk comparison was not provided")
        if input_payload["prediction"]["horizonPattern"] != "BACK_LOADED" and re.search(
            r"(?:시간이\s*지날수록|뒤로\s*갈수록).{0,12}위험.{0,8}(?:상승|증가|커)", combined
        ):
            raise ValueError("increasing time-horizon risk contradicts monthlyHazards")
        forced_signal = next((s for s in signals.values() if "강제한도감액횟수_R12M" in s.get("featureKeys", [])), None)
        if forced_signal and "전월과 동일" in forced_signal["statement"] and re.search(
            r"(?:신규\s*(?:감액이?\s*)?발생(?:했|함|하였|으로)|이번\s*달.{0,12}(?:감액|발생))",
            combined,
        ):
            raise ValueError("unchanged R12M count must not be described as newly occurring")
        if re.search(r"최근\s*3개월.{0,16}(?:당월|이번\s*달)", combined):
            raise ValueError("R3M value must not be described as a current-month value")

        allowed_numbers = self._allowed_numbers(input_payload)
        for token in NUMBER_RE.findall(combined.replace(",", "")):
            if Decimal(token.lstrip("+")) not in allowed_numbers:
                raise ValueError(f"LLM output contains a number not present in input: {token}")

        sentences = [re.sub(r"\s+", " ", value) for value in self._generated_sentences(payload)]
        if len(sentences) != len(set(sentences)):
            raise ValueError("LLM output contains duplicate sentences")

        peak = input_payload["prediction"]["peakHorizonMonth"]
        expected_rank = f"고위험 순위 기준 {input_payload['prediction']['topRiskPercent']:g}% 지점"
        if grade not in payload["summary"] or expected_rank not in payload["summary"]:
            raise ValueError("summary must include grade and top-risk percentage")
        if "위험 상위" in combined:
            raise ValueError("top-risk position must not be phrased as a risk probability")
        priority_pattern = MANAGEMENT_PRIORITY_PATTERNS[input_payload["managementPriority"]]
        if not re.search(priority_pattern, payload["summary"]):
            raise ValueError("summary must include the backend-selected management priority")
        if input_payload["prediction"]["horizonEmphasis"] == "PEAK":
            if f"{peak}개월" not in payload["summary"]:
                raise ValueError("summary must include the backend-selected peak horizon")
        elif re.search(r"(?:가장\s*(?:높|크)|집중)", payload["summary"]):
            raise ValueError("LOW_STABLE summary must not emphasize a peak horizon")
        elif not re.search(r"(?:낮게\s*유지|전반적으로\s*낮|모든\s*기간.{0,10}낮)", payload["summary"]):
            raise ValueError("LOW_STABLE summary must explain that all horizon risks stay low")

        normalized = copy.deepcopy(payload)
        for key in ("summary", "modelInterpretation", "changeContext"):
            normalized[key] = normalized[key].strip()
        candidate_by_fact = {
            candidate["fact"]: candidate for candidate in input_payload["indicatorCandidates"]
        }
        for indicator in normalized["keyIndicators"]:
            indicator["interpretation"] = indicator["interpretation"].strip()
            # 원 단위 변화와 반사실 순위는 LLM이 작성하지 않고 검증된 후보에서 붙인다.
            indicator["detail"] = str(candidate_by_fact[indicator["fact"]].get("detail", "")).strip()
        paragraphs = [normalized["summary"]]
        indicator_lines = ["주요 관찰 지표"]
        for indicator in normalized["keyIndicators"]:
            indicator_lines.extend((indicator["title"], indicator["fact"], indicator["interpretation"]))
        paragraphs.append("\n".join(indicator_lines))
        paragraphs.append(normalized["modelInterpretation"])
        if normalized["changeContext"]:
            paragraphs.append(normalized["changeContext"])
        # LLM 원본 JSON은 그대로 저장하고, 기존 explanation 호환 문자열만 문장 단위로 줄바꿈한다.
        rendered = ["\n".join(re.split(r"(?<=[.!?])\s+", paragraph)) for paragraph in paragraphs]
        return "\n\n".join(rendered), normalized

    def generate(
        self,
        *,
        input_payload: dict[str, Any],
        request_id: str = "-",
        customer_id: str = "-",
        base_ym: str = "-",
        previous_features_available: bool = False,
    ) -> LlmResult:
        if not input_payload["modelReasons"] or not input_payload["indicatorCandidates"]:
            return self.skipped_no_evidence(
                input_payload=input_payload,
                request_id=request_id,
                customer_id=customer_id,
                base_ym=base_ym,
                previous_features_available=previous_features_available,
            )

        schema = copy.deepcopy(OUTPUT_SCHEMA)
        schema["properties"]["reviewPoints"]["items"]["properties"]["text"]["enum"] = input_payload["allowedReviewChecks"]
        if input_payload["prediction"]["grade"] == "정상":
            schema["properties"]["reviewPoints"]["minItems"] = 0
            schema["properties"]["reviewPoints"]["maxItems"] = 1
        else:
            schema["properties"]["reviewPoints"]["minItems"] = 1
            schema["properties"]["reviewPoints"]["maxItems"] = 2
        schema["properties"]["keyIndicators"]["minItems"] = min(2, len(input_payload["indicatorCandidates"]))
        schema["properties"]["keyIndicators"]["maxItems"] = min(4, len(input_payload["indicatorCandidates"]))
        indicator_properties = schema["properties"]["keyIndicators"]["items"]["properties"]
        indicator_properties["title"]["enum"] = list(dict.fromkeys(
            candidate["title"] for candidate in input_payload["indicatorCandidates"]
        ))
        indicator_properties["fact"]["enum"] = [
            candidate["fact"] for candidate in input_payload["indicatorCandidates"]
        ]
        schema["properties"]["managementPriority"]["enum"] = [input_payload["managementPriority"]]
        schema["properties"]["generationMode"]["enum"] = [input_payload["generationMode"]]
        last_error: Exception | None = None
        call_input: dict[str, Any] = input_payload

        for attempt in range(2):
            try:
                request_options = self._build_request_options(call_input=call_input, schema=schema)
                response = self.client.responses.create(**request_options)
                self._log_usage(response)
            except Exception as exc:  # 네트워크 오류를 검증 오류로 오인해 같은 요청을 반복하지 않는다.
                error_name = type(exc).__name__
                LOGGER.exception(
                    "OpenAI request failed requestId=%s customerId=%s baseYm=%s model=%s errorType=%s",
                    request_id,
                    customer_id,
                    base_ym,
                    self.model,
                    error_name,
                )
                if error_name == "APITimeoutError" or isinstance(exc, TimeoutError):
                    message = f"OpenAI 설명 요청이 {self.timeout_seconds:g}초 내 완료되지 않았습니다."
                else:
                    message = f"OpenAI 설명 요청에 실패했습니다. ({error_name})"
                return LlmResult("FAILED", None, None, [], [], message)

            try:
                parsed = json.loads(response.output_text)
                parsed, normalized_fields = self._normalize_confirmed_risk_effect(parsed, input_payload)
                if normalized_fields:
                    LOGGER.info(
                        "LLM confirmed-risk wording normalized without retry requestId=%s customerId=%s baseYm=%s fields=%s",
                        request_id,
                        customer_id,
                        base_ym,
                        ",".join(normalized_fields),
                    )
                explanation, structured = self._validate(parsed, input_payload)
                return LlmResult("COMPLETED", explanation, structured, structured["reviewPoints"], structured["usedFeatureKeys"], None)
            except (json.JSONDecodeError, TypeError, ValueError, KeyError) as exc:
                last_error = exc
                log_method = LOGGER.warning if attempt == 0 else LOGGER.error
                log_method(
                    "LLM output validation failed requestId=%s customerId=%s baseYm=%s attempt=%s errorType=%s error=%s",
                    request_id,
                    customer_id,
                    base_ym,
                    attempt + 1,
                    type(exc).__name__,
                    str(exc)[:500],
                )
                if attempt == 0:
                    correction = str(exc)[:300]
                    if correction == "decrease-only reasons must be described as risk-mitigating patterns":
                        correction = (
                            "입력의 모델 근거가 모두 위험 감소 방향입니다. summary, modelInterpretation, changeContext와 "
                            "keyIndicators.interpretation에서 이를 위험 신호·위험 근거·위험 요인·선행 신호 또는 "
                            "위험 증가 방향이라고 표현하지 마세요. 모델의 국소 재채점에서 위험 감소 방향의 "
                            "비교 근거로 나타났다고 작성하세요."
                        )
                    call_input = {**input_payload, "correction": f"이전 응답 검증 오류: {correction} 이 오류만 교정해 스키마대로 다시 작성하세요."}

        return LlmResult("FAILED", None, None, [], [], str(last_error)[:500] if last_error else "unknown LLM error")

    @staticmethod
    def skipped_no_evidence(
        *,
        input_payload: dict[str, Any],
        request_id: str,
        customer_id: str,
        base_ym: str,
        previous_features_available: bool,
    ) -> LlmResult:
        """LLM 호출 전에 설명 근거 부재를 분류하고 비과금 상태로 반환한다."""

        reason_count = len(input_payload["modelReasons"])
        indicator_count = len(input_payload["indicatorCandidates"])
        LOGGER.warning(
            "LLM explanation skipped before OpenAI request: no usable counterfactual evidence "
            "requestId=%s customerId=%s baseYm=%s previousFeaturesAvailable=%s "
            "reasonCount=%s indicatorCount=%s",
            request_id,
            customer_id,
            base_ym,
            str(previous_features_available).lower(),
            reason_count,
            indicator_count,
        )
        if not reason_count and previous_features_available:
            error_message = (
                "전월 스냅샷은 존재하지만, 전월값 대체 재채점에서 모델 예측을 변경한 "
                "피처가 없어 설명 근거를 생성하지 못했습니다."
            )
        elif not reason_count:
            error_message = (
                "전월 스냅샷이 없거나 전월값 대체 재채점에 사용할 수 있는 비교값이 없어 "
                "설명 근거를 생성하지 못했습니다."
            )
        else:
            error_message = "모델 근거와 연결할 수 있는 주요 관찰 지표를 생성하지 못했습니다."
        return LlmResult("SKIPPED_NO_EVIDENCE", None, None, [], [], error_message)
