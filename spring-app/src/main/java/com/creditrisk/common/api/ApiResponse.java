package com.creditrisk.common.api;

import java.time.Instant;

/**
 * 화면용 API가 공통으로 사용하는 성공 응답 형식이다.
 *
 * @param success 성공 여부
 * @param data 응답 데이터
 * @param timestamp 응답 생성 시각
 * @param requestId 요청 추적 식별자
 * @param <T> 응답 데이터 자료형
 */
public record ApiResponse<T>(boolean success, T data, Instant timestamp, String requestId) {

    /**
     * 현재 요청 식별자를 포함한 성공 응답을 생성한다.
     *
     * @param data 반환할 데이터
     * @param requestId 요청 추적 식별자
     * @return 공통 성공 응답
     * @param <T> 응답 데이터 자료형
     */
    public static <T> ApiResponse<T> success(T data, String requestId) {
        // 모든 성공 API의 메타 필드를 같은 기준으로 맞춘다.
        return new ApiResponse<>(true, data, Instant.now(), requestId);
    }
}

