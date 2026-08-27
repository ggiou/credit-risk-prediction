package com.creditrisk.prediction.dto;

import java.time.Instant;

/**
 * 예측 이력 검색과 페이지 조건이다.
 */
public record PredictionHistoryCondition(
        String customerId,
        String baseYm,
        String riskGrade,
        String modelVersion,
        String llmStatus,
        Instant predictedFrom,
        Instant predictedTo,
        int page,
        int size,
        int offset,
        String sortDirection) {
}
