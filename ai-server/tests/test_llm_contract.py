import copy
import json
import re
from types import SimpleNamespace

import pytest

from app.llm import RiskExplanationClient, SYSTEM_RULES


def dynamic_request_payload(request):
    return json.loads(request["input"][1]["content"][0]["text"])


def llm_input():
    return {
        "modelContext": {
            "modelVersion": "miribom-lgbm-v0.3",
            "promptVersion": "v3.3",
            "predictionSource": "LIGHTGBM_JSON",
            "dataType": "PUBLIC_SYNTHETIC_DEMO",
            "target": "기준월 이후 1·2·3개월째 연체 발생 위험",
        },
        "prediction": {
            "grade": "주의", "topRiskPercent": 0.33,
            "monthlyHazards": [
                {"month": 1, "value": 0.02786, "valueDisplay": "2.79%"},
                {"month": 2, "value": 0.01332, "valueDisplay": "1.33%"},
                {"month": 3, "value": 0.00733, "valueDisplay": "0.73%"},
            ],
            "peakHorizonMonth": 1, "horizonPattern": "FRONT_LOADED", "horizonEmphasis": "PEAK",
        },
        "managementPriority": "PRIORITY_REVIEW",
        "generationMode": "FULL_ANALYSIS",
        "modelReasons": [{
            "reasonId": "R1", "featureKey": "f_카드가용비율", "displayName": "이용 가능 카드 비율",
            "modelDirection": "INCREASE_RISK", "rank": 1,
            "reasonMethod": "PREVIOUS_VALUE_COUNTERFACTUAL",
            "currentValue": 0.0, "previousValue": 1.0, "changeValue": -1.0, "unit": "RATIO",
            "counterfactualGrade": "정상", "currentTopRiskPercent": 0.33,
            "counterfactualTopRiskPercent": 4.7, "topRiskPercentDifference": 4.37,
            "counterfactualRiskDirection": "CURRENT_MORE_RISKY", "counterfactualGradeChanged": True,
            "counterfactualComparisonStatement": (
                "이용 가능 카드 비율을 전월값으로 대체한 재채점에서는 고위험 순위가 "
                "현재 0.3%에서 4.7%로 4.4%p 이동했습니다."
            ),
            "evidenceFeatureKeys": ["이용가능카드수_신용", "f_카드가용비율"],
            "patternCode": "CREDIT_AVAILABILITY",
        }],
        "observedChanges": [{
            "signalId": "S1", "statement": "최근 12개월 강제 한도 감액 횟수는 전월과 동일합니다.",
            "featureKeys": ["강제한도감액횟수_R12M"], "relationToModel": "CONTEXT",
        }],
        "indicatorCandidates": [
            {
                "indicatorId": "K1", "title": "카드 이용 가능 상태",
                "fact": (
                    "이용 가능 카드 비율을 전월값으로 대체한 재채점에서는 고위험 순위가 "
                    "현재 0.3%에서 4.7%로 4.4%p 이동했습니다."
                ),
                "modelRelation": "RISK_INCREASE", "reasonIds": ["R1"], "signalIds": [],
                "featureKeys": ["f_카드가용비율", "이용가능카드수_신용"],
            },
            {
                "indicatorId": "K2", "title": "카드 이용 가능 상태",
                "fact": "최근 12개월 강제 한도 감액 횟수는 전월과 동일합니다.",
                "modelRelation": "CONTEXT", "reasonIds": [], "signalIds": ["S1"],
                "featureKeys": ["강제한도감액횟수_R12M"],
            },
        ],
        "allowedReviewChecks": ["강제 한도 감액 발생 시점과 사용 가능 카드 상태 확인"],
    }


