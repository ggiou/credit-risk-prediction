package com.creditrisk.page;

import com.creditrisk.common.api.RequestIdFilter;
import jakarta.servlet.RequestDispatcher;
import jakarta.servlet.http.HttpServletRequest;
import org.springframework.boot.web.servlet.error.ErrorController;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.stereotype.Controller;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.servlet.ModelAndView;

import java.time.Instant;
import java.util.LinkedHashMap;
import java.util.Map;

/** 페이지 렌더링 단계의 오류를 사용자용 화면 또는 API 응답으로 변환한다. */
@Controller
public class PageErrorController implements ErrorController {

    /** 원래 요청 유형과 상태에 맞는 안전한 오류 응답을 반환한다. */
    @RequestMapping("/error")
    public Object error(HttpServletRequest request) {
        int statusCode = statusCode(request);
        String requestId = requestId(request);
        if (isApiRequest(request)) {
            return ResponseEntity.status(statusCode).body(apiError(statusCode, requestId));
        }
        if (statusCode >= 500) {
            return new ModelAndView(
                    "error/500",
                    Map.of("requestId", requestId),
                    HttpStatus.INTERNAL_SERVER_ERROR);
        }
        return new ModelAndView(
                "error/404",
                Map.of("requestId", requestId),
                HttpStatus.NOT_FOUND);
    }

    /** Servlet 오류 속성에서 HTTP 상태를 읽는다. */
    private int statusCode(HttpServletRequest request) {
        Object value = request.getAttribute(RequestDispatcher.ERROR_STATUS_CODE);
        return value instanceof Number number ? number.intValue() : 500;
    }

    /** 원래 요청 경로 또는 Accept 헤더로 API 요청을 구분한다. */
    private boolean isApiRequest(HttpServletRequest request) {
        Object uri = request.getAttribute(RequestDispatcher.ERROR_REQUEST_URI);
        String path = uri == null ? request.getRequestURI() : String.valueOf(uri);
        String contextPath = request.getContextPath();
        if (!contextPath.isEmpty() && path.startsWith(contextPath)) {
            path = path.substring(contextPath.length());
        }
        String accept = request.getHeader("Accept");
        return path.startsWith("/api/")
                || path.startsWith("/internal/")
                || accept != null && accept.contains("application/json");
    }

    /** 오류 추적에 사용할 요청 ID를 null 없이 반환한다. */
    private String requestId(HttpServletRequest request) {
        Object value = request.getAttribute(RequestIdFilter.ATTRIBUTE_NAME);
        return value == null ? "-" : String.valueOf(value);
    }

    /** 기본 오류 처리 단계에서도 기존 API 오류 형식을 유지한다. */
    private Map<String, Object> apiError(int statusCode, String requestId) {
        Map<String, Object> error = new LinkedHashMap<>();
        error.put("code", statusCode >= 500 ? "INTERNAL_SERVER_ERROR" : "RESOURCE_NOT_FOUND");
        error.put("message", statusCode >= 500
                ? "요청 처리 중 오류가 발생했습니다."
                : "요청한 리소스를 찾을 수 없습니다.");
        error.put("details", Map.of());

        Map<String, Object> body = new LinkedHashMap<>();
        body.put("success", false);
        body.put("error", error);
        body.put("timestamp", Instant.now());
        body.put("requestId", requestId);
        return body;
    }
}
