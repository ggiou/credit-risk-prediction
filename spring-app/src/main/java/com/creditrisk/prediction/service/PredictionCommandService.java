package com.creditrisk.prediction.service;

import com.creditrisk.common.domain.LlmStatus;
import com.creditrisk.common.domain.RiskGrade;
import com.creditrisk.common.exception.BusinessException;
import com.creditrisk.customer.service.CustomerDetailService;
import com.creditrisk.prediction.client.AiPredictionClient;
import com.creditrisk.prediction.dto.PredictionDetailResponse;
import com.creditrisk.prediction.dto.PredictionExecutionResponse;
import com.creditrisk.prediction.mapper.PredictionMapper;
import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.dao.DuplicateKeyException;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.sql.Timestamp;
import java.time.Instant;
import java.time.YearMonth;
import java.time.format.DateTimeFormatter;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/**
 * 고객 피처 조회, 스냅샷·모델 기준 결과 재사용, FastAPI 호출, 예측 저장을 순서대로 수행한다.
 */
@Service
public class PredictionCommandService {

    private static final DateTimeFormatter BASE_YM_FORMAT = DateTimeFormatter.ofPattern("yyyyMM");
    private static final TypeReference<Map<String, Object>> FEATURE_TYPE = new TypeReference<>() {
    };

    private final PredictionMapper predictionMapper;
    private final CustomerDetailService customerDetailService;
    private final PredictionQueryService predictionQueryService;
    private final AiPredictionClient aiPredictionClient;
    private final ObjectMapper objectMapper;
    private final String modelVersion;
    private final String promptVersion;

    /** 예측 실행에 필요한 DB, AI 서버, 직렬화 의존성을 주입받는다. */
    public PredictionCommandService(
            PredictionMapper predictionMapper,
            CustomerDetailService customerDetailService,
            PredictionQueryService predictionQueryService,
            AiPredictionClient aiPredictionClient,
            ObjectMapper objectMapper,
            @Value("${ai.model.version}") String modelVersion,
            @Value("${ai.model.prompt-version}") String promptVersion) {
        this.predictionMapper = predictionMapper;
        this.customerDetailService = customerDetailService;
        this.predictionQueryService = predictionQueryService;
        this.aiPredictionClient = aiPredictionClient;
        this.objectMapper = objectMapper;
        this.modelVersion = modelVersion;
        this.promptVersion = promptVersion;
    }

    /**
     * 고객의 기준월 피처를 예측하고 신규 결과 또는 재사용 결과를 반환한다.
     */
    @Transactional
    public PredictionExecutionResponse execute(
            String customerId,
            String baseYm,
            boolean generateExplanation,
            String requestId) {
        // 고객 미존재와 피처 미적재 오류를 AI 호출 전에 분리한다.
        customerDetailService.validateCustomer(customerId);
        String previousBaseYm = YearMonth.parse(baseYm, BASE_YM_FORMAT)
                .minusMonths(1)
                .format(BASE_YM_FORMAT);
        List<Map<String, Object>> snapshots = predictionMapper.findFeatureSnapshots(
                customerId, baseYm, previousBaseYm);
        Map<String, Object> currentSnapshot = findSnapshot(snapshots, baseYm);
        if (currentSnapshot == null) {
            throw new BusinessException(
                    "FEATURE_SNAPSHOT_NOT_FOUND",
                    "해당 고객과 기준월의 피처 스냅샷을 찾을 수 없습니다.",
                    HttpStatus.NOT_FOUND,
                    Map.of("customerId", customerId, "baseYm", baseYm));
        }

        long featureSnapshotId = ((Number) currentSnapshot.get("featureSnapshotId")).longValue();
        Map<String, Object> reused = predictionMapper.findByFeatureSnapshotAndModel(
                featureSnapshotId, modelVersion);
        if (hasResult(reused) && !needsExplanationRetry(reused, generateExplanation)) {
            // 완료된 설명이 있거나 설명을 요청하지 않았다면 저장된 예측 결과를 그대로 재사용한다.
            return PredictionExecutionResponse.from(predictionQueryService.toDetail(reused), true);
        }

        Map<String, Object> previousSnapshot = findSnapshot(snapshots, previousBaseYm);
        Map<String, Object> currentFeatures = parseFeatures(currentSnapshot.get("features"));
        Map<String, Object> previousFeatures = previousSnapshot == null
                ? null
                : parseFeatures(previousSnapshot.get("features"));
        String featureSchemaVersion = String.valueOf(currentSnapshot.get("featureSchemaVersion"));
        Map<String, Object> aiRequest = buildAiRequest(
                requestId,
                customerId,
                baseYm,
                currentSnapshot,
                previousSnapshot,
                featureSchemaVersion,
                generateExplanation,
                currentFeatures,
                previousFeatures);
        Map<String, Object> aiResponse = aiPredictionClient.predict(aiRequest);
        validateAiResponse(aiResponse, customerId, baseYm, featureSnapshotId);
        Map<String, Object> insertValues = toInsertValues(aiResponse);

        if (hasResult(reused)) {
            // 예측 행은 새로 만들지 않고 실패·미요청·이전 프롬프트의 LLM 결과만 안전하게 갱신한다.
            long predictionId = ((Number) reused.get("predictionId")).longValue();
            insertValues.put("predictionId", predictionId);
            predictionMapper.updateRetriedExplanation(insertValues);
            PredictionDetailResponse updated = predictionQueryService.getById(predictionId);
            return PredictionExecutionResponse.from(updated, true);
        }

        try {
            predictionMapper.insertPrediction(insertValues);
        } catch (DuplicateKeyException exception) {
            // 동시에 같은 스냅샷과 모델이 실행된 경우 먼저 저장된 결과를 재사용한다.
            Map<String, Object> concurrentResult = predictionMapper.findByFeatureSnapshotAndModel(
                    featureSnapshotId, modelVersion);
            if (concurrentResult != null && !concurrentResult.isEmpty()) {
                return PredictionExecutionResponse.from(predictionQueryService.toDetail(concurrentResult), true);
            }
            throw exception;
        }

        long predictionId = ((Number) insertValues.get("predictionId")).longValue();
        PredictionDetailResponse saved = predictionQueryService.getById(predictionId);
        return PredictionExecutionResponse.from(saved, false);
    }