def valid_output():
    input_payload = llm_input()
    indicators = []
    for candidate, interpretation in zip(input_payload["indicatorCandidates"], (
        "현재 카드 이용 가능 상태가 모델 순위에 영향을 준 비교 근거입니다.",
        "기존 한도 감액 이력은 신규 발생과 구분해 확인해야 합니다.",
    )):
        indicator = {key: copy.deepcopy(value) for key, value in candidate.items() if key != "indicatorId"}
        indicator["interpretation"] = interpretation
        indicators.append(indicator)
    return {
        "summary": (
            "모델 등급은 주의이며 고위험 순위 기준 0.33% 지점으로, 수치가 작을수록 "
            "비교군 내 위험 우선순위가 높습니다. 1개월 구간의 우선 검토가 필요합니다."
        ),
        "modelInterpretation": "모델은 카드 이용 가능 상태 패턴을 위험 증가 방향의 우선 근거로 포착했습니다.",
        "keyIndicators": indicators,
        "changeContext": "카드 이용 가능 상태와 기존 한도 조정 이력을 함께 점검할 필요가 있습니다.",
        "reviewPoints": [{
            "priority": 1, "text": "강제 한도 감액 발생 시점과 사용 가능 카드 상태 확인",
            "reasonIds": ["R1"], "signalIds": ["S1"],
        }],
        "managementPriority": "PRIORITY_REVIEW",
        "usedFeatureKeys": ["f_카드가용비율", "이용가능카드수_신용", "강제한도감액횟수_R12M"],
        "usedReasonIds": ["R1"], "usedSignalIds": ["S1"], "generationMode": "FULL_ANALYSIS",
    }


def test_validation_accepts_structured_output_and_renders_legacy_explanation():
    output = valid_output()
    explanation, structured = object.__new__(RiskExplanationClient)._validate(output, llm_input())
    indicator_section = "주요 관찰 지표\n" + "\n".join(
        value for indicator in output["keyIndicators"]
        for value in (indicator["title"], indicator["fact"], indicator["interpretation"])
    )
    expected = "\n\n".join(
        "\n".join(re.split(r"(?<=[.!?])\s+", value))
        for value in (output["summary"], indicator_section, output["modelInterpretation"], output["changeContext"])
    )
    assert explanation == expected
    assert structured["reviewPoints"][0]["reasonIds"] == ["R1"]


def test_validation_removes_backend_fact_repeated_in_model_interpretation():
    output = valid_output()
    repeated_fact = output["keyIndicators"][0]["fact"]
    output["modelInterpretation"] += " " + repeated_fact

    explanation, structured = object.__new__(RiskExplanationClient)._validate(output, llm_input())

    assert structured["modelInterpretation"] == (
        "모델은 카드 이용 가능 상태 패턴을 위험 증가 방향의 우선 근거로 포착했습니다."
    )
    assert explanation.count(repeated_fact) == 1


def test_validation_still_rejects_duplicate_llm_generated_sentences():
    output = valid_output()
    output["modelInterpretation"] = output["summary"]

    with pytest.raises(ValueError, match="duplicate sentences"):
        object.__new__(RiskExplanationClient)._validate(output, llm_input())


def test_normal_low_stable_output_allows_no_review_point():
    input_payload = llm_input()
    input_payload["prediction"].update(grade="정상", topRiskPercent=98.7, horizonEmphasis="LOW_STABLE")
    input_payload["managementPriority"] = "ROUTINE_MONITORING"
    input_payload["modelReasons"][0]["modelDirection"] = "DECREASE_RISK"
    input_payload["indicatorCandidates"][0]["modelRelation"] = "RISK_DECREASE"
    output = valid_output()
    output["summary"] = (
        "모델 등급은 정상이며 고위험 순위 기준 98.7% 지점으로, 수치가 작을수록 비교군 내 "
        "위험 우선순위가 높습니다. 세 기간의 위험값은 전반적으로 낮게 유지되어 정기 모니터링 대상입니다."
    )
    output["modelInterpretation"] = "모델은 카드 이용 가능 상태를 위험 완화 방향의 비교 근거로 포착했습니다."
    output["keyIndicators"][0]["modelRelation"] = "RISK_DECREASE"
    output["reviewPoints"] = []
    output["managementPriority"] = "ROUTINE_MONITORING"

    explanation, structured = object.__new__(RiskExplanationClient)._validate(output, input_payload)

    assert "낮게 유지" in explanation
    assert structured["reviewPoints"] == []


