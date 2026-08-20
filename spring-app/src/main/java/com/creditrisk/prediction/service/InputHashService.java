package com.creditrisk.prediction.service;

import com.creditrisk.common.exception.BusinessException;
import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.SerializationFeature;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.util.HexFormat;
import java.util.Map;
import java.util.TreeMap;

/**
 * Spring과 FastAPI가 같은 입력 재사용 기준을 사용하도록 SHA-256 해시를 계산한다.
 */
@Service
public class InputHashService {

    private final ObjectMapper canonicalObjectMapper;

    /** JSON 객체 키 정렬이 적용된 전용 ObjectMapper를 생성한다. */
    public InputHashService(ObjectMapper objectMapper) {
        // 전역 ObjectMapper 설정을 바꾸지 않도록 복사본에만 결정적 직렬화를 적용한다.
        this.canonicalObjectMapper = objectMapper.copy()
                .enable(SerializationFeature.ORDER_MAP_ENTRIES_BY_KEYS);
    }

    /**
     * 모델·피처·프롬프트 버전과 현재·이전 피처로 입력 해시를 계산한다.
     */
    public String calculate(
            String modelVersion,
            String featureSchemaVersion,
            String promptVersion,
            boolean generateExplanation,
            Map<String, Object> currentFeatures,
            Map<String, Object> previousFeatures) {
        try {
            // FastAPI와 동일한 필드와 UTF-8 JSON을 사용하고 키 순서를 정렬한다.
            Map<String, Object> payload = new TreeMap<>();
            payload.put("currentFeatures", currentFeatures);
            payload.put("featureSchemaVersion", featureSchemaVersion);
            payload.put("generateExplanation", generateExplanation);
            payload.put("modelVersion", modelVersion);
            payload.put("previousFeatures", previousFeatures);
            payload.put("promptVersion", promptVersion);
            byte[] canonical = canonicalObjectMapper.writeValueAsBytes(payload);
            byte[] digest = MessageDigest.getInstance("SHA-256").digest(canonical);
            return HexFormat.of().formatHex(digest);
        } catch (JsonProcessingException | NoSuchAlgorithmException exception) {
            // 직렬화 실패 시 중복 예측이 생성될 수 있으므로 FastAPI 호출 전에 중단한다.
            throw new BusinessException(
                    "INPUT_HASH_FAILED",
                    "예측 입력 해시를 생성하지 못했습니다.",
                    HttpStatus.INTERNAL_SERVER_ERROR,
                    Map.of());
        }
    }
}

