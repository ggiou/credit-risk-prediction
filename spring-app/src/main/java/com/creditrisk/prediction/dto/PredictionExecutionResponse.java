package com.creditrisk.prediction.dto;

import java.time.Instant;
import java.util.List;
import java.util.Map;

/**
 * 신규 분석 또는 피처 스냅샷·모델 기반 재사용 결과를 전달한다.
 */
public record PredictionExecutionResponse(
        long predictionId,
        String customerId,
        String baseYm,
        boolean reused,
        String analysisStatus,
        String modelVersion,
        String featureSchemaVersion,
        PredictionDetailResponse.Risk risk,
        List<Map<String, Object>> riskFactors,
        String explanation,
        PredictionDetailResponse.Llm llm,
        Instant predictedAt) {

    /** 저장 예측 상세에 이번 요청의 재사용 여부를 추가한다. */
    public static PredictionExecutionResponse from(PredictionDetailResponse detail, boolean reused) {
        // 조회 응답과 실행 응답의 필드 값이 달라지지 않도록 상세 DTO를 그대로 재사용한다.
        return new PredictionExecutionResponse(
                detail.predictionId(),
                detail.customerId(),
                detail.baseYm(),
                reused,
                detail.analysisStatus(),
                detail.modelVersion(),
                detail.featureSchemaVersion(),
                detail.risk(),
                detail.riskFactors(),
                detail.explanation(),
                detail.llm(),
                detail.predictedAt());
    }
}
