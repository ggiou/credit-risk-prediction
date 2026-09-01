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
                "v1.2");
        when(predictionMapper.findFeatureSnapshots(CUSTOMER_ID, BASE_YM, "201811"))
                .thenReturn(List.of(currentSnapshot()));
    }

    @Test
    void reusesResultWhenCompletedExplanationExists() {
        Map<String, Object> reused = reusedResult("COMPLETED", "완료된 설명", "v1.2");
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
        return Map.of(
                "customerId", CUSTOMER_ID,
                "baseYm", BASE_YM,
                "featureSnapshotId", 10L,
                "modelVersion", MODEL_VERSION,
                "prediction", Map.of(
                        "hazard1m", 0.0000008466749669384437,
                        "hazard2m", 0.0000003988043456338314,
                        "hazard3m", 0.00000021807945963754698,
                        "cumulativeRisk3m", 0.0000014635581629951488,
                        "riskGrade", "NORMAL",
                        "percentile", 81.6),
                "riskFactors", List.of(),
                "explanation", "새 설명",
                "llm", Map.of("status", "COMPLETED", "promptVersion", "v1.2"),
                "predictedAt", "2026-09-01T00:00:00Z");
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
                        81.6),
                List.of(),
                explanation,
                new PredictionDetailResponse.Llm(llmStatus, "v1.2"),
                Instant.parse("2026-09-01T00:00:00Z"));
    }
}
