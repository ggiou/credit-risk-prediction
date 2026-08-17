package com.creditrisk.prediction.service;

import com.creditrisk.common.exception.BusinessException;
import com.creditrisk.prediction.dto.PredictionDetailResponse;
import com.creditrisk.prediction.mapper.PredictionMapper;
import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;

import java.sql.Timestamp;
import java.time.Instant;
import java.util.List;
import java.util.Map;

/**
 * 저장된 예측 결과를 상세 응답으로 변환한다.
 */
@Service
public class PredictionQueryService {

    private static final TypeReference<List<Map<String, Object>>> RISK_FACTOR_TYPE = new TypeReference<>() {
    };

    private final PredictionMapper predictionMapper;
    private final ObjectMapper objectMapper;
    private final String modelVersion;

    /** 예측 조회 Mapper와 JSON 변환기를 주입받는다. */
    public PredictionQueryService(
            PredictionMapper predictionMapper,
            ObjectMapper objectMapper,
            @Value("${ai.model.version}") String modelVersion) {
        this.predictionMapper = predictionMapper;
        this.objectMapper = objectMapper;
        this.modelVersion = modelVersion;
    }

    /**
     * 예측 ID에 저장된 당시 결과를 다시 계산하지 않고 조회한다.
     */
    public PredictionDetailResponse getById(long predictionId) {
        // 과거 결과는 현재 모델로 재계산하지 않고 저장된 원본을 그대로 사용한다.
        Map<String, Object> row = predictionMapper.findById(predictionId);
        if (row == null || row.isEmpty()) {
            throw predictionNotFound(Map.of("predictionId", predictionId));
        }
        return toDetail(row);
    }

    /**
     * 고객과 기준월의 활성 모델 최신 예측 결과를 조회한다.
     */
    public PredictionDetailResponse getCurrent(String customerId, String baseYm) {
        // 동일 월에 재분석 이력이 여러 개면 가장 최근 저장 결과를 사용한다.
        Map<String, Object> row = predictionMapper.findCurrent(customerId, baseYm, modelVersion);
        if (row == null || row.isEmpty()) {
            throw predictionNotFound(Map.of("customerId", customerId, "baseYm", baseYm));
        }
        return toDetail(row);
    }

    /**
     * DB 조회 행을 API 예측 상세 구조로 변환한다.
     */
    public PredictionDetailResponse toDetail(Map<String, Object> row) {
        String riskGradeName = stringValue(row.get("riskGradeName"));
        String llmStatus = stringValue(row.get("llmStatus"));
        return new PredictionDetailResponse(
                longValue(row.get("predictionId")),
                stringValue(row.get("customerId")),
                stringValue(row.get("baseYm")),
                "FAILED".equals(llmStatus) ? "PARTIAL" : "COMPLETED",
                stringValue(row.get("modelVersion")),
                stringValue(row.get("featureSchemaVersion")),
                new PredictionDetailResponse.Risk(
                        doubleValue(row.get("hazard1m")),
                        doubleValue(row.get("hazard2m")),
                        doubleValue(row.get("hazard3m")),
                        doubleValue(row.get("cumulativeRisk3m")),
                        riskGradeCode(riskGradeName),
                        riskGradeName,
                        doubleValue(row.get("percentile"))),
                parseReasons(row.get("reasons")),
                nullableString(row.get("explanation")),
                new PredictionDetailResponse.Llm(
                        llmStatus,
                        nullableString(row.get("llmModel")),
                        nullableString(row.get("promptVersion")),
                        nullableString(row.get("llmErrorMessage"))),
                stringValue(row.get("inputHash")),
                instantValue(row.get("predictedAt")));
    }

    /**
     * DB의 reasons JSON을 주요 위험 요인 목록으로 변환한다.
     */
    private List<Map<String, Object>> parseReasons(Object value) {
        if (value == null || String.valueOf(value).isBlank()) {
            return List.of();
        }
        try {
            // JSON 구조가 깨진 경우 잘못된 요인을 화면에 보여주지 않고 데이터 오류로 중단한다.
            return objectMapper.readValue(String.valueOf(value), RISK_FACTOR_TYPE);
        } catch (JsonProcessingException exception) {
            throw new BusinessException(
                    "INVALID_PREDICTION_DATA",
                    "저장된 주요 위험 요인 형식이 올바르지 않습니다.",
                    HttpStatus.INTERNAL_SERVER_ERROR,
                    Map.of());
        }
    }

    /** 예측 미존재 업무 예외를 생성한다. */
    private BusinessException predictionNotFound(Map<String, Object> details) {
        return new BusinessException(
                "PREDICTION_NOT_FOUND",
                "예측 결과를 찾을 수 없습니다.",
                HttpStatus.NOT_FOUND,
                details);
    }

    /** 한글 위험등급을 API 코드로 변환한다. */
    private String riskGradeCode(String riskGradeName) {
        return switch (riskGradeName) {
            case "정상" -> "NORMAL";
            case "관심" -> "INTEREST";
            case "주의" -> "CAUTION";
            case "경고" -> "WARNING";
            default -> "";
        };
    }

    /** DB 값을 문자열로 변환한다. */
    private String stringValue(Object value) {
        return value == null ? "" : String.valueOf(value);
    }

    /** null을 보존하는 문자열 변환이다. */
    private String nullableString(Object value) {
        return value == null ? null : String.valueOf(value);
    }

    /** 숫자형 DB 값을 long으로 변환한다. */
    private long longValue(Object value) {
        return value instanceof Number number ? number.longValue() : 0L;
    }

    /** 숫자형 DB 값을 double로 변환한다. */
    private double doubleValue(Object value) {
        return value instanceof Number number ? number.doubleValue() : 0.0;
    }

    /** JDBC Timestamp 또는 Instant를 API 시각으로 변환한다. */
    private Instant instantValue(Object value) {
        if (value instanceof Timestamp timestamp) {
            return timestamp.toInstant();
        }
        return value instanceof Instant instant ? instant : null;
    }
}

