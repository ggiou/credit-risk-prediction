package com.creditrisk.prediction.service;

import com.creditrisk.customer.service.CustomerDetailService;
import com.creditrisk.prediction.client.AiPredictionClient;
import com.creditrisk.prediction.dto.PredictionDetailResponse;
import com.creditrisk.prediction.dto.PredictionExecutionResponse;
import com.creditrisk.prediction.mapper.PredictionMapper;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.ArgumentCaptor;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

import java.time.Instant;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.anyMap;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

@ExtendWith(MockitoExtension.class)
class PredictionCommandServiceTest {

    private static final String CUSTOMER_ID = "SYN_2653";
    private static final String BASE_YM = "201812";
    private static final String MODEL_VERSION = "miribom-lgbm-v0.3";

    @Mock
    private PredictionMapper predictionMapper;
    @Mock
    private CustomerDetailService customerDetailService;
    @Mock
    private PredictionQueryService predictionQueryService;
    @Mock
    private AiPredictionClient aiPredictionClient;

    private PredictionCommandService service;

    @BeforeEach
    void setUp() {
        service = new PredictionCommandService(
                predictionMapper,
                customerDetailService,
                predictionQueryService,
                aiPredictionClient,
                new ObjectMapper(),
                MODEL_VERSION,
                "v3.3");
        when(predictionMapper.findFeatureSnapshots(CUSTOMER_ID, BASE_YM, "201811"))
                .thenReturn(List.of(currentSnapshot()));
    }

    @Test
    void reusesResultWhenCompletedExplanationExists() {
        Map<String, Object> reused = reusedResult("COMPLETED", "완료된 설명", "v3.3");
        PredictionDetailResponse detail = detail("COMPLETED", "완료된 설명");
        when(predictionMapper.findByFeatureSnapshotAndModel(10L, MODEL_VERSION)).thenReturn(reused);
        when(predictionQueryService.toDetail(reused)).thenReturn(detail);

        PredictionExecutionResponse response = service.execute(
                CUSTOMER_ID, BASE_YM, true, "request-completed");

        assertThat(response.reused()).isTrue();
        verify(aiPredictionClient, never()).predict(anyMap());
        verify(predictionMapper, never()).updateRetriedExplanation(anyMap());
    }

    @Test
    void retriesMissingExplanationWithoutCreatingAnotherPrediction() {
        Map<String, Object> reused = reusedResult("FAILED", null, "v1.0");
        when(predictionMapper.findByFeatureSnapshotAndModel(10L, MODEL_VERSION)).thenReturn(reused);
        when(aiPredictionClient.predict(anyMap())).thenReturn(successfulAiResponse());
        when(predictionQueryService.getById(20L)).thenReturn(detail("COMPLETED", "새 설명"));

        PredictionExecutionResponse response = service.execute(
                CUSTOMER_ID, BASE_YM, true, "request-retry");

        @SuppressWarnings("unchecked")
        ArgumentCaptor<Map<String, Object>> values = ArgumentCaptor.forClass(Map.class);
        verify(predictionMapper).updateRetriedExplanation(values.capture());
        assertThat(values.getValue())
                .containsEntry("predictionId", 20L)
                .containsEntry("llmStatus", "COMPLETED")
                .containsEntry("riskGrade", "NORMAL")
                .containsEntry("percentile", 81.6);
        assertThat(response.reused()).isTrue();
        verify(predictionMapper, never()).insertPrediction(anyMap());
    }

    @Test
    void regeneratesCompletedExplanationWhenPromptVersionChanges() {
        Map<String, Object> reused = reusedResult("COMPLETED", "이전 형식 설명", "v1.0");
        when(predictionMapper.findByFeatureSnapshotAndModel(10L, MODEL_VERSION)).thenReturn(reused);
        when(aiPredictionClient.predict(anyMap())).thenReturn(successfulAiResponse());
        when(predictionQueryService.getById(20L)).thenReturn(detail("COMPLETED", "새 목록형 설명"));

        PredictionExecutionResponse response = service.execute(
                CUSTOMER_ID, BASE_YM, true, "request-new-prompt");

        verify(aiPredictionClient).predict(anyMap());
        verify(predictionMapper).updateRetriedExplanation(anyMap());
        assertThat(response.reused()).isTrue();
        verify(predictionMapper, never()).insertPrediction(anyMap());
    }