def test_normal_priority_accepts_natural_routine_monitoring_synonym():
    input_payload = llm_input()
    input_payload["prediction"].update(grade="정상", topRiskPercent=98.7, horizonEmphasis="LOW_STABLE")
    input_payload["managementPriority"] = "ROUTINE_MONITORING"
    input_payload["modelReasons"][0]["modelDirection"] = "DECREASE_RISK"
    input_payload["indicatorCandidates"][0]["modelRelation"] = "RISK_DECREASE"
    output = valid_output()
    output["summary"] = (
        "모델 등급은 정상이며 고위험 순위 기준 98.7% 지점으로, 수치가 작을수록 비교군 내 "
        "위험 우선순위가 높습니다. 세 기간의 위험값이 낮게 유지되어 관리 우선순위는 일상 모니터링입니다."
    )
    output["modelInterpretation"] = "모델은 카드 이용 가능 상태를 위험 완화 방향의 비교 근거로 포착했습니다."
    output["keyIndicators"][0]["modelRelation"] = "RISK_DECREASE"
    output["reviewPoints"] = []
    output["managementPriority"] = "ROUTINE_MONITORING"

    _, structured = object.__new__(RiskExplanationClient)._validate(output, input_payload)

    assert structured["managementPriority"] == "ROUTINE_MONITORING"


def test_validation_rejects_modified_indicator_fact():
    output = valid_output()
    output["keyIndicators"][0]["fact"] += " 임의 사실입니다."
    with pytest.raises(ValueError, match="indicatorCandidates"):
        object.__new__(RiskExplanationClient)._validate(output, llm_input())


def test_validation_normalizes_unused_or_missing_source_references():
    output = valid_output()
    output["usedFeatureKeys"].remove("강제한도감액횟수_R12M")

    _, structured = object.__new__(RiskExplanationClient)._validate(output, llm_input())

    assert structured["usedFeatureKeys"] == [
        "f_카드가용비율", "이용가능카드수_신용", "강제한도감액횟수_R12M"
    ]


def test_validation_rejects_risk_signal_when_all_reasons_mitigate_risk():
    input_payload = llm_input()
    input_payload["modelReasons"][0]["modelDirection"] = "DECREASE_RISK"
    with pytest.raises(ValueError, match="risk-mitigating patterns"):
        object.__new__(RiskExplanationClient)._validate(valid_output(), input_payload)


def test_decrease_only_validation_does_not_reject_backend_fixed_fact_text():
    input_payload = llm_input()
    input_payload["modelReasons"][0]["modelDirection"] = "DECREASE_RISK"
    input_payload["indicatorCandidates"][0]["modelRelation"] = "RISK_DECREASE"
    input_payload["indicatorCandidates"][0]["fact"] += " 위험 신호 관련 관찰 문구입니다."
    output = valid_output()
    output["modelInterpretation"] = "모델은 카드 이용 가능 상태를 위험 감소 방향의 비교 근거로 포착했습니다."
    output["keyIndicators"][0]["modelRelation"] = "RISK_DECREASE"
    output["keyIndicators"][0]["fact"] = input_payload["indicatorCandidates"][0]["fact"]

    _, structured = object.__new__(RiskExplanationClient)._validate(output, input_payload)

    assert structured["keyIndicators"][0]["fact"].endswith("관찰 문구입니다.")


def test_decrease_only_reasons_allow_peak_risk_signal_in_summary():
    input_payload = llm_input()
    input_payload["modelReasons"][0]["modelDirection"] = "DECREASE_RISK"
    input_payload["indicatorCandidates"][0]["modelRelation"] = "RISK_DECREASE"
    output = valid_output()
    output["summary"] = (
        "모델 등급은 주의이며 고위험 순위 기준 0.33% 지점으로, 수치가 작을수록 비교군 내 "
        "위험 우선순위가 높습니다. 위험 신호는 1개월 구간에서 가장 높아 관리 우선순위는 우선 검토입니다."
    )
    output["modelInterpretation"] = "모델은 카드 이용 가능 상태를 위험 감소 방향의 비교 근거로 포착했습니다."
    output["keyIndicators"][0]["modelRelation"] = "RISK_DECREASE"

    _, structured = object.__new__(RiskExplanationClient)._validate(output, input_payload)

    assert "위험 신호는 1개월" in structured["summary"]


