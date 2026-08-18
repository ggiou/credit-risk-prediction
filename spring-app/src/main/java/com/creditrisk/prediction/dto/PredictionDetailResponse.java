package com.creditrisk.prediction.dto;

import java.time.Instant;
import java.util.List;
import java.util.Map;

/**
 * 저장된 위험률, 주요 요인, LLM 설명과 모델 메타정보를 전달한다.
 */
public record PredictionDetailResponse(
        long predictionId,
        String customerId,
        String baseYm,
        String analysisStatus,
        String modelVersion,
        String featureSchemaVersion,
        Risk risk,
        List<Map<String, Object>> riskFactors,
        String explanation,
        Llm llm,
        String inputHash,
        Instant predictedAt) {

    /** 모델이 계산한 기간별 위험률과 등급이다. */
    public record Risk(
            double hazard1m,
            double hazard2m,
            double hazard3m,
            double cumulativeRisk3m,
            String riskGrade,
            String riskGradeName,
            double percentile) {
    }

    /** LLM 설명 생성 상태와 버전 정보다. */
    public record Llm(
            String status,
            String model,
            String promptVersion,
            String errorMessage) {
    }
}

