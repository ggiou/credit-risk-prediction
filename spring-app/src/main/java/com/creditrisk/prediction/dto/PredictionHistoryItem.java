package com.creditrisk.prediction.dto;

import java.time.Instant;

/**
 * 전체 또는 고객별 예측 이력의 한 행이다.
 */
public record PredictionHistoryItem(
        long predictionId,
        Instant predictedAt,
        String customerId,
        String baseYm,
        double hazard1m,
        double hazard2m,
        double hazard3m,
        String riskGrade,
        String riskGradeName,
        String modelVersion,
        String featureSchemaVersion,
        String llmStatus,
        String llmModel,
        String promptVersion) {
}