def test_validation_rejects_counterfactual_disclaimer_rendered_by_ui():
    output = valid_output()
    output["modelInterpretation"] += " 해당 결과는 고객별 확정 원인이나 SHAP 기여가 아닙니다."
    with pytest.raises(ValueError, match="rendered once by the UI"):
        object.__new__(RiskExplanationClient)._validate(output, llm_input())


def test_validation_rejects_noun_form_sentence_endings():
    output = valid_output()
    output["modelInterpretation"] = "모델은 카드 이용 가능 상태 패턴을 우선 근거로 포착함."
    with pytest.raises(ValueError, match="polite Korean endings"):
        object.__new__(RiskExplanationClient)._validate(output, llm_input())


def test_validation_rejects_internal_field_name_in_display_narrative():
    output = valid_output()
    output["modelInterpretation"] = "각 재채점에서 modelDirection은 위험 감소로 일관되었습니다."

    with pytest.raises(ValueError, match="internal field name"):
        object.__new__(RiskExplanationClient)._validate(output, llm_input())


def test_validation_rejects_model_conclusion_in_change_context():
    output = valid_output()
    output["changeContext"] = "관찰 흐름은 혼재되어 있으며 모델의 재채점은 위험 감소 방향입니다."

    with pytest.raises(ValueError, match="observed changes only"):
        object.__new__(RiskExplanationClient)._validate(output, llm_input())


def test_validation_requires_limited_interpretation_for_divergent_direction():
    input_payload = llm_input()
    input_payload["modelReasons"][0].update(direction="INCREASE", modelDirection="DECREASE_RISK")
    input_payload["indicatorCandidates"][0]["modelRelation"] = "RISK_DECREASE"
    output = valid_output()
    output["modelInterpretation"] = "선택된 근거는 모델의 국소 재채점에서 위험 감소 방향으로 나타났습니다."
    output["keyIndicators"][0]["modelRelation"] = "RISK_DECREASE"
    output["keyIndicators"][0]["interpretation"] = "관찰된 값은 증가했지만 모델 반응은 위험 감소 방향으로 나타났습니다."

    with pytest.raises(ValueError, match="limited interpretation"):
        object.__new__(RiskExplanationClient)._validate(output, input_payload)


def test_validation_accepts_limited_interpretation_for_divergent_direction():
    input_payload = llm_input()
    input_payload["modelReasons"][0].update(direction="INCREASE", modelDirection="DECREASE_RISK")
    input_payload["indicatorCandidates"][0]["modelRelation"] = "RISK_DECREASE"
    output = valid_output()
    output["modelInterpretation"] = "선택된 근거는 모델의 국소 재채점에서 위험 감소 방향으로 나타났습니다."
    output["keyIndicators"][0]["modelRelation"] = "RISK_DECREASE"
    output["keyIndicators"][0]["interpretation"] = (
        "관찰된 변화와 모델의 국소 재채점 방향이 다릅니다. "
        "다른 피처와의 조합에서 나타난 반응으로 제한하여 해석할 필요가 있습니다."
    )

    _, structured = object.__new__(RiskExplanationClient)._validate(output, input_payload)

    assert "제한하여 해석" in structured["keyIndicators"][0]["interpretation"]


@pytest.mark.parametrize(
    ("mutate", "message"),
    [
        (lambda output: output.update(usedReasonIds=["R404"]), "unknown reason ID"),
        (lambda output: output["reviewPoints"].extend(copy.deepcopy(output["reviewPoints"]) * 2), "zero to two"),
        (lambda output: output.update(changeContext="c3 누적 위험은 12%입니다."), "internal field name"),
        (lambda output: output.update(modelInterpretation="horizon이 고객 위험 근거입니다."), "horizon"),
        (lambda output: output.update(changeContext="이번 달 강제 한도 감액이 신규 발생했습니다."), "unchanged R12M"),
        (lambda output: output.update(changeContext="생활고로 카드 사용 불능 상태입니다."), "unsupported circumstance"),
        (lambda output: output.update(changeContext="최근 3개월 청구금액은 당월 1% 증가했습니다."), "R3M value"),
        (lambda output: output.update(changeContext="관찰되지 않은 비율은 77.77%입니다."), "number not present"),
        (lambda output: output.update(changeContext="전월보다 위험률이 1% 상승했습니다."), "model risk comparison"),
        (lambda output: output.update(changeContext="시간이 지날수록 위험이 커집니다."), "time-horizon risk"),
        (lambda output: output.update(changeContext="위험 완화가 확인되었습니다."), "confirmed risk effect"),
        (lambda output: output.update(changeContext="위험 상위 0.33%입니다."), "risk probability"),
    ],
)
def test_validation_rejects_unsupported_output(mutate, message):
    output = valid_output()
    mutate(output)
    with pytest.raises(ValueError, match=message):
        object.__new__(RiskExplanationClient)._validate(output, llm_input())


