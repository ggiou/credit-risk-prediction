package com.creditrisk.common.exception;

import org.springframework.http.HttpStatus;

import java.util.Map;

/**
 * 화면에 안전하게 공개할 수 있는 업무 오류를 표현한다.
 */
public class BusinessException extends RuntimeException {

    private final String code;
    private final HttpStatus status;
    private final Map<String, Object> details;

    /**
     * 오류 코드와 HTTP 상태를 포함한 업무 예외를 생성한다.
     *
     * @param code API 오류 코드
     * @param message 사용자에게 전달할 오류 메시지
     * @param status HTTP 상태
     * @param details 오류 확인에 필요한 비민감 상세값
     */
    public BusinessException(String code, String message, HttpStatus status, Map<String, Object> details) {
        super(message);
        this.code = code;
        this.status = status;
        this.details = details == null ? Map.of() : Map.copyOf(details);
    }

    /** API 오류 코드를 반환한다. */
    public String getCode() {
        return code;
    }

    /** 응답에 사용할 HTTP 상태를 반환한다. */
    public HttpStatus getStatus() {
        return status;
    }

    /** 오류 확인에 필요한 상세값을 반환한다. */
    public Map<String, Object> getDetails() {
        return details;
    }
}

