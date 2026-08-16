package com.creditrisk.prediction.dto;

import java.time.Instant;

/**
 * 예측 이력 검색과 페이지 조건이다.
 */
public record PredictionHistoryCondition(
        String customerId,
        String baseYm,
        String riskGradeName,
        String modelVersion,
        String llmStatus,
        Instant predictedFrom,
        Instant predictedTo,
        int page,
        int size,
        String sortDirection) {

    /** 페이지 시작 위치를 반환한다. */
    public int offset() {
        // 0 기반 페이지 번호를 MySQL OFFSET으로 변환한다.
        return page * size;
    }
}