    /** 동일 스냅샷·모델 결과가 존재하는지 확인한다. */
    private boolean hasResult(Map<String, Object> result) {
        return result != null && !result.isEmpty();
    }

    /** 설명 요청인데 완료 설명이 없거나 프롬프트 버전이 바뀌었으면 동일 피처로 설명 생성을 재시도한다. */
    private boolean needsExplanationRetry(Map<String, Object> result, boolean generateExplanation) {
        if (!generateExplanation) {
            return false;
        }
        boolean completed = LlmStatus.COMPLETED.name().equals(String.valueOf(result.get("llmStatus")));
        Object explanation = result.get("explanation");
        boolean currentPrompt = promptVersion.equals(String.valueOf(result.get("promptVersion")));
        return !completed || explanation == null || String.valueOf(explanation).isBlank() || !currentPrompt;
    }

    /** 기준년월이 일치하는 스냅샷 행을 찾는다. */
    private Map<String, Object> findSnapshot(List<Map<String, Object>> snapshots, String baseYm) {
        return snapshots.stream()
                .filter(row -> baseYm.equals(String.valueOf(row.get("baseYm"))))
                .findFirst()
                .orElse(null);
    }

    /** 피처 JSON 문자열을 Map으로 변환한다. */
    private Map<String, Object> parseFeatures(Object value) {
        try {
            // 원천 결측값 null을 보존해 FastAPI의 결측 처리 규칙에 맡긴다.
            return objectMapper.readValue(String.valueOf(value), FEATURE_TYPE);
        } catch (JsonProcessingException exception) {
            throw new BusinessException(
                    "INVALID_FEATURE_SNAPSHOT",
                    "피처 스냅샷 JSON 형식이 올바르지 않습니다.",
                    HttpStatus.INTERNAL_SERVER_ERROR,
                    Map.of());
        }
    }

    /** FastAPI 내부 계약에 맞는 요청 Map을 구성한다. */
    private Map<String, Object> buildAiRequest(
            String requestId,
            String customerId,
            String baseYm,
            Map<String, Object> currentSnapshot,
            Map<String, Object> previousSnapshot,
            String featureSchemaVersion,
            boolean generateExplanation,
            Map<String, Object> currentFeatures,
            Map<String, Object> previousFeatures) {
        Map<String, Object> request = new LinkedHashMap<>();
        request.put("requestId", requestId);
        request.put("customerId", customerId);
        request.put("baseYm", baseYm);
        request.put("featureSnapshotId", currentSnapshot.get("featureSnapshotId"));
        request.put("previousFeatureSnapshotId", previousSnapshot == null ? null : previousSnapshot.get("featureSnapshotId"));
        request.put("featureSchemaVersion", featureSchemaVersion);
        request.put("expectedModelVersion", modelVersion);
        request.put("promptVersion", promptVersion);
        request.put("generateExplanation", generateExplanation);
        request.put("currentFeatures", currentFeatures);
        request.put("previousFeatures", previousFeatures);
        return request;
    }