    private Map<String, Object> currentSnapshot() {
        return Map.of(
                "featureSnapshotId", 10L,
                "baseYm", BASE_YM,
                "featureSchemaVersion", "v1",
                "features", "{}");
    }

    private Map<String, Object> reusedResult(String llmStatus, String explanation, String promptVersion) {
        Map<String, Object> result = new LinkedHashMap<>();
        result.put("predictionId", 20L);
        result.put("llmStatus", llmStatus);
        result.put("explanation", explanation);
        result.put("promptVersion", promptVersion);
        return result;
    }

    private Map<String, Object> successfulAiResponse() {
        Map<String, Object> response = new LinkedHashMap<>();
        response.put("customerId", CUSTOMER_ID);
        response.put("baseYm", BASE_YM);
        response.put("featureSnapshotId", 10L);
        response.put("modelVersion", MODEL_VERSION);
        response.put("predictionSource", "LIGHTGBM_JSON");
        response.put("prediction", Map.of(
                        "hazard1m", 0.0000008466749669384437,
                        "hazard2m", 0.0000003988043456338314,
                        "hazard3m", 0.00000021807945963754698,
                        "cumulativeRisk3m", 0.0000014635581629951488,
                        "riskGrade", "NORMAL",
                        "topRiskPercent", 81.6,
                        "percentile", 81.6));
        response.put("riskFactors", List.of(Map.ofEntries(
                Map.entry("reasonId", "R1"),
                Map.entry("featureKey", "청구금액_B0"),
                Map.entry("reasonMethod", "PREVIOUS_VALUE_COUNTERFACTUAL"),
                Map.entry("evidenceFeatureKeys", List.of("청구금액_B0"))
        )));
        response.put("observedChanges", List.of(Map.of(
                "signalId", "S1", "featureKeys", List.of("청구금액_B0"))));
        response.put("explanation", "모델 요약\n\n주요 관찰 지표\n청구 부담 흐름\n당월 청구금액은 전월보다 0.13% 증가했습니다.\n당월 청구 흐름은 모델 비교 근거입니다.\n\n모델 근거 해석");
        response.put("recommendation", "1. 다음 결제 예정 금액과 최근 납부 이력 확인");
        response.put("llmOutput", Map.of(
                "summary", "모델 요약",
                "modelInterpretation", "모델 근거 해석",
                "keyIndicators", List.of(Map.of(
                        "title", "청구 부담 흐름",
                        "fact", "당월 청구금액은 전월보다 0.13% 증가했습니다.",
                        "detail", "당월 청구금액은 전월 100,000원에서 현재 100,130원으로 130원 증가했습니다.",
                        "interpretation", "당월 청구 흐름은 모델 비교 근거입니다.",
                        "modelRelation", "RISK_DECREASE",
                        "reasonIds", List.of("R1"),
                        "signalIds", List.of("S1"),
                        "featureKeys", List.of("청구금액_B0"))),
                "changeContext", "",
                "managementPriority", "ROUTINE_MONITORING",
                "usedFeatureKeys", List.of("청구금액_B0"),
                "usedReasonIds", List.of("R1"),
                "usedSignalIds", List.of("S1"),
                "generationMode", "FULL_ANALYSIS",
                "reviewPoints", List.of(Map.of(
                        "priority", 1,
                        "text", "다음 결제 예정 금액과 최근 납부 이력 확인",
                        "reasonIds", List.of("R1"),
                        "signalIds", List.of("S1")))));
        response.put("llm", Map.of("status", "COMPLETED", "promptVersion", "v3.3"));
        response.put("predictedAt", "2026-09-01T00:00:00Z");
        return response;
    }

    private PredictionDetailResponse detail(String llmStatus, String explanation) {
        return new PredictionDetailResponse(
                20L,
                CUSTOMER_ID,
                BASE_YM,
                "COMPLETED",
                MODEL_VERSION,
                "v1",
                new PredictionDetailResponse.Risk(
                        0.0000008466749669384437,
                        0.0000003988043456338314,
                        0.00000021807945963754698,
                        0.0000014635581629951488,
                        "NORMAL",
                        "정상",
                        81.6,
                        81.6),
                List.of(),
                explanation,
                null,
                null,
                new PredictionDetailResponse.Llm(llmStatus, "v3.3", "v3.3", false),
                Instant.parse("2026-09-01T00:00:00Z"));
    }
}
