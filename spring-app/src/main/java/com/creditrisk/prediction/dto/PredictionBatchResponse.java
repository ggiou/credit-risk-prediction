package com.creditrisk.prediction.dto;

import java.time.Instant;
import java.util.List;

/** 다건 분석 진행 상태와 고객별 처리 결과를 전달한다. */
public record PredictionBatchResponse(
        long batchId,
        String requestedBy,
        String baseYm,
        boolean generateExplanation,
        String status,
        int totalCount,
        int completedCount,
        int reusedCount,
        int failedCount,
        int pendingCount,
        Instant createdAt,
        Instant startedAt,
        Instant completedAt,
        List<Item> items) {

    public record Item(
            long batchItemId,
            String customerId,
            String status,
            Long predictionId,
            String errorCode,
            String errorMessage) {
    }
}