def test_timeout_fails_once_without_correction_retry():
    class APITimeoutError(Exception):
        pass

    class TimeoutResponses:
        def __init__(self):
            self.calls = 0

        def create(self, **kwargs):
            self.calls += 1
            raise APITimeoutError("Request timed out")

    responses = TimeoutResponses()
    client = object.__new__(RiskExplanationClient)
    client.client = SimpleNamespace(responses=responses)
    client.model = "test-model"
    client.timeout_seconds = 60
    result = client.generate(input_payload=llm_input())

    assert result.status == "FAILED"
    assert result.structured_output is None
    assert result.error_message == "OpenAI 설명 요청이 60초 내 완료되지 않았습니다."
    assert responses.calls == 1


def test_no_counterfactual_effect_skips_openai_request_with_precise_message():
    input_payload = llm_input()
    input_payload["modelReasons"] = []

    class ResponsesMustNotBeCalled:
        def __init__(self):
            self.calls = 0

        def create(self, **kwargs):
            self.calls += 1
            raise AssertionError("OpenAI Responses API must not be called without model evidence")

    responses = ResponsesMustNotBeCalled()
    client = object.__new__(RiskExplanationClient)
    client.client = SimpleNamespace(responses=responses)
    client.model = "test-model"
    client.timeout_seconds = 60

    result = client.generate(
        input_payload=input_payload,
        request_id="test-request",
        customer_id="SYN_10001",
        base_ym="201812",
        previous_features_available=True,
    )

    assert result.status == "SKIPPED_NO_EVIDENCE"
    assert result.error_message == (
        "전월 스냅샷은 존재하지만, 전월값 대체 재채점에서 모델 예측을 변경한 "
        "피처가 없어 설명 근거를 생성하지 못했습니다."
    )
    assert responses.calls == 0


def test_validation_failure_gets_one_correction_retry():
    invalid = valid_output()
    invalid["usedReasonIds"] = ["R404"]

    class ValidationResponses:
        def __init__(self):
            self.inputs = []

        def create(self, **kwargs):
            self.inputs.append(dynamic_request_payload(kwargs))
            payload = invalid if len(self.inputs) == 1 else valid_output()
            return SimpleNamespace(output_text=json.dumps(payload, ensure_ascii=False))

    responses = ValidationResponses()
    client = object.__new__(RiskExplanationClient)
    client.client = SimpleNamespace(responses=responses)
    client.model = "test-model"
    client.timeout_seconds = 60
    result = client.generate(input_payload=llm_input())

    assert result.status == "COMPLETED"
    assert len(responses.inputs) == 2
    assert "unknown reason ID" in responses.inputs[1]["correction"]


def test_confirmed_risk_effect_is_normalized_without_retry():
    invalid = valid_output()
    invalid["modelInterpretation"] = "카드 이용 가능 상태에서 위험 증가가 확인되었습니다."

    class SingleResponse:
        def __init__(self):
            self.calls = 0

        def create(self, **kwargs):
            self.calls += 1
            return SimpleNamespace(output_text=json.dumps(invalid, ensure_ascii=False))

    responses = SingleResponse()
    client = object.__new__(RiskExplanationClient)
    client.client = SimpleNamespace(responses=responses)
    client.model = "test-model"
    client.timeout_seconds = 60

    result = client.generate(input_payload=llm_input())

    assert result.status == "COMPLETED"
    assert responses.calls == 1
    assert result.structured_output["modelInterpretation"] == (
        "선택된 근거는 모델의 국소 재채점에서 모두 위험 증가 방향의 비교 근거로 나타났습니다."
    )


