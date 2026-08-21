package com.creditrisk.customer.dto;

import java.time.Instant;

/**
 * 고객 목록 한 행에 표시할 현재 예측 요약이다.
 */
public record CustomerListItem(
        String customerId,
        String displayName,
        String baseYm,
        Long predictionId,
        String analysisStatus,
        String riskGrade,
        String riskGradeName,
        Double hazard1m,
        Double hazard2m,
        Double hazard3m,
        Double riskChange3m,
        String primaryRiskFactor,
        Instant predictedAt) {
}

