package com.creditrisk.prediction.service;

import com.creditrisk.prediction.dto.PredictionDetailResponse;
import com.creditrisk.prediction.mapper.PredictionMapper;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

import java.sql.Timestamp;
import java.time.Instant;
import java.util.LinkedHashMap;
import java.util.Map;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.Mockito.when;

@ExtendWith(MockitoExtension.class)
class PredictionQueryServiceTest {

    @Mock
    private PredictionMapper predictionMapper;

    private PredictionQueryService service;

    @BeforeEach
    void setUp() {
        service = new PredictionQueryService(
                predictionMapper,
                new ObjectMapper(),
                "miribom-lgbm-v0.3",
                "v3.1");
    }

    @Test
    void returnsStoredStructuredOutputWithoutRegeneration() {
        Map<String, Object> row = new LinkedHashMap<>();
        row.put("predictionId", 7L);
        row.put("customerId", "SYN_123");
        row.put("baseYm", "201812");
        row.put("modelVersion", "miribom-lgbm-v0.3");
        row.put("featureSchemaVersion", "v1");
        row.put("hazard1m", 0.01);
        row.put("hazard2m", 0.005);
        row.put("hazard3m", 0.002);
        row.put("cumulativeRisk3m", 0.0169);
        row.put("riskGrade", "NORMAL");
        row.put("riskGradeName", "정상");
        row.put("percentile", 81.4);
        row.put("reasons", "[]");
        row.put("explanation", "저장된 설명");
        row.put("recommendation", null);
        row.put("llmOutput", "{\"summary\":\"저장된 설명\",\"keyIndicators\":[],\"managementPriority\":\"ROUTINE_MONITORING\"}");
        row.put("llmStatus", "COMPLETED");
        row.put("promptVersion", "v3.1");
        row.put("predictedAt", Timestamp.from(Instant.parse("2026-09-05T00:00:00Z")));
        when(predictionMapper.findById(7L)).thenReturn(row);

        PredictionDetailResponse response = service.getById(7L);

        assertThat(response.explanation()).isEqualTo("저장된 설명");
        assertThat(response.llmOutput())
                .containsEntry("managementPriority", "ROUTINE_MONITORING")
                .containsKey("keyIndicators");
        assertThat(response.llm().outdated()).isFalse();
    }
}