def test_summary_backend_facts_are_normalized_without_retry():
    output = valid_output()
    output["summary"] = (
        "수치가 작을수록 비교군 내 위험 우선순위가 높습니다. "
        "1개월 구간의 우선 검토가 필요합니다."
    )

    class SingleResponse:
        def __init__(self):
            self.calls = 0

        def create(self, **kwargs):
            self.calls += 1
            return SimpleNamespace(output_text=json.dumps(output, ensure_ascii=False))

    responses = SingleResponse()
    client = object.__new__(RiskExplanationClient)
    client.client = SimpleNamespace(responses=responses)
    client.model = "test-model"
    client.timeout_seconds = 60

    result = client.generate(input_payload=llm_input())

    assert result.status == "COMPLETED"
    assert responses.calls == 1
    assert result.structured_output["summary"] == (
        "모델 등급은 주의이며 고위험 순위 기준 0.33% 지점입니다. "
        "수치가 작을수록 비교군 내 위험 우선순위가 높습니다. "
        "1개월 구간의 우선 검토가 필요합니다."
    )


def test_valid_summary_is_preserved_without_normalization():
    output = valid_output()
    original_summary = output["summary"]

    class SingleResponse:
        def create(self, **kwargs):
            return SimpleNamespace(output_text=json.dumps(output, ensure_ascii=False))

    client = object.__new__(RiskExplanationClient)
    client.client = SimpleNamespace(responses=SingleResponse())
    client.model = "test-model"
    client.timeout_seconds = 60

    result = client.generate(input_payload=llm_input())

    assert result.status == "COMPLETED"
    assert result.structured_output["summary"] == original_summary


def test_lightgbm_name_is_removed_from_model_interpretation_without_retry():
    output = valid_output()
    output["modelInterpretation"] = (
        "LightGBM은 카드 이용 가능 상태 패턴을 위험 증가 방향의 우선 근거로 포착했습니다."
    )

    class SingleResponse:
        def __init__(self):
            self.calls = 0

        def create(self, **kwargs):
            self.calls += 1
            return SimpleNamespace(output_text=json.dumps(output, ensure_ascii=False))

    responses = SingleResponse()
    client = object.__new__(RiskExplanationClient)
    client.client = SimpleNamespace(responses=responses)
    client.model = "test-model"
    client.timeout_seconds = 60

    result = client.generate(input_payload=llm_input())

    assert result.status == "COMPLETED"
    assert responses.calls == 1
    assert result.structured_output["modelInterpretation"] == (
        "모델은 카드 이용 가능 상태 패턴을 위험 증가 방향의 우선 근거로 포착했습니다."
    )


def test_decrease_only_retry_receives_actionable_korean_correction():
    input_payload = llm_input()
    input_payload["modelReasons"][0]["modelDirection"] = "DECREASE_RISK"
    input_payload["indicatorCandidates"][0]["modelRelation"] = "RISK_DECREASE"
    invalid = valid_output()
    invalid["keyIndicators"][0]["modelRelation"] = "RISK_DECREASE"
    corrected = copy.deepcopy(invalid)
    corrected["modelInterpretation"] = "모델은 카드 이용 가능 상태를 위험 감소 방향의 비교 근거로 포착했습니다."

    class ValidationResponses:
        def __init__(self):
            self.inputs = []

        def create(self, **kwargs):
            self.inputs.append(dynamic_request_payload(kwargs))
            payload = invalid if len(self.inputs) == 1 else corrected
            return SimpleNamespace(output_text=json.dumps(payload, ensure_ascii=False))

    client = object.__new__(RiskExplanationClient)
    client.client = SimpleNamespace(responses=ValidationResponses())
    client.model = "test-model"
    client.timeout_seconds = 60

    result = client.generate(input_payload=input_payload)

    assert result.status == "COMPLETED"
    correction = client.client.responses.inputs[1]["correction"]
    assert "위험 신호·위험 근거·위험 요인·선행 신호" in correction
    assert "위험 감소 방향의 비교 근거" in correction


