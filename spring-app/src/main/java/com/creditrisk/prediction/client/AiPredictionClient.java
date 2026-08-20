package com.creditrisk.prediction.client;

import com.creditrisk.common.exception.BusinessException;
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
                throw aiError("AI_SERVER_INVALID_RESPONSE", "AI 서버 응답이 비어 있습니다.", HttpStatus.BAD_GATEWAY);
            }
            return response;
        } catch (ResourceAccessException exception) {
            // 연결 실패와 읽기 타임아웃은 모델 입력 오류가 아니므로 서비스 이용 불가로 구분한다.
            throw aiError("AI_SERVER_TIMEOUT", "AI 서버 연결 또는 응답 시간이 초과되었습니다.", HttpStatus.GATEWAY_TIMEOUT);
        } catch (RestClientResponseException exception) {
            // FastAPI가 반환한 내부 상세나 스택은 화면에 전달하지 않고 상태만 안전하게 변환한다.
            throw aiError("AI_SERVER_ERROR", "AI 서버가 예측 요청을 처리하지 못했습니다.", HttpStatus.BAD_GATEWAY);
        }
    }

    /** AI 서버 호출 오류를 공통 업무 예외로 생성한다. */
    private BusinessException aiError(String code, String message, HttpStatus status) {
        return new BusinessException(code, message, status, Map.of());
    }
}

