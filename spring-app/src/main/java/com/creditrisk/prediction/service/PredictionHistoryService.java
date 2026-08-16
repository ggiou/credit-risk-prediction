package com.creditrisk.prediction.service;

import com.creditrisk.common.api.PageData;
import com.creditrisk.common.domain.LlmStatus;
import com.creditrisk.common.domain.RiskGrade;
import com.creditrisk.prediction.dto.PredictionHistoryCondition;
import com.creditrisk.prediction.dto.PredictionHistoryItem;
import com.creditrisk.prediction.mapper.PredictionMapper;
import org.springframework.stereotype.Service;

import java.sql.Timestamp;
import java.time.Instant;
import java.util.List;
import java.util.Map;

/**
 * 전체 또는 특정 고객의 과거 예측 결과를 검색한다.
 */
@Service
public class PredictionHistoryService {

    private final PredictionMapper predictionMapper;

    /** 예측 조회 Mapper를 주입받는다. */
    public PredictionHistoryService(PredictionMapper predictionMapper) {
        this.predictionMapper = predictionMapper;
    }

    /**
     * 검색 조건에 맞는 예측 이력을 페이지로 반환한다.
     */
    public PageData<PredictionHistoryItem> search(
            String customerId,
            String baseYm,
            RiskGrade riskGrade,
            String modelVersion,
            LlmStatus llmStatus,
            Instant predictedFrom,
            Instant predictedTo,
            int page,
            int size,
            String sort) {
        // DB 값인 한글 위험등급으로 한 번 변환해 Mapper의 조건을 단순하게 유지한다.
        PredictionHistoryCondition condition = new PredictionHistoryCondition(
                blankToNull(customerId),
                blankToNull(baseYm),
                riskGrade == null ? null : riskGrade.getDisplayName(),
                blankToNull(modelVersion),
                llmStatus == null ? null : llmStatus.name(),
                predictedFrom,
                predictedTo,
                page,
                size,
                sort.split(",")[1].toUpperCase());

        List<PredictionHistoryItem> items = predictionMapper.findHistory(condition).stream()
                .map(this::toHistoryItem)
                .toList();
        return PageData.of(items, page, size, predictionMapper.countHistory(condition));
    }

    /** MyBatis 조회 행을 예측 이력 DTO로 변환한다. */
    private PredictionHistoryItem toHistoryItem(Map<String, Object> row) {
        // 예측 결과의 필수값은 스키마 제약으로 보장되므로 기본형으로 변환한다.
        return new PredictionHistoryItem(
                longValue(row.get("predictionId")),
                instantValue(row.get("predictedAt")),
                stringValue(row.get("customerId")),
                stringValue(row.get("baseYm")),
                doubleValue(row.get("hazard1m")),
                doubleValue(row.get("hazard2m")),
                doubleValue(row.get("hazard3m")),
                stringValue(row.get("riskGrade")),
                stringValue(row.get("riskGradeName")),
                stringValue(row.get("modelVersion")),
                stringValue(row.get("featureSchemaVersion")),
                stringValue(row.get("llmStatus")),
                nullableString(row.get("llmModel")),
                nullableString(row.get("promptVersion")));
    }

    /** 공백 검색 조건을 null로 변환한다. */
    private String blankToNull(String value) {
        return value == null || value.isBlank() ? null : value.trim();
    }

    /** 숫자형 DB 값을 long으로 변환한다. */
    private long longValue(Object value) {
        return value instanceof Number number ? number.longValue() : 0L;
    }

    /** 숫자형 DB 값을 double로 변환한다. */
    private double doubleValue(Object value) {
        return value instanceof Number number ? number.doubleValue() : 0.0;
    }

    /** DB 값을 문자열로 변환한다. */
    private String stringValue(Object value) {
        return value == null ? "" : String.valueOf(value);
    }

    /** null을 보존하는 문자열 변환이다. */
    private String nullableString(Object value) {
        return value == null ? null : String.valueOf(value);
    }

    /** JDBC Timestamp를 UTC 시각으로 변환한다. */
    private Instant instantValue(Object value) {
        return value instanceof Timestamp timestamp ? timestamp.toInstant() : null;
    }
}