def test_openai_request_uses_versioned_explicit_prompt_cache():
    class CapturingResponses:
        def __init__(self):
            self.request = None

        def create(self, **kwargs):
            self.request = kwargs
            return SimpleNamespace(output_text=json.dumps(valid_output(), ensure_ascii=False))

    responses = CapturingResponses()
    client = object.__new__(RiskExplanationClient)
    client.client = SimpleNamespace(responses=responses)
    client.model = "test-model"
    client.prompt_version = "v3.6"
    client.prompt_cache_enabled = True
    client.prompt_cache_mode = "explicit"
    client.prompt_cache_ttl = "30m"
    client.prompt_cache_key_prefix = "miribom-risk-explanation"
    client.timeout_seconds = 60

    input_payload = llm_input()
    input_payload["customerId"] = "SYN_123"
    input_payload["requestId"] = "request-456"
    result = client.generate(input_payload=input_payload)

    assert result.status == "COMPLETED"
    assert responses.request["prompt_cache_key"] == "miribom-risk-explanation:v3.6"
    assert "SYN_123" not in responses.request["prompt_cache_key"]
    assert "request-456" not in responses.request["prompt_cache_key"]
    assert responses.request["prompt_cache_options"] == {"mode": "explicit", "ttl": "30m"}
    assert "instructions" not in responses.request
    developer_message, user_message = responses.request["input"]
    assert developer_message["role"] == "developer"
    assert developer_message["content"] == [{
        "type": "input_text",
        "text": SYSTEM_RULES,
        "prompt_cache_breakpoint": {"mode": "explicit"},
    }]
    assert user_message["role"] == "user"
    assert json.loads(user_message["content"][0]["text"]) == input_payload
    review_schema = responses.request["text"]["format"]["schema"]["properties"]["reviewPoints"]
    assert review_schema["minItems"] == 1
    assert review_schema["maxItems"] == 2
    assert "모델 방향이 위험 감소이면서" in SYSTEM_RULES
    assert "표시상 고위험 순위" in SYSTEM_RULES
    assert "정상 등급: 0~1개" in SYSTEM_RULES
    assert "관심·주의·경고 등급: 1~2개" in SYSTEM_RULES
    assert "내부 필드명을 화면 문장에 직접 쓰지 않는다" in SYSTEM_RULES


def test_openai_request_omits_all_prompt_cache_fields_when_disabled():
    client = object.__new__(RiskExplanationClient)
    client.model = "test-model"
    client.prompt_version = "v3.6"
    client.prompt_cache_enabled = False
    client.prompt_cache_mode = "explicit"
    client.prompt_cache_ttl = "30m"
    client.prompt_cache_key_prefix = "miribom-risk-explanation"

    schema = {"type": "object"}
    request = client._build_request_options(call_input=llm_input(), schema=schema)

    assert "prompt_cache_key" not in request
    assert "prompt_cache_options" not in request
    assert "prompt_cache_breakpoint" not in request["input"][0]["content"][0]
    assert request["text"]["format"]["schema"] is schema
    assert request["input"][0]["content"][0]["text"] == SYSTEM_RULES
    assert json.loads(request["input"][1]["content"][0]["text"]) == llm_input()


def test_usage_logging_handles_cache_details_and_missing_usage(caplog):
    client = object.__new__(RiskExplanationClient)
    client.model = "gpt-5.6-luna"
    client.prompt_version = "v3.6"
    client.prompt_cache_enabled = True
    client.prompt_cache_mode = "explicit"
    client.prompt_cache_ttl = "30m"
    client.prompt_cache_key_prefix = "miribom-risk-explanation"
    usage = SimpleNamespace(
        input_tokens=7171,
        input_tokens_details=SimpleNamespace(cached_tokens=2500, cache_write_tokens=0),
        output_tokens=1886,
        total_tokens=9057,
    )

    with caplog.at_level("INFO", logger="miribom.ai.llm"):
        client._log_usage(SimpleNamespace(usage=usage))
        client._log_usage(SimpleNamespace())

    assert "cacheKey=miribom-risk-explanation:v3.6" in caplog.text
    assert "input=7171 cached=2500 cacheWrite=0 output=1886 total=9057 cacheHit=true" in caplog.text
    assert "input=0 cached=0 cacheWrite=0 output=0 total=0 cacheHit=false" in caplog.text
