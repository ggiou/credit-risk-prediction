package com.creditrisk.prediction.client;

import com.creditrisk.common.exception.BusinessException;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Component;
import org.springframework.web.client.ResourceAccessException;
import org.springframework.web.client.RestClient;
import org.springframework.web.client.RestClientResponseException;

import java.util.Map;

/**
 * Spring Boot에서 내부 FastAPI 예측 서버를 호출한다.
 */
@Component
public class AiPredictionClient {

    private static final Logger log = LoggerFactory.getLogger(AiPredictionClient.class);

    private final RestClient restClient;

    /** AI 서버 기본 주소가 설정된 RestClient를 주입받는다. */
    public AiPredictionClient(RestClient aiRestClient) {
        this.restClient = aiRestClient;
    }

    /**
     * 현재·이전 피처를 전달하고 위험률과 설명을 요청한다.
     */
    @SuppressWarnings("unchecked")
    public Map<String, Object> predict(Map<String, Object> requestBody) {
        try {
            // 브라우저가 AI 서버 주소를 알지 못하도록 Spring 서버에서만 내부 API를 호출한다.
            Map<String, Object> response = restClient.post()
                    .uri("/internal/v1/predictions")
                    .body(requestBody)
                    .retrieve()
                    .body(Map.class);
            if (response == null) {
                log.error(
                        "AI 서버가 빈 응답을 반환했습니다. requestId={} customerId={} baseYm={} featureSnapshotId={}",
                        context(requestBody, "requestId"),
                        context(requestBody, "customerId"),
                        context(requestBody, "baseYm"),
                        context(requestBody, "featureSnapshotId"));
                throw aiError("AI_SERVER_INVALID_RESPONSE", "AI 서버 응답이 비어 있습니다.", HttpStatus.BAD_GATEWAY);
            }
            logLlmFailure(response, requestBody);
            return response;
        } catch (ResourceAccessException exception) {
            // 연결 실패와 읽기 타임아웃은 모델 입력 오류가 아니므로 서비스 이용 불가로 구분한다.
            log.error(
                    "AI 서버 연결 또는 응답 시간이 초과되었습니다. requestId={} customerId={} baseYm={} errorType={}",
                    context(requestBody, "requestId"),
                    context(requestBody, "customerId"),
                    context(requestBody, "baseYm"),
                    exception.getClass().getSimpleName(),
                    exception);
            throw aiError("AI_SERVER_TIMEOUT", "AI 서버 연결 또는 응답 시간이 초과되었습니다.", HttpStatus.GATEWAY_TIMEOUT);
        } catch (RestClientResponseException exception) {
            // FastAPI가 반환한 내부 상세나 스택은 화면에 전달하지 않고 상태만 안전하게 변환한다.
            log.error(
                    "AI 서버가 오류 상태를 반환했습니다. requestId={} customerId={} baseYm={} httpStatus={} featureSchemaVersion={} modelVersion={} promptVersion={} errorType={}",
                    context(requestBody, "requestId"),
                    context(requestBody, "customerId"),
                    context(requestBody, "baseYm"),
                    exception.getStatusCode().value(),
                    context(requestBody, "featureSchemaVersion"),
                    context(requestBody, "expectedModelVersion"),
                    context(requestBody, "promptVersion"),
                    exception.getClass().getSimpleName(),
                    exception);
            throw aiError("AI_SERVER_ERROR", "AI 서버가 예측 요청을 처리하지 못했습니다.", HttpStatus.BAD_GATEWAY);
        }
    }

    /** HTTP 200 안의 LLM 부분 실패도 운영 로그에서 확인할 수 있도록 남긴다. */
    private void logLlmFailure(Map<String, Object> response, Map<String, Object> requestBody) {
        if (!(response.get("llm") instanceof Map<?, ?> llm)
                || !"FAILED".equals(String.valueOf(llm.get("status")))) {
            return;
        }
        Object errorValue = llm.get("errorMessage");
        String errorMessage = errorValue == null ? "unknown" : String.valueOf(errorValue);
        log.warn(
                "LightGBM 예측은 완료됐지만 LLM 설명 생성이 실패했습니다. requestId={} customerId={} baseYm={} error={}",
                context(requestBody, "requestId"),
                context(requestBody, "customerId"),
                context(requestBody, "baseYm"),
                errorMessage.substring(0, Math.min(errorMessage.length(), 500)));
    }

    /** 전체 요청 본문 대신 로그에 허용된 식별 필드만 추출한다. */
    private String context(Map<String, Object> requestBody, String key) {
        Object value = requestBody.get(key);
        return value == null ? "-" : String.valueOf(value);
    }

    /** AI 서버 호출 오류를 공통 업무 예외로 생성한다. */
    private BusinessException aiError(String code, String message, HttpStatus status) {
        return new BusinessException(code, message, status, Map.of());
    }
}