    /** AI 응답의 식별자, 스냅샷, 버전, 위험률 범위를 검증한다. */
    @SuppressWarnings("unchecked")
    private void validateAiResponse(
            Map<String, Object> response,
            String customerId,
            String baseYm,
            long expectedFeatureSnapshotId) {
        // 다른 요청의 응답이나 다른 버전 결과를 저장하지 않도록 핵심 식별자를 모두 비교한다.
        if (!customerId.equals(String.valueOf(response.get("customerId")))
                || !baseYm.equals(String.valueOf(response.get("baseYm")))
                || !modelVersion.equals(String.valueOf(response.get("modelVersion")))
                || !String.valueOf(expectedFeatureSnapshotId).equals(
                        String.valueOf(response.get("featureSnapshotId")))) {
            throw invalidAiResponse("AI 서버 응답 식별자 또는 버전이 요청과 일치하지 않습니다.");
        }
        Object predictionObject = response.get("prediction");
        if (!(predictionObject instanceof Map<?, ?> prediction)) {
            throw invalidAiResponse("AI 서버 응답에 prediction이 없습니다.");
        }
        for (String key : List.of("hazard1m", "hazard2m", "hazard3m", "cumulativeRisk3m")) {
            Object value = prediction.get(key);
            if (!(value instanceof Number number) || number.doubleValue() < 0 || number.doubleValue() > 1) {
                throw invalidAiResponse("AI 서버 위험률 범위가 올바르지 않습니다.");
            }
        }
    }

    /** 검증이 끝난 AI 응답을 예측 결과 INSERT 값으로 변환한다. */
    @SuppressWarnings("unchecked")
    private Map<String, Object> toInsertValues(Map<String, Object> response) {
        Map<String, Object> prediction = (Map<String, Object>) response.get("prediction");
        Map<String, Object> llm = response.get("llm") instanceof Map<?, ?> value
                ? (Map<String, Object>) value
                : Map.of("status", "FAILED", "errorMessage", "LLM 응답이 없습니다.");
        List<Map<String, Object>> riskFactors = response.get("riskFactors") instanceof List<?> list
                ? (List<Map<String, Object>>) list
                : new ArrayList<>();
        Map<String, Object> values = new LinkedHashMap<>();
        values.put("featureSnapshotId", response.get("featureSnapshotId"));
        values.put("modelVersion", response.get("modelVersion"));
        values.put("hazard1m", prediction.get("hazard1m"));
        values.put("hazard2m", prediction.get("hazard2m"));
        values.put("hazard3m", prediction.get("hazard3m"));
        values.put("cumulativeRisk3m", prediction.get("cumulativeRisk3m"));
        values.put("riskGrade", riskGradeCode(String.valueOf(prediction.get("riskGrade"))));
        values.put("percentile", prediction.get("percentile"));
        values.put("reasons", writeJson(riskFactors));
        values.put("explanation", response.get("explanation"));
        values.put("llmStatus", llmStatusName(llm));
        values.put("promptVersion", llm.getOrDefault("promptVersion", promptVersion));
        values.put("predictedAt", Timestamp.from(parseInstant(response.get("predictedAt"))));
        return values;
    }

    /** AI 응답 상태를 DB enum 문자열로 제한한다. */
    private String llmStatusName(Map<String, Object> llm) {
        try {
            return LlmStatus.valueOf(
                    String.valueOf(llm.getOrDefault("status", LlmStatus.FAILED.name())))
                    .name();
        } catch (IllegalArgumentException exception) {
            throw invalidAiResponse("AI 서버 LLM 상태가 올바르지 않습니다.");
        }
    }

    /** AI 응답의 영문 위험등급 코드만 DB 저장값으로 허용한다. */
    private String riskGradeCode(String code) {
        try {
            return RiskGrade.valueOf(code).name();
        } catch (IllegalArgumentException exception) {
            throw invalidAiResponse("AI 서버 위험등급이 올바르지 않습니다.");
        }
    }

    /** 객체를 DB JSON 문자열로 직렬화한다. */
    private String writeJson(Object value) {
        try {
            return objectMapper.writeValueAsString(value);
        } catch (JsonProcessingException exception) {
            throw invalidAiResponse("주요 위험 요인을 JSON으로 변환하지 못했습니다.");
        }
    }

    /** AI 응답의 ISO 8601 시각을 변환한다. */
    private Instant parseInstant(Object value) {
        try {
            return Instant.parse(String.valueOf(value));
        } catch (RuntimeException exception) {
            throw invalidAiResponse("AI 서버 분석일시 형식이 올바르지 않습니다.");
        }
    }

    /** 잘못된 AI 응답 예외를 생성한다. */
    private BusinessException invalidAiResponse(String message) {
        return new BusinessException(
                "AI_SERVER_INVALID_RESPONSE",
                message,
                HttpStatus.BAD_GATEWAY,
                Map.of());
    }
}
