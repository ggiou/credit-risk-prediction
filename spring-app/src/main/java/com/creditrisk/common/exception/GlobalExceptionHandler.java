package com.creditrisk.common.exception;

import com.creditrisk.common.api.RequestIdFilter;
import jakarta.servlet.http.HttpServletRequest;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.MethodArgumentNotValidException;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;
import org.springframework.web.servlet.ModelAndView;
import org.springframework.web.servlet.resource.NoResourceFoundException;

import java.time.Instant;
import java.util.LinkedHashMap;
import java.util.Map;

/**
 * Controller에서 발생한 예외를 공통 오류 응답으로 변환한다.
 */
@RestControllerAdvice
public class GlobalExceptionHandler {

    private static final Logger log = LoggerFactory.getLogger(GlobalExceptionHandler.class);

    /**
     * 업무 예외를 명세된 오류 코드와 상태로 반환한다.
     *
     * @param exception 발생한 업무 예외
     * @param request 현재 요청
     * @return 공통 오류 응답
     */
    @ExceptionHandler(BusinessException.class)
    public ResponseEntity<Map<String, Object>> handleBusinessException(
            BusinessException exception, HttpServletRequest request) {
        // 고객번호와 기준월처럼 허용된 상세 정보만 응답에 포함한다.
        return ResponseEntity.status(exception.getStatus())
                .body(errorBody(exception.getCode(), exception.getMessage(), exception.getDetails(), request));
    }

    /**
     * 요청 DTO 검증 실패를 잘못된 요청 오류로 반환한다.
     *
     * @param exception 입력값 검증 예외
     * @param request 현재 요청
     * @return 공통 오류 응답
     */
    @ExceptionHandler(MethodArgumentNotValidException.class)
    public ResponseEntity<Map<String, Object>> handleValidationException(
            MethodArgumentNotValidException exception, HttpServletRequest request) {
        // 여러 필드가 실패해도 화면이 최초 수정 지점을 바로 알 수 있도록 첫 오류를 사용한다.
        String message = exception.getBindingResult().getFieldErrors().stream()
                .findFirst()
                .map(error -> error.getField() + ": " + error.getDefaultMessage())
                .orElse("요청값이 올바르지 않습니다.");
        return ResponseEntity.badRequest()
                .body(errorBody("INVALID_REQUEST", message, Map.of(), request));
    }

    /**
     * Controller의 직접 입력 검증 실패를 잘못된 요청 오류로 반환한다.
     *
     * @param exception 잘못된 입력값 예외
     * @param request 현재 요청
     * @return 공통 오류 응답
     */
    @ExceptionHandler(IllegalArgumentException.class)
    public ResponseEntity<Map<String, Object>> handleIllegalArgumentException(
            IllegalArgumentException exception, HttpServletRequest request) {
        // 업무 데이터가 아닌 쿼리 파라미터 실패이므로 별도 상세값 없이 메시지만 반환한다.
        return ResponseEntity.badRequest()
                .body(errorBody("INVALID_REQUEST", exception.getMessage(), Map.of(), request));
    }

    /**
     * 예상하지 못한 오류의 내부 정보를 숨기고 공통 서버 오류로 반환한다.
     *
     * @param exception 처리되지 않은 예외
     * @param request 현재 요청
     * @return 공통 오류 응답
     */
    @ExceptionHandler(Exception.class)
    public Object handleUnexpectedException(
            Exception exception, HttpServletRequest request) {
        // 실패 원인은 서버 로그에만 기록하고 SQL·인증 정보는 화면 응답에 노출하지 않는다.
        log.error("처리되지 않은 서버 오류가 발생했습니다.", exception);
        if (acceptsHtml(request)) {
            return new ModelAndView(
                    "error/500",
                    Map.of("requestId", requestId(request)),
                    HttpStatus.INTERNAL_SERVER_ERROR);
        }
        return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR)
                .body(errorBody("INTERNAL_SERVER_ERROR", "요청 처리 중 오류가 발생했습니다.", Map.of(), request));
    }

    /** 존재하지 않는 정적 리소스 요청을 서버 오류와 구분한다. */
    @ExceptionHandler(NoResourceFoundException.class)
    public Object handleNoResourceFoundException(
            NoResourceFoundException exception, HttpServletRequest request) {
        if (acceptsHtml(request)) {
            return new ModelAndView(
                    "error/404",
                    Map.of("requestId", requestId(request)),
                    HttpStatus.NOT_FOUND);
        }
        return ResponseEntity.status(HttpStatus.NOT_FOUND)
                .body(errorBody("RESOURCE_NOT_FOUND", "요청한 리소스를 찾을 수 없습니다.", Map.of(), request));
    }

    /**
     * 명세에 맞는 공통 오류 본문을 생성한다.
     */
    private Map<String, Object> errorBody(
            String code, String message, Map<String, Object> details, HttpServletRequest request) {
        // LinkedHashMap으로 필드 순서를 고정해 로그와 API 문서 비교를 쉽게 한다.
        Map<String, Object> error = new LinkedHashMap<>();
        error.put("code", code);
        error.put("message", message);
        error.put("details", details);

        Map<String, Object> body = new LinkedHashMap<>();
        body.put("success", false);
        body.put("error", error);
        body.put("timestamp", Instant.now());
        body.put("requestId", request.getAttribute(RequestIdFilter.ATTRIBUTE_NAME));
        return body;
    }

    /** 브라우저의 HTML 페이지 요청인지 확인한다. */
    private boolean acceptsHtml(HttpServletRequest request) {
        String accept = request.getHeader("Accept");
        return accept != null && accept.contains("text/html");
    }

    /** 오류 화면에 표시할 요청 ID를 null 없이 반환한다. */
    private String requestId(HttpServletRequest request) {
        Object value = request.getAttribute(RequestIdFilter.ATTRIBUTE_NAME);
        return value == null ? "-" : String.valueOf(value);
    }
}
